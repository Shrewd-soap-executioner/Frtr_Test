import pytest
from httpx import AsyncClient, ASGITransport
import uuid
from main import app


pytestmark = pytest.mark.anyio


@pytest.fixture(scope="session")
def anyio_backend():
    return 'asyncio'


@pytest.fixture(scope="session")
async def ac():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


async def test_register_user(ac: AsyncClient):
    test_email = f"test_{uuid.uuid4().hex[:6]}@example.com"

    response = await ac.post(
        "/register",
        json={
            "email": test_email,
            "password": "securepassword123",
            "password_confirm": "securepassword123"
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert "message" in data
    assert data["message"] == "Регистрация успешна!"


async def test_register_password_mismatch(ac: AsyncClient):
    test_email = f"test_{uuid.uuid4().hex[:6]}@mismatch.com"

    response = await ac.post(
        "/register",
        json={
            "email": test_email,
            "password": "password123",
            "password_confirm": "different_password"
        }
    )
    assert response.status_code == 422


async def test_login_user(ac: AsyncClient):
    test_email = f"test_{uuid.uuid4().hex[:6]}@login.com"
    test_password = "testpassword"

    await ac.post(
        "/register",
        json={"email": test_email, "password": test_password, "password_confirm": test_password}
    )

    response = await ac.post(
        "/login",
        json={"email": test_email, "password": test_password}
    )

    assert response.status_code == 200
    data = response.json()
    assert "activation_key" in data
    assert len(data["activation_key"]) == 32


async def test_login_wrong_password(ac: AsyncClient):
    test_email = f"test_{uuid.uuid4().hex[:6]}@wrongpass.com"

    await ac.post(
        "/register",
        json={"email": test_email, "password": "correct_password", "password_confirm": "correct_password"}
    )

    response = await ac.post(
        "/login",
        json={"email": test_email, "password": "wrong_password"}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Неверный email или пароль"


async def test_regenerate_key(ac: AsyncClient):
    test_email = f"test_{uuid.uuid4().hex[:6]}@regen.com"

    await ac.post("/register", json={"email": test_email, "password": "pass", "password_confirm": "pass"})
    login_resp = await ac.post("/login", json={"email": test_email, "password": "pass"})

    user_id = login_resp.json()["id"]
    old_key = login_resp.json()["activation_key"]

    regen_resp = await ac.post(f"/users/{user_id}/regenerate-key")
    assert regen_resp.status_code == 200

    new_key = regen_resp.json()["activation_key"]
    assert new_key != old_key


async def test_change_password(ac: AsyncClient):
    test_email = f"test_{uuid.uuid4().hex[:6]}@changepass.com"
    old_pass = "old_password"
    new_pass = "new_password_123"

    await ac.post("/register", json={"email": test_email, "password": old_pass, "password_confirm": old_pass})
    login_resp = await ac.post("/login", json={"email": test_email, "password": old_pass})
    user_id = login_resp.json()["id"]

    change_resp = await ac.post(
        f"/users/{user_id}/change-password",
        json={"old_password": old_pass, "new_password": new_pass}
    )
    assert change_resp.status_code == 200

    success_login = await ac.post("/login", json={"email": test_email, "password": new_pass})
    assert success_login.status_code == 200

async def test_desktop_flow_and_single_use_key(ac: AsyncClient):
    test_email = f"test_{uuid.uuid4().hex[:6]}@desktop.com"

    await ac.post("/register", json={"email": test_email, "password": "pass", "password_confirm": "pass"})
    login_resp = await ac.post("/login", json={"email": test_email, "password": "pass"})
    activation_key = login_resp.json()["activation_key"]

    connect_resp = await ac.post("/api/activate-key", json={"activation_key": activation_key})

    if connect_resp.status_code == 503:
        pytest.skip("Нет свободных тестовых машин для завершения этого теста (503 Service Unavailable)")

    assert connect_resp.status_code == 200
    data = connect_resp.json()
    assert "new_key" in data
    new_key = data["new_key"]

    spam_resp = await ac.post("/api/activate-key", json={"activation_key": activation_key})
    assert spam_resp.status_code == 401
    assert "Неверный или уже использованный ключ" in spam_resp.json()["detail"]

    disconnect_resp = await ac.post("/api/disconnect", json={"activation_key": new_key})
    assert disconnect_resp.status_code == 200
    assert disconnect_resp.json()["message"] == "Успешно отключено"