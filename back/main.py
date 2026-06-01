import secrets
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, model_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from passlib.context import CryptContext
from db import engine, get_db, async_session_maker
from models import Base, User, VirtualMachine
from tasks import send_email_task

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
active_connections: dict[int, WebSocket] = {}

tags_metadata = [
    {"name": "Авторизация", "description": "Регистрация и вход пользователей."},
    {"name": "Десктоп", "description": "Выдача и освобождение виртуальных машин."},
    {"name": "Пользователи", "description": "Управление профилем (ключи, пароли)."}
]

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_maker() as session:
        result = await session.execute(select(VirtualMachine).limit(1))
        if not result.scalar_one_or_none():
            print("Создаю тестовые виртуальные машины в базе...")
            session.add_all([
                VirtualMachine(name="FRTR-Server-Frankfurt", host="192.168.1.10", port=8080, protocol="http"),
                VirtualMachine(name="FRTR-Server-London", host="192.168.1.11", port=1080, protocol="socks5"),
                VirtualMachine(name="FRTR-Server-Amsterdam", host="192.168.1.12", port=3128, protocol="http")
            ])
            await session.commit()
    yield
    await engine.dispose()

app = FastAPI(
    title="FRTR Access API",
    description="API для управления прокси-серверами через десктопный клиент.",
    version="1.0.0",
    openapi_tags=tags_metadata,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class UserRegisterSchema(BaseModel):
    email: EmailStr
    password: str
    password_confirm: str

    @model_validator(mode='after')
    def check_passwords_match(self):
        if self.password != self.password_confirm:
            raise ValueError('Пароли не совпадают')
        return self

class UserLoginSchema(BaseModel):
    email: EmailStr
    password: str

class ChangePasswordSchema(BaseModel):
    old_password: str
    new_password: str

class DesktopConnectSchema(BaseModel):
    activation_key: str

@app.websocket("/ws/connection-status/{user_id}")
async def websocket_profile(websocket: WebSocket, user_id: int, token: str = Query(...)):
    await websocket.accept()
    
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.id == user_id, User.activation_key == token))
        user = result.scalar_one_or_none()
        
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
        
    active_connections[user_id] = websocket
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if user_id in active_connections:
            del active_connections[user_id]

@app.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    tags=["Авторизация"],
    summary="Регистрация пользователя",
    responses={201: {"description": "Успешно"}, 400: {"description": "Email уже занят"}}
)
async def register(data: UserRegisterSchema, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Пользователь с таким email уже существует")

    hashed_pwd = pwd_context.hash(data.password)
    activation_key = secrets.token_hex(16)

    new_user = User(email=data.email, password=hashed_pwd, activation_key=activation_key)
    db.add(new_user)
    await db.commit()

    send_email_task.delay(data.email, activation_key)
    return {"message": "Регистрация успешна!"}

@app.post(
    "/login",
    tags=["Авторизация"],
    summary="Вход в систему",
    responses={200: {"description": "Успешный вход"}, 401: {"description": "Неверные данные"}}
)
async def login(data: UserLoginSchema, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user or not pwd_context.verify(data.password, user.password):
        raise HTTPException(status_code=401, detail="Неверный email или пароль")

    return {"id": user.id, "email": user.email, "activation_key": user.activation_key}

@app.patch(
    "/users/{user_id}/regenerate-key",
    tags=["Пользователи"],
    summary="Перевыпуск ключа доступа"
)
async def regenerate_key(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    # Принудительно освобождаем ВМ при сбросе ключа (сброс сессии)
    vm_res = await db.execute(select(VirtualMachine).where(VirtualMachine.current_user_id == user.id))
    vm = vm_res.scalar_one_or_none()
    if vm:
        vm.current_user_id = None
        if user.id in active_connections:
            try:
                await active_connections[user.id].send_json({"status": "disconnected"})
            except Exception:
                pass

    new_key = secrets.token_hex(16)
    user.activation_key = new_key
    await db.commit()

    send_email_task.delay(user.email, new_key)
    return {"activation_key": new_key}

@app.patch(
    "/users/{user_id}/change-password",
    tags=["Пользователи"],
    summary="Смена пароля"
)
async def change_password(user_id: int, data: ChangePasswordSchema, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not pwd_context.verify(data.old_password, user.password):
        raise HTTPException(status_code=400, detail="Старый пароль введен неверно")

    user.password = pwd_context.hash(data.new_password)
    await db.commit()
    return {"message": "Пароль успешно изменен"}

@app.post(
    "/api/activate-key",
    tags=["Десктоп"],
    summary="Подключение десктопа к серверу",
    responses={
        200: {"description": "ВМ успешно выдана"},
        401: {"description": "Ключ недействителен"},
        503: {"description": "Нет свободных ВМ"}
    }
)
async def desktop_connect(data: DesktopConnectSchema, db: AsyncSession = Depends(get_db)):
    user_res = await db.execute(select(User).where(User.activation_key == data.activation_key))
    user = user_res.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="Неверный или уже использованный ключ")

    vm_res = await db.execute(select(VirtualMachine).where(VirtualMachine.current_user_id == user.id))
    vm = vm_res.scalar_one_or_none()

    if vm:
        raise HTTPException(status_code=400, detail="Сессия уже активна. Отключитесь или сбросьте ключ в профиле.")

    free_vm_res = await db.execute(select(VirtualMachine).where(
        VirtualMachine.current_user_id.is_(None)
    ).limit(1))
    vm = free_vm_res.scalar_one_or_none()

    if not vm:
        raise HTTPException(status_code=503, detail="Нет свободных серверов. Попробуйте позже.")

    vm.current_user_id = user.id

    user.activation_key = secrets.token_hex(16)
    await db.commit()

    if user.id in active_connections:
        ws = active_connections[user.id]
        try:
            await ws.send_json({
                "status": "connected",
                "vm_data": {
                    "name": vm.name,
                    "host": vm.host,
                    "port": vm.port,
                    "protocol": vm.protocol
                },
                "new_key": user.activation_key
            })
        except Exception as e:
            print(f"Ошибка WebSocket: {e}")

    return {
        "message": "Подключение разрешено",
        "vm_name": vm.name,
        "vm_ip": f"{vm.protocol}://{vm.host}:{vm.port}",
        "new_key": user.activation_key
    }

@app.delete(
    "/api/activate-key/{activation_key}",
    tags=["Десктоп"],
    summary="Отключение десктопа и освобождение ВМ"
)
async def desktop_disconnect(activation_key: str, db: AsyncSession = Depends(get_db)):
    user_res = await db.execute(select(User).where(User.activation_key == activation_key))
    user = user_res.scalar_one_or_none()

    if not user:
        return {"message": "Уже отключено"}

    vm_res = await db.execute(select(VirtualMachine).where(VirtualMachine.current_user_id == user.id))
    vm = vm_res.scalar_one_or_none()

    if vm:
        vm.current_user_id = None
        await db.commit()

        if user.id in active_connections:
            ws = active_connections[user.id]
            try:
                await ws.send_json({"status": "disconnected"})
            except Exception:
                pass

    return {"message": "Успешно отключено"}