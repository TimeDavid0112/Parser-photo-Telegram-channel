from pyrogram import Client
from config import API_ID, API_HASH, SESSION_NAME

if __name__ == "__main__":
    app = Client(SESSION_NAME, api_id=API_ID, api_hash=API_HASH)
    try:
        app.start()
        print("✅ Авторизация успешна, сессия сохранена!")
        app.stop()
    except KeyError as e:
        print("❌ Telegram требует подтверждения через e-mail.")
        print("Зайди в официальный клиент, привяжи e-mail и повтори запуск.")
