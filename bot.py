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
TOKEN = "GAPGPTMASKTOKENi2n8eq1fqacX0X"  # توکن ربات بله
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
    }
    save_db(default_data)
    return default_data
  with db_lock:
    try:
      with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except:
      return {"users": {}, "campaigns": [], "promo_codes": {}}


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


# --- مینی‌اپ گرافیکی و تعاملی (Flask) ---
@app.route("/")
def home():
  return "Bale Membergir Mini-App is Running! 🚀"


@app.route("/webapp", methods=["GET", "POST"])
def webapp():
  chat_id = request.args.get("chat_id")
  if not chat_id:
    chat_id = str(ADMIN_ID)

  db = load_db()
  str_chat_id = str(chat_id)

  # ثبت‌نام خودکار کاربر اگر وجود نداشت
  if str_chat_id not in db["users"]:
    db["users"][str_chat_id] = {
        "nickname": f"کاربر_{chat_id}",
        "coins": 50,
        "ref_by": None,
        "last_spin": None,
        "visited_campaigns": [],
    }
    save_db(db)

  user = db["users"][str_chat_id]
  if "visited_campaigns" not in user:
    user["visited_campaigns"] = []

  message = ""

  if request.method == "POST":
    action = request.form.get("action")

    if action == "setname":
      new_name = request.form.get("nickname", "").strip()
      if new_name:
        user["nickname"] = new_name
        save_db(db)
        message = "✅ نام مستعار با موفقیت تغییر کرد!"

    elif action == "spin":
      last_spin = user.get("last_spin")
      now = datetime.now()
      can_spin = True
      if last_spin:
        last_time = datetime.fromisoformat(last_spin)
        if now - last_time < timedelta(hours=24):
          can_spin = False

      if can_spin:
        reward = random.randint(10, 100)
        user["coins"] += reward
        user["last_spin"] = now.isoformat()
        save_db(db)
        message = f"🎉 تبریک! {reward} سکه از گردونه جایزه گرفتی!"
      else:
        message = "⏳ گردونه شانس هر ۲۴ ساعت یک‌بار قابل چرخش است!"

    elif action == "visit_campaign":
      try:
        camp_idx = int(request.form.get("campaign_index", -1))
      except:
        camp_idx = -1

      campaigns = db.get("campaigns", [])
      if 0 <= camp_idx < len(campaigns):
        target_camp = campaigns[camp_idx]

        if target_camp["user_id"] == str_chat_id:
          message = "❌ شما نمی‌توانید کانال خودتان را بازدید کنید."
        elif camp_idx in user["visited_campaigns"]:
          message = "❌ شما قبلاً پاداش این کانال را دریافت کرده‌اید."
        else:
          if target_camp.get("delivered", 0) < target_camp.get("requested", 0):
            user["visited_campaigns"].append(camp_idx)
            user["coins"] += 5
            target_camp["delivered"] += 1
            save_db(db)
            message = "✅ تبریک! ۵ سکه بابت بازدید از کانال دریافت کردی."
          else:
            message = "❌ ظرفیت این کمپین به اتمام رسیده است."
      else:
        message = "❌ کمپین مورد نظر یافت نشد."

    elif action == "promo":
      code = request.form.get("code", "").strip()
      promo_codes = db.get("promo_codes", {})
      if code in promo_codes:
        p_data = promo_codes[code]
        if p_data["uses"] > 0 and str_chat_id not in p_data["claimed_by"]:
          p_data["uses"] -= 1
          p_data["claimed_by"].append(str_chat_id)
          user["coins"] += p_data["reward"]
          save_db(db)
          message = f"✅ کد هدیه اعمال شد! {p_data['reward']} سکه اضافه شد."
        else:
          message = "❌ این کد هدیه منقضی شده یا قبلاً استفاده شده است."
      else:
        message = "❌ کد هدیه نامعتبر است."

    elif action == "order":
      ch_link = request.form.get("channel", "").strip()
      try:
        count = int(request.form.get("count", 0))
      except:
        count = 0

      cost = count * 2
      if count >= 10 and ch_link:
        if user["coins"] >= cost:
          user["coins"] -= cost
          db["campaigns"].append({
              "user_id": str_chat_id,
              "channel": ch_link,
              "requested": count,
              "delivered": 0,
          })
          save_db(db)
          message = (
              f"✅ کمپین ممبر با موفقیت ثبت شد! {cost} سکه از حساب شما کسر گردید."
          )
        else:
          message = "❌ موجودی سکه شما برای این تعداد ممبر کافی نیست!"
      else:
        message = "❌ حداقل تعداد سفارش باید ۱۰ ممبر باشد."

  html_template = """
    <!DOCTYPE html>
    <html lang="fa" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>مینی‌اپ ممبرگیر بله</title>
        <style>
            body { font-family: Tahoma, sans-serif; background: #f0f2f5; margin: 0; padding: 10px; color: #333; }
            .card { background: #fff; padding: 15px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); margin-bottom: 12px; }
            h2 { color: #007bff; margin-top: 0; font-size: 16px; border-bottom: 2px solid #f0f2f5; padding-bottom: 8px; }
            .info { font-size: 13px; color: #555; line-height: 1.5; }
            .btn { background: #007bff; color: white; border: none; padding: 10px; border-radius: 8px; width: 100%; font-size: 14px; cursor: pointer; margin-top: 8px; font-weight: bold;}
            .btn-success { background: #28a745; }
            .btn-warning { background: #ffc107; color: #333; }
            .btn-sm { padding: 6px; font-size: 12px; margin-top: 4px; }
            input, select { width: 100%; padding: 8px; margin-top: 6px; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; font-family: Tahoma; }
            .highlight { color: #e67e22; font-weight: bold; }
            .alert { background: #d4edda; color: #155724; padding: 10px; border-radius: 8px; margin-bottom: 12px; font-size: 13px; text-align: center; }
            .channel-item { background: #f8f9fa; padding: 8px; border-radius: 6px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; font-size: 13px; }
        </style>
    </head>
    <body>
        {% if message %}
        <div class="alert">{{ message }}</div>
        {% endif %}

        <div class="card">
            <h2>👤 حساب کاربری</h2>
            <div class="info">
                <p><b>نام مستعار:</b> {{ user.get('nickname') }}</p>
                <p><b>موجودی سکه:</b> <span class="highlight">🪙 {{ user.get('coins') }} سکه</span></p>
                <p><b>آیدی عددی:</b> {{ chat_id }}</p>
                
                <form method="POST">
                    <input type="hidden" name="action" value="setname">
                    <input type="text" name="nickname" placeholder="تغییر نام مستعار..." required>
                    <button type="submit" class="btn">ثبت نام مستعار</button>
                </form>
            </div>
        </div>

        <div class="card">
            <h2>🎁 کسب درآمد و سکه رایگان</h2>
            <div class="info">
                <p><b>لینک دعوت شما (زیرمجموعه‌گیری):</b></p>
                <input type="text" readonly value="https://ble.ir/bot_username?start={{ chat_id }}">
                <p style="margin-top:6px; font-size:12px; color:#777;">با دعوت هر دوست، ۲۰ سکه هدیه بگیر!</p>
                
                <form method="POST" style="margin-top: 8px;">
                    <input type="hidden" name="action" value="spin">
                    <button type="submit" class="btn btn-warning">🎡 چرخش گردونه شانس (روزانه)</button>
                </form>
            </div>
        </div>

        <div class="card">
            <h2>📢 بازدید از کانال‌های کاربران و دریافت سکه</h2>
            <div class="info" style="margin-bottom: 8px;">عضو شو و ۵ سکه جایزه بگیر:</div>
            {% set active_campaigns = [] %}
            {% for idx in range(campaigns|length) %}
                {% if campaigns[idx].delivered < campaigns[idx].requested and campaigns[idx].user_id != chat_id %}
                    {% set _ = active_campaigns.append((idx, campaigns[idx])) %}
                {% endif %}
            {% endfor %}

            {% if active_campaigns|length == 0 %}
            <div style="text-align: center; color: #777; font-size: 13px; padding: 10px;">در حال حاضر کانالی برای بازدید وجود ندارد.</div>
            {% else %}
                {% for idx, camp in active_campaigns %}
                <div class="channel-item">
                    <div>
                        <b>{{ camp.channel }}</b> <span style="color: #27ae60;">(+5 سکه)</span>
                        <div style="font-size: 11px; color: #888;">پیشرفت: {{ camp.delivered }}/{{ camp.requested }}</div>
                    </div>
                    <div>
                        {% if idx in user.get('visited_campaigns', []) %}
                        <span style="font-size:11px; color:#888;">✅ دریافت شده</span>
                        {% else %}
                        <form method="POST" style="display:inline;">
                            <input type="hidden" name="action" value="visit_campaign">
                            <input type="hidden" name="campaign_index" value="{{ idx }}">
                            <button type="submit" class="btn btn-sm btn-success">دریافت پاداش</button>
                        </form>
                        {% endif %}
                    </div>
                </div>
                {% endfor %}
            {% endif %}
        </div>

        <div class="card">
            <h2>🎟️ کد هدیه</h2>
            <form method="POST">
                <input type="hidden" name="action" value="promo">
                <input type="text" name="code" placeholder="مثال: KIALAND100" required>
                <button type="submit" class="btn btn-success">ثبت و دریافت جایزه</button>
            </form>
        </div>

        <div class="card">
            <h2>🚀 ثبت سفارش ممبر</h2>
            <div class="info" style="margin-bottom:8px; color:#e74c3c;">هر ممبر معادل ۲ سکه است (حداقل ۱۰ ممبر).</div>
            <form method="POST">
                <input type="hidden" name="action" value="order">
                <input type="text" name="channel" placeholder="آیدی یا لینک کانال (مثال: @my_channel)" required>
                <input type="number" name="count" placeholder="تعداد ممبر درخواستی (مثال: 50)" min="10" required>
                <button type="submit" class="btn">ثبت سفارش و کسر سکه</button>
            </form>
        </div>

        <div class="card" style="text-align: center; color: #777; font-size: 12px;">
            پشتیبانی: @kia_karfarma 💻
        </div>
    </body>
    </html>
    """
  return render_template_string(
      html_template,
      user=user,
      chat_id=chat_id,
      campaigns=db.get("campaigns", []),
      message=message,
  )


