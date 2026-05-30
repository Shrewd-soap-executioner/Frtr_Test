import os
import smtplib
from email.message import EmailMessage
from celery import Celery

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")

celery_app = Celery('tasks', broker=CELERY_BROKER_URL)
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Europe/Moscow',
    enable_utc=True,
)

SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 465))


@celery_app.task
def send_email_task(user_email: str, activation_key: str):

    if not SMTP_USER or not SMTP_PASSWORD:
        print(f"[CELERY] SMTP не настроен. Ключ для {user_email}: {activation_key}")
        return False

    try:
        print(f"[CELERY] Подключение к {SMTP_HOST} для отправки письма на {user_email}...")

        msg = EmailMessage()
        msg['Subject'] = "Ваш ключ доступа к FTRTRTestService"
        msg['From'] = SMTP_USER
        msg['To'] = user_email

        html_content = f"""
        <html>
          <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px;">
            <div style="max-width: 600px; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
              <h2 style="color: #1976D2; text-align: center;">Добро пожаловать!</h2>
              <p style="font-size: 16px; color: #333;">Ваш уникальный ключ сгенерирован.</p>
              <div style="background-color: #f8f9fa; padding: 15px; border-radius: 4px; text-align: center; margin: 20px 0;">
                <code style="font-size: 18px; color: #d63384; word-break: break-all;">{activation_key}</code>
              </div>
              <p style="font-size: 14px; color: #777; text-align: center;">Никому не передавайте этот ключ!</p>
            </div>
          </body>
        </html>
        """
        msg.set_content("Ваш почтовый клиент не поддерживает HTML.")
        msg.add_alternative(html_content, subtype='html')

        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

        print(f"[CELERY] Письмо отправлено на {user_email}")
        return True

    except Exception as e:
        print(f"[CELERY] Ошибка отправки: {str(e)}")
        return False