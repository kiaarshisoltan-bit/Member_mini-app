import json
import os
import random
import threading
import time
from datetime import datetime, timedelta
from flask import Flask, jsonify, render_template_string, request
import requests

app = Flask(__name__)

# --- تنظیمات و توکن ربات ---
TOKEN = "GAPGPTMASKTOKEN6lp2g2qw50qX0X"  # توکن ربات بله
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


# --- مینی‌اپ و صفحات وب (Flask) ---
@app.route("/")
def home():
  return "Bale Membergir Bot & Mini-App is Running! 🚀"


@app.route("/webapp", methods=["GET"])
def webapp():
  chat_id = request.args.get("chat_id")
  db = load_db()
  user = db["users"].get(str(chat_id), {})

  html_template = """
    <!DOCTYPE html>
    <html lang="fa" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>مینی‌اپ ممبرگیر بله</title>
        <style>
            body { font-family: Tahoma, sans-serif; background: #f4f7f6; margin: 0; padding: 15px; color: #333; }
            .card { background: #fff; padding: 15px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); margin-bottom: 15px; }
            h2 { color: #007bff; margin-top: 0; font-size: 18px; }
            .info { font-size: 14px; color: #555; line-height: 1.6; }
            .btn { background: #007bff; color: white; border: none; padding: 10px; border-radius: 8px; width: 100%; font-size: 15px; cursor: pointer; margin-top: 5px; }
            .highlight { color: #28a745; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="card">
            <h2>👤 حساب کاربری شما</h2>
            <div class="info">
                <p><b>نام مستعار:</b> {{ user.get('nickname', 'ثبت‌نشده') }}</p>
                <p><b>موجودی سکه:</b> <span class="highlight">🪙 {{ user.get('coins', 0) }}</span></p>
                <p><b>آیدی عددی:</b> {{ chat_id }}</p>
                <p><b>لینک دعوت شما:</b> <br><code>https://ble.ir/bot_username?start={{ chat_id }}</code></p>
            </div>
        </div>
        <div class="card">
            <h2>🚀 بخش‌های ربات</h2>
            <p class="info">برای ثبت سفارش ممبر، چرخش گردونه شانس، دریافت سکه از طریق بازدید کانال‌ها و انتقال سکه، به ربات تلگرام/بله مراجعه کنید!</p>
        </div>
    </body>
    </html>
    """
  return render_template_string(
      html_template, user=user, chat_id=chat_id
  )