# --- ترد Polling بله (هماهنگ‌سازی کامل دستورات چت با مینی‌اپ) ---
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

  # ثبت‌نام خودکار
  if str_chat_id not in db["users"]:
    parts = text.split()
    ref_id = parts[1] if len(parts) > 1 and text.startswith("/start") else None

    db["users"][str_chat_id] = {
        "nickname": f"کاربر_{chat_id}",
        "coins": 50,
        "ref_by": ref_id,
        "last_spin": None,
        "visited_campaigns": [],
    }

    if ref_id and ref_id in db["users"] and ref_id != str_chat_id:
      db["users"][ref_id]["coins"] += 20

    save_db(db)

  user = db["users"][str_chat_id]
  if "visited_campaigns" not in user:
    user["visited_campaigns"] = []

  if text.startswith("/start"):
    webapp_url = (
        f"https://member-mini-app.onrender.com/webapp?chat_id={chat_id}"
    )
    keyboard = {
        "inline_keyboard": [[{
            "text": "🚀 ورود به مینی‌اپ ممبرگیر",
            "url": webapp_url,
        }]]
    }
    send_message(
        chat_id,
        f"سلام {user.get('nickname')} عزیز! 🌺\nموجودی فعلی شما: 🪙"
        f" {user.get('coins')} سکه\n\nبرای دسترسی به مینی‌اپ و مدیریت کامل، روی"
        " دکمه زیر بزن:",
        reply_markup=keyboard,
    )

  elif text.startswith("/profile"):
    send_message(
        chat_id,
        f"👤 **پروفایل شما:**\n\n- نام مستعار: {user.get('nickname')}\n- موجودی"
        f" سکه: 🪙 {user.get('coins')}\n- آیدی عددی: {chat_id}",
    )

  elif text.startswith("/setname"):
    parts = text.split(maxsplit=1)
    if len(parts) > 1:
      new_name = parts[1].strip()
      user["nickname"] = new_name
      save_db(db)
      send_message(chat_id, f"✅ نام مستعار شما به «{new_name}» تغییر یافت.")
    else:
      send_message(
          chat_id, "❌ لطفاً نام جدید را وارد کنید.\nمثال: `/setname کیا`",
      )

  elif text.startswith("/spin"):
    last_spin = user.get("last_spin")
    now = datetime.now()
    can_spin = True
    if last_spin:
      last_time = datetime.fromisoformat(last_spin)
      if now - last_time < timedelta(hours=24):
        can_spin = False

    if can_spin:
      reward = random.randint(10, 100)
      user["coins"] += reward
      user["last_spin"] = now.isoformat()
      save_db(db)
      send_message(
          chat_id, f"🎉 تبریک! {reward} سکه از گردونه شانس جایزه گرفتی!",
      )
    else:
      send_message(
          chat_id, "⏳ گردونه شانس هر ۲۴ ساعت یک‌بار قابل چرخش است!",
      )

  elif text.startswith("/promo"):
    parts = text.split(maxsplit=1)
    if len(parts) > 1:
      code = parts[1].strip()
      promo_codes = db.get("promo_codes", {})
      if code in promo_codes:
        p_data = promo_codes[code]
        if p_data["uses"] > 0 and str_chat_id not in p_data["claimed_by"]:
          p_data["uses"] -= 1
          p_data["claimed_by"].append(str_chat_id)
          user["coins"] += p_data["reward"]
          save_db(db)
          send_message(
              chat_id,
              f"✅ کد هدیه اعمال شد! {p_data['reward']} سکه به شما اضافه شد.",
          )
        else:
          send_message(
              chat_id, "❌ این کد هدیه منقضی شده یا قبلاً استفاده شده است.",
          )
      else:
        send_message(chat_id, "❌ کد هدیه نامعتبر است.")
    else:
      send_message(
          chat_id,
          "❌ لطفاً کد هدیه را وارد کنید.\nمثال: `/promo KIALAND100`",
      )

  elif text.startswith("/order"):
    parts = text.split()
    if len(parts) == 3:
      ch_link = parts[1].strip()
      try:
        count = int(parts[2])
        cost = count * 2
        if count >= 10:
          if user["coins"] >= cost:
            user["coins"] -= cost
            db["campaigns"].append({
                "user_id": str_chat_id,
                "channel": ch_link,
                "requested": count,
                "delivered": 0,
            })
            save_db(db)
            send_message(
                chat_id,
                f"✅ سفارش ممبر ثبت شد! {cost} سکه از حساب شما کسر گردید.",
            )
          else:
            send_message(chat_id, "❌ موجودی سکه شما برای این سفارش کافی نیست!")
        else:
          send_message(chat_id, "❌ حداقل تعداد سفارش باید ۱۰ ممبر باشد.")
      except ValueError:
        send_message(chat_id, "❌ فرمت تعداد ممبر نامعتبر است.")
    else:
      send_message(
          chat_id,
          "❌ فرمت دستور نادرست است.\nاستفاده: `/order [لینک_کانال] [تعداد]`",
      )

  elif text.startswith("/transfer"):
    parts = text.split()
    if len(parts) == 3:
      try:
        target_id = parts[1].strip()
        amount = int(parts[2])

        if target_id == str_chat_id:
          send_message(chat_id, "❌ نمی‌توانید به خودتان سکه انتقال دهید!")
        elif amount <= 0:
          send_message(chat_id, "❌ مقدار سکه باید بزرگ‌تر از صفر باشد.")
        elif user["coins"] < amount:
          send_message(chat_id, "❌ موجودی سکه شما کافی نیست!")
        else:
          if target_id not in db["users"]:
            send_message(
                chat_id, "❌ کاربر مورد نظر در ربات ثبت‌نام نکرده است.",
            )
          else:
            user["coins"] -= amount
            db["users"][target_id]["coins"] += amount
            save_db(db)
            send_message(
                chat_id,
                f"✅ موفقیت! {amount} سکه به کاربر {target_id} منتقل شد.",
            )
            send_message(
                target_id,
                f"🎁 شما مبلغ {amount} سکه از کاربر {str_chat_id} دریافت کردید!",
            )
      except ValueError:
        send_message(chat_id, "❌ فرمت مقدار سکه نامعتبر است.")
    else:
      send_message(
          chat_id,
          "❌ فرمت دستور نادرست است.\nاستفاده: `/transfer [آیدی_مقصد] [تعداد]`",
      )

  elif text == "/support" or text == "پشتیبانی":
    send_message(
        chat_id,
        "💬 برای ارتباط با پشتیبانی، به آیدی زیر پیام دهید:\n👉 @kia_karfarma",
    )

  # --- پنل ادمین ---
  elif chat_id == ADMIN_ID:
    if text.startswith("/makecode"):
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
            f"✅ کد هدیه `{code}` با پاداش {reward} سکه ساخته شد.",
        )
      except:
        send_message(chat_id, "❌ فرمت: /makecode کد | سکه | ظرفیت")

    elif text.startswith("/broadcast"):
      msg_text = text.replace("/broadcast", "").strip()
      if msg_text:
        success_count = 0
        for uid in db["users"]:
          try:
            send_message(int(uid), f"📢 **پیام مدیریت:**\n\n{msg_text}")
            success_count += 1
          except:
            pass
        send_message(
            chat_id,
            f"✅ پیام همگانی با موفقیت به {success_count} کاربر ارسال شد.",
        )
      else:
        send_message(chat_id, "❌ متن پیام خالی است.")


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
