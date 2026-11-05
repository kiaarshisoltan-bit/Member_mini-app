import json
import os
import threading
import time
from datetime import datetime, timedelta
from flask import Flask, jsonify, render_template_string, request
import requests

app = Flask(__name__)

# --- تنظیمات و توکن ربات ---
# توکن ربات بله خود را اینجا قرار دهید
TOKEN = "YOUR_BALE_BOT_TOKEN"
BASE_URL = f"https://tapi.bale.ai/bot{TOKEN}"
ADMIN_ID = 1708788049
DB_FILE = "bot_database.json"

# --- مدیریت دیتابیس JSON ---
db_lock = threading.Lock()


def load_db():
  if not os.path.exists(DB_FILE):
    default_data = {
        "users": {},
        "campaigns": [],
        "promo_codes": {},
        "channels": [],
    }
    save_db(default_data)
    return default_data
  with db_lock:
    try:
      with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except:
      return {"users": {}, "campaigns": [], "promo_codes": {}, "channels": []}


def save_db(data):
  with db_lock:
    with open(DB_FILE, "w", encoding="utf-8") as f:
      json.dump(data, f, ensure_ascii=False, indent=4)


# --- توابع کمکی ربات بله ---
def send_message(chat_id, text, reply_markup=None):
  url = f"{BASE_URL}/sendMessage"
  payload = {"chat_id": chat_id, "text": text}
  if reply_markup:
    payload["reply_markup"] = json.dumps(reply_markup)
  try:
    requests.post(url, json=payload, timeout=10)
  except Exception as e:
    print(f"Error sending message: {e}")


# --- منطق اصلی ربات و مینی اپ (Flask Routes) ---
@app.route("/")
def home():
  return "Bale Membergir Bot is Running! 🚀"


@app.route("/webapp", methods=["GET"])
def webapp():
  # مینی اپ گرافیکی و ساده برای کاربران
  chat_id = request.args.get("chat_id")
  db = load_db()
  user = db["users"].get(str(chat_id), {})

  html_template = """
    <!DOCTYPE html>
    <html lang="fa" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ممبرگیر بله</title>
        <style>
            body { font-family: Tahoma, sans-serif; background: #f4f7f6; margin: 0; padding: 20px; color: #333; }
            .card { background: #fff; padding: 20px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); margin-bottom: 15px; }
            h2 { color: #007bff; margin-top: 0; }
            .btn { background: #28a745; color: white; border: none; padding: 10px 15px; border-radius: 8px; cursor: pointer; width: 100%; font-size: 16px; margin-top: 10px;}
            .info { font-size: 14px; color: #555; line-height: 1.6; }
        </style>
    </head>
    <body>
        <div class="card">
            <h2>👤 حساب کاربری شما</h2>
            <div class="info">
                <p><b>نام مستعار:</b> {{ user.get('nickname', 'ثبت‌نشده') }}</p>
                <p><b>موجودی سکه:</b> 🪙 {{ user.get('coins', 0) }}</p>
                <p><b>آیدی عددی:</b> {{ chat_id }}</p>
            </div>
        </div>
        <div class="card">
            <h2>🎁 کسب درآمد و سکه</h2>
            <p class="info">برای دریافت سکه رایگان از طریق ربات در پیام‌رسان بله اقدام کنید!</p>
        </div>
    </body>
    </html>
    """
  return render_template_string(
      html_template, user=user, chat_id=chat_id
  )


# --- ترد Polling برای دریافت پیام‌های بله ---
def bale_polling():
  offset = 0
  print("Bale Bot Polling Started...")
  while True:
    try:
      response = requests.get(
          f"{BASE_URL}/getUpdates",
          params={"offset": offset, "timeout": 30},
          timeout=35,
      )
      if response.status_code == 200:
        result = response.json().get("result", [])
        for update in result:
          offset = update["update_id"] + 1
          handle_update(update)
      time.sleep(1)
    except Exception as e:
      print(f"Polling error: {e}")
      time.sleep(5)


def handle_update(update):
  if "message" not in update:
    return
  msg = update["message"]
  chat_id = msg["chat"]["id"]
  text = msg.get("text", "").strip()

  db = load_db()
  str_chat_id = str(chat_id)

  # ثبت نام خودکار /start
  if text.startswith("/start"):
    if str_chat_id not in db["users"]:
      # بررسی لینک دعوت (رفرال)
      parts = text.split()
      ref_id = parts[1] if len(parts) > 1 else None

      db["users"][str_chat_id] = {
          "nickname": f"کاربر_{chat_id}",
          "coins": 50,  # جایزه ورود اولیه
          "ref_by": ref_id,
      }

      if ref_id and ref_id in db["users"] and ref_id != str_chat_id:
        db["users"][ref_id]["coins"] += 20  # پاداش زیرمجموعه‌گیری

      save_db(db)
      send_message(
          chat_id,
          "سلام کیا جان! خوش اومدی. 🌺\n۵۰ سکه هدیه ورود به شما داده شد.\nلطفاً"
          " نام مستعار خود را با ارسال دستور زیر ثبت کنید:\n/setname [نام"
          " مستعار]",
      )
    else:
      send_message(
          chat_id,
          f"سلام مجدد! حساب کاربری شما فعال است.\nموجودی سکه: 🪙"
          f" {db['users'][str_chat_id]['coins']}",
      )

  elif text.startswith("/setname"):
    parts = text.split(maxsplit=1)
    if len(parts) > 1:
      nickname = parts[1]
      db["users"][str_chat_id]["nickname"] = nickname
      save_db(db)
      send_message(
          chat_id, f"✅ نام مستعار شما با موفقیت به «{nickname}» تغییر یافت!"
      )
    else:
      send_message(
          chat_id, "❌ لطفاً نام مستعار خود را وارد کنید. مثال:\n/setname ممد"
      )

  elif text == "پشتیبانی" or text == "/support":
    send_message(
        chat_id,
        "📞 راه‌های ارتباطی و پشتیبانی:\nآیدی پشتیبان: @kia_karfarma",
    )


# --- ترد Keep-Alive برای جلوگیری از خوابیدن سرور Render ---
def keep_alive_worker():
  # بعد از دیلوِی روی Render، آدرس وب‌اپ خود را اینجا قرار دهید تا هر ۳ دقیقه پینگ شود
  render_url = os.environ.get("RENDER_EXTERNAL_URL")
  if not render_url:
    return
  while True:
    try:
      requests.get(render_url)
    except:
      pass
    time.sleep(180)  # هر ۳ دقیقه


if __name__ == "__main__":
  # شروع ترد پولینگ بله
  t_polling = threading.Thread(target=bale_polling, daemon=True)
  t_polling.start()

  # شروع ترد Keep-Alive
  t_keep = threading.Thread(target=keep_alive_worker, daemon=True)
  t_keep.start()

  # اجرای سرور Flask روی پورت پورتی که Render میده
  port = int(os.environ.get("PORT", 5000))
  app.run(host="0.0.0.0", port=port)