# --- ترد Polling بله ---
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

  # دستور /start و ثبت‌نام خودکار
  if text.startswith("/start"):
    if str_chat_id not in db["users"]:
      parts = text.split()
      ref_id = parts[1] if len(parts) > 1 else None

      db["users"][str_chat_id] = {
          "nickname": f"کاربر_{chat_id}",
          "coins": 50,  # جایزه ورود
          "ref_by": ref_id,
          "last_spin": None,
      }

      if ref_id and ref_id in db["users"] and ref_id != str_chat_id:
        db["users"][ref_id]["coins"] += 20  # پاداش زیرمجموعه‌گیری

      save_db(db)
      send_message(
          chat_id,
          "سلام کیا جان! خوش اومدی. 🌺\n۵۰ سکه هدیه ورود به شما داده شد.\nلطفاً"
          " نام مستعار خود را با دستور زیر ثبت کنید:\n/setname [نام"
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

  elif text == "حساب کاربری" or text == "/profile":
    u = db["users"].get(
        str_chat_id, {"nickname": "ثبت‌نشده", "coins": 0}
    )
    send_message(
        chat_id,
        f"👤 **حساب کاربری شما:**\n\nنام مستعار: {u['nickname']}\nموجودی سکه: 🪙"
        f" {u['coins']}\nآیدی عددی: {chat_id}",
    )

  elif text == "کسب درآمد" or text == "/earn":
    send_message(
        chat_id,
        "🎁 **روش‌های افزایش سکه:**\n\n1️⃣ زیرمجموعه‌گیری: ارسال لینک دعوت به"
        f" دوستان (هر دعوت = ۲۰ سکه)\nلینک دعوت شما:\n`https://ble.ir/bot?start={chat_id}`\n\n2️⃣"
        " عضویت در کانال رسمی ربات: جایزه ۳۰ سکه‌ای (با دستور /join_official)\n3️⃣"
        " گردونه شانس روزانه: دستور /spin\n4️⃣ استفاده از کد هدیه: دستور /promo"
        " [کد]",
    )

  elif text == "/join_official":
    # جایزه عضویت در کانال اطلاع‌رسانی (فرض بر تایید)
    if "official_joined" not in db["users"][str_chat_id]:
      db["users"][str_chat_id]["official_joined"] = True
      db["users"][str_chat_id]["coins"] += 30
      save_db(db)
      send_message(
          chat_id, "🎉 ۳۰ سکه جایزه عضویت در کانال @ettela_resani_member واریز شد!"
      )
    else:
      send_message(
          chat_id, "❌ شما قبلاً جایزه این کانال را دریافت کرده‌اید!"
      )

  elif text == "/spin":
    # گردونه شانس هر ۲۴ ساعت
    user_data = db["users"][str_chat_id]
    last_spin = user_data.get("last_spin")
    now = datetime.now()

    if last_spin:
      last_spin_time = datetime.fromisoformat(last_spin)
      if now - last_spin_time < timedelta(hours=24):
        remaining = timedelta(hours=24) - (now - last_spin_time)
        hours, remainder = divmod(int(remaining.total_seconds()), 3600)
        minutes, _ = divmod(remainder, 60)
        send_message(
            chat_id,
            f"⏳ شما قبلاً گردونه را چرخانده‌اید!\nلطفاً {hours} ساعت و"
            f" {minutes} دقیقه دیگر صبر کنید.",
        )
        return

    reward = random.randint(0, 100)
    user_data["coins"] += reward
    user_data["last_spin"] = now.isoformat()
    save_db(db)
    send_message(
        chat_id,
        f"🎡 چرخش گردونه شانس انجام شد!\nشما برنده **{reward} سکه** شدید. 🪙",
    )

  elif text.startswith("/promo"):
    parts = text.split()
    if len(parts) > 1:
      code = parts[1]
      promo_codes = db.get("promo_codes", {})
      if code in promo_codes:
        p_data = promo_codes[code]
        if p_data["uses"] > 0 and str_chat_id not in p_data["claimed_by"]:
          p_data["uses"] -= 1
          p_data["claimed_by"].append(str_chat_id)
          db["users"][str_chat_id]["coins"] += p_data["reward"]
          save_db(db)
          send_message(
              chat_id,
              f"✅ کد هدیه با موفقیت اعمال شد! {p_data['reward']} سکه به شما"
              " اضافه شد.",
          )
        else:
          send_message(
              chat_id, "❌ این کد هدیه منقضی شده یا قبلاً استفاده شده است."
          )
      else:
        send_message(chat_id, "❌ کد هدیه نامعتبر است.")
    else:
      send_message(
          chat_id, "❌ لطفاً کد هدیه را وارد کنید. مثال:\n/promo KIALAND100"
      )

  elif text.startswith("/transfer"):
    # فرمت: /transfer [chat_id] [amount]
    parts = text.split()
    if len(parts) == 3:
      target_id = parts[1]
      try:
        amount = int(parts[2])
      except:
        send_message(chat_id, "❌ مقدار سکه باید عدد باشد.")
        return

      if target_id not in db["users"]:
        send_message(chat_id, "❌ کاربر مقصد در ربات ثبت‌نام نکرده است.")
        return
      if amount <= 0 or db["users"][str_chat_id]["coins"] < amount:
        send_message(chat_id, "❌ موجودی کافی نیست یا مقدار نامعتبر است.")
        return

      db["users"][str_chat_id]["coins"] -= amount
      db["users"][target_id]["coins"] += amount
      save_db(db)
      send_message(chat_id, f"✅ {amount} سکه با موفقیت به کاربر انتقال یافت.")
      send_message(target_id, f"🎁 {amount} سکه از طرف کاربر {chat_id} دریافت کردید!")
    else:
      send_message(
          chat_id,
          "❌ فرمت دستور نادرست است. مثال:\n/transfer 123456789 50",
      )

  elif text.startswith("/order"):
    # فرمت: /order [لینک کانال] [تعداد ممبر]
    parts = text.split()
    if len(parts) == 3:
      channel_link = parts[1]
      try:
        count = int(parts[2])
      except:
        send_message(chat_id, "❌ تعداد ممبر باید عدد باشد.")
        return

      total_cost = count * 2  # هر ممبر ۲ سکه
      if db["users"][str_chat_id]["coins"] < total_cost:
        send_message(
            chat_id,
            f"❌ موجودی کافی نیست! هزینه کل: {total_cost} سکه (هر ممبر ۲ سکه).",
        )
        return

      db["users"][str_chat_id]["coins"] -= total_cost
      db["campaigns"].append({
          "user_id": str_chat_id,
          "channel": channel_link,
          "requested": count,
          "delivered": 0,
      })
      save_db(db)
      send_message(
          chat_id,
          f"✅ کمپین ممبر شما با موفقیت ثبت شد!\nهزینه کسر شده: {total_cost}"
          " سکه.",
      )
    else:
      send_message(
          chat_id,
          "❌ فرمت دستور نادرست است. مثال:\n/order @my_channel 100",
      )

  elif text == "/support" or text == "پشتیبانی":
    send_message(
        chat_id,
        "📞 **پشتیبانی و راهنما:**\nراه ارتباطی: @kia_karfarma\nراهنمای کار با"
        " ربات در مینی‌اپ و منوها موجود است.",
    )

  # --- پنل ادمین ---
  elif chat_id == ADMIN_ID:
    if text.startswith("/broadcast"):
      msg_text = text.replace("/broadcast", "").strip()
      if msg_text:
        count = 0
        for uid in db["users"]:
          send_message(uid, f"📢 **اطلاعیه ادمین:**\n\n{msg_text}")
          count += 1
        send_message(chat_id, f"✅ پیام همگانی به {count} کاربر ارسال شد.")

    elif text.startswith("/makecode"):
      # فرمت: /makecode [کد] | [سکه] | [ظرفیت]
      try:
        content = text.replace("/makecode", "").strip()
        parts = [p.strip() for p in content.split("|")]
        code, reward, capacity = parts[0], int(parts[1]), int(parts[2])
        db["promo_codes"][code] = {
            "reward": reward,
            "uses": capacity,
            "claimed_by": [],
        }
        save_db(db)
        send_message(
            chat_id,
            f"✅ کد هدیه `{code}` با پاداش {reward} سکه و ظرفیت {capacity} ساخته"
            " شد.",
        )
      except Exception as e:
        send_message(
            chat_id,
            "❌ فرمت ساخت کد نادرست است. مثال:\n/makecode EID1405 | 50 | 10",
        )


# --- ترد Keep-Alive ---
def keep_alive_worker():
  render_url = os.environ.get("RENDER_EXTERNAL_URL")
  if not render_url:
    return
  while True:
    try:
      requests.get(render_url)
    except:
      pass
    time.sleep(180)


if __name__ == "__main__":
  t_polling = threading.Thread(target=bale_polling, daemon=True)
  t_polling.start()

  t_keep = threading.Thread(target=keep_alive_worker, daemon=True)
  t_keep.start()

  port = int(os.environ.get("PORT", 5000))
  app.run(host="0.0.0.0", port=port)
