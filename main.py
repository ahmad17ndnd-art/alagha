from datetime import datetime
import os
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
import httpx
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
import uvicorn

# ==============================================================================
# 1. إعداد قاعدة البيانات (Database Setup - SQLite & SQLAlchemy)
# ==============================================================================
DATABASE_URL = "sqlite:///./smart_lock.db"
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# جدول المستخدمين (مع إضافات إعدادات الإشعارات وتيليجرام)
class User(Base):
  __tablename__ = "users"
  id = Column(Integer, primary_key=True, index=True)
  email = Column(String, unique=True, index=True)
  name = Column(String)
  password_hash = Column(String, nullable=True)
  is_admin = Column(Boolean, default=False)
  is_active = Column(Boolean, default=True)
  telegram_chat_id = Column(
      String, nullable=True
  )  # معرف تيليجرام الخاص بالمستخدم
  notifications_enabled = Column(Boolean, default=True)  # تفعيل/إيقاف الإشعارات
  sound_enabled = Column(Boolean, default=True)  # تفعيل/إيقاف صوت الإشعار


# جدول الكروت والصلاحيات
class Card(Base):
  __tablename__ = "cards"
  id = Column(Integer, primary_key=True, index=True)
  card_id = Column(String, unique=True, index=True)
  user_id = Column(Integer, ForeignKey("users.id"))
  is_temporary = Column(Boolean, default=False)
  expiry_time = Column(DateTime, nullable=True)
  start_hour = Column(Integer, default=0)
  end_hour = Column(Integer, default=24)
  is_active = Column(Boolean, default=True)


# جدول الأجهزة (ESP32)
class Device(Base):
  __tablename__ = "devices"
  id = Column(Integer, primary_key=True, index=True)
  device_id = Column(String, unique=True, index=True)
  unlock_requested = Column(Boolean, default=False)
  is_online = Column(Boolean, default=True)


# جدول سجل الحركات
class AccessLog(Base):
  __tablename__ = "access_logs"
  id = Column(Integer, primary_key=True, index=True)
  card_id = Column(String)
  user_name = Column(String)
  status_message = Column(String)
  timestamp = Column(DateTime, default=datetime.now)


# إنشاء الجداول
Base.metadata.create_all(bind=engine)


def get_db():
  db = SessionLocal()
  try:
    yield db
  finally:
    db.close()


# ==============================================================================
# 2. إعداد المتغيرات البيئية والتكوين والدوال المساعدة
# ==============================================================================
CONFIG = {
    "PORT": 3000,
    "SECRET_KEY": "super_secret_saas_key_2026_python",
    "GOOGLE_CLIENT_ID": (
        "034269901652-sftbqggk6morgtebdmchkubbt4ohuuci.apps.googleusercontent.com"
    ),
    "GOOGLE_CLIENT_SECRET": "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",
    "GOOGLE_REDIRECT_URI": "http://localhost:3000/auth/google/callback",
    "SUPER_ADMIN_EMAIL": "ahmad17ndnd@gmail.com",
    "TELEGRAM_BOT_TOKEN": "8915690581:AAH15aBE6EvmjQQcRN1Pdyjrh7uQIJijkmo",
}


async def send_telegram_alert(
    chat_id: str, message: str, sound_enabled: bool = True
):
  """دالة لإرسال إشعارات تيليجرام مع التحكم بالصوت"""
  if not chat_id:
    return
  url = f"https://api.telegram.org/bot{CONFIG['TELEGRAM_BOT_TOKEN']}/sendMessage"
  payload = {
      "chat_id": chat_id,
      "text": message,
      "disable_notification": (
          not sound_enabled
      ),  # إذا كان الصوت مفصولاً، يُرسل إشعار صامت
  }
  async with httpx.AsyncClient() as client:
    try:
      await client.post(url, json=payload)
    except Exception as e:
      print(f"Telegram Error: {e}")


app = FastAPI(
    title="Smart Lock SaaS Platform",
    description="Advanced SaaS Backend with Telegram Alerts & Sound Controls",
    version="2.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================================================
# 3. المسار الرئيسي (Root Endpoint)
# ==============================================================================
@app.get("/")
async def root():
  return {
      "status": "Online",
      "system": "Smart Lock SaaS Platform Pro",
      "features": [
          "Database Integration",
          "User Block/Allow",
          "Temporary Cards & Expiry",
          "Work Hours Schedule",
          "Password Management",
          "Remote Door Unlock",
          "Access Logs & History",
          "Telegram Alerts with Sound & Notification Controls",
      ],
  }


# ==============================================================================
# 4. مسارات المصادقة وتسجيل الدخول وتطبيقات الإشعارات
# ==============================================================================
@app.get("/auth/google/login")
async def google_login():
  google_auth_url = (
      "https://accounts.google.com/o/oauth2/v2/auth?"
      f"client_id={CONFIG['GOOGLE_CLIENT_ID']}&"
      f"redirect_uri={CONFIG['GOOGLE_REDIRECT_URI']}&"
      "response_type=code&"
      "scope=openid%20email%20profile"
  )
  return RedirectResponse(url=google_auth_url)


@app.get("/auth/google/callback")
async def google_callback(code: str, db: Session = Depends(get_db)):
  token_url = "https://oauth2.googleapis.com/token"
  data = {
      "client_id": CONFIG["GOOGLE_CLIENT_ID"],
      "client_secret": CONFIG["GOOGLE_CLIENT_SECRET"],
      "code": code,
      "grant_type": "authorization_code",
      "redirect_uri": CONFIG["GOOGLE_REDIRECT_URI"],
  }

  async with httpx.AsyncClient() as client:
    token_response = await client.post(token_url, data=data)
    token_json = token_response.json()

    if "error" in token_json:
      raise HTTPException(
          status_code=400, detail=token_json.get("error_description")
      )

    access_token = token_json.get("access_token")
    user_info_response = await client.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    user_data = user_info_response.json()

  email = user_data.get("email")
  name = user_data.get("name")
  is_admin = email == CONFIG["SUPER_ADMIN_EMAIL"]

  user = db.query(User).filter(User.email == email).first()
  if not user:
    user = User(
        email=email,
        name=name,
        is_admin=is_admin,
        is_active=True,
        notifications_enabled=True,
        sound_enabled=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

  if not user.is_active:
    raise HTTPException(status_code=403, detail="هذا الحساب محظور من قبل الإدارة")

  return {
      "status": "success",
      "message": "تم تسجيل الدخول بنجاح عبر Google",
      "user_id": user.id,
      "is_super_admin": user.is_admin,
      "user_details": {
          "name": user.name,
          "email": user.email,
          "profile_pic": user_data.get("picture"),
          "telegram_chat_id": user.telegram_chat_id,
          "notifications_enabled": user.notifications_enabled,
          "sound_enabled": user.sound_enabled,
      },
  }


@app.post("/auth/set-password")
async def set_password(email: str, new_password: str, db: Session = Depends(get_db)):
  user = db.query(User).filter(User.email == email).first()
  if not user:
    raise HTTPException(status_code=404, detail="المستخدم غير موجود")

  user.password_hash = new_password
  db.commit()
  return {"status": "success", "message": "تم تحديث كلمة المرور بنجاح"}


@app.post("/api/users/notification-settings")
async def update_notification_settings(
    user_id: int,
    notifications_enabled: bool,
    sound_enabled: bool,
    db: Session = Depends(get_db),
):
  """ميزة من التطبيق: تشغيل/إيقاف الإشعارات أو إيقاف الصوت فقط"""
  user = db.query(User).filter(User.id == user_id).first()
  if not user:
    raise HTTPException(status_code=404, detail="المستخدم غير موجود")

  user.notifications_enabled = notifications_enabled
  user.sound_enabled = sound_enabled
  db.commit()
  return {
      "status": "success",
      "message": "تم تحديث إعدادات الإشعارات بنجاح",
  }


@app.post("/api/users/link-telegram")
async def link_telegram(user_id: int, telegram_chat_id: str, db: Session = Depends(get_db)):
  """ربط حساب المستخدم بمعرف التيليجرام الخاص به لاستلام التنبيهات"""
  user = db.query(User).filter(User.id == user_id).first()
  if not user:
    raise HTTPException(status_code=404, detail="المستخدم غير موجود")

  user.telegram_chat_id = telegram_chat_id
  db.commit()
  return {"status": "success", "message": "تم ربط حساب Telegram بنجاح"}


# ==============================================================================
# 5. مسارات أجهزة ESP32 (التحقق وإرسال تنبيهات تيليجرام الفورية عند الرفض)
# ==============================================================================
async def notify_admins_or_user(db: Session, error_msg: str, card_id: str):
  """دالة مساعدة لإرسال إشعارات فورية لكل المشرفين أو المستخدمين المفعلين لديهم الإشعارات"""
  admins = (
      db.query(User)
      .filter(
          (User.is_admin == True) & (User.notifications_enabled == True)
      )
      .all()
  )
  alert_text = (
      f"🚨 تنبيه أمني خطير!\nمحاولة دخول مرفوضة.\n- سبب الرفض: {error_msg}\n- رقم"
      f" الكرت: {card_id}\n- الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
  )

  for admin in admins:
    if admin.telegram_chat_id:
      await send_telegram_alert(
          admin.telegram_chat_id, alert_text, admin.sound_enabled
      )


@app.get("/api/cards/check")
async def check_card_access(card_id: str, db: Session = Depends(get_db)):
  """فحص البطاقة وتسجيل الحركة مع إرسال تنبيه فوري عبر تيليجرام عند الرفض"""

  card = db.query(Card).filter(Card.card_id == card_id).first()

  if not card or not card.is_active:
    error_reason = "Card Inactive / Not Found"
    log_entry = AccessLog(
        card_id=card_id,
        user_name="مجهول / غير مسجل",
        status_message=f"Access Denied: {error_reason}",
    )
    db.add(log_entry)
    db.commit()

    # إرسال إشعار تيليجرام فوري
    await notify_admins_or_user(db, error_reason, card_id)

    return JSONResponse(
        status_code=403, content={"access": False, "message": error_reason}
    )

  user = db.query(User).filter(User.id == card.user_id).first()
  user_name = user.name if user else "مستخدم غير معروف"

  if not user or not user.is_active:
    error_reason = "User Blocked"
    log_entry = AccessLog(
        card_id=card_id, user_name=user_name, status_message=error_reason
    )
    db.add(log_entry)
    db.commit()
    await notify_admins_or_user(db, error_reason, card_id)
    return JSONResponse(
        status_code=403, content={"access": False, "message": error_reason}
    )

  if card.is_temporary and card.expiry_time:
    if datetime.now() > card.expiry_time:
      error_reason = "Temporary Card Expired"
      log_entry = AccessLog(
          card_id=card_id, user_name=user_name, status_message=error_reason
      )
      db.add(log_entry)
      db.commit()
      await notify_admins_or_user(db, error_reason, card_id)
      return JSONResponse(
          status_code=403, content={"access": False, "message": error_reason}
      )

  current_hour = datetime.now().hour
  if not (card.start_hour <= current_hour < card.end_hour):
    error_reason = "Outside Work Hours"
    log_entry = AccessLog(
        card_id=card_id, user_name=user_name, status_message=error_reason
      )
    db.add(log_entry)
    db.commit()
    await notify_admins_or_user(db, error_reason, card_id)
    return JSONResponse(
        status_code=403, content={"access": False, "message": error_reason}
    )

  # نجاح الدخول
  log_entry = AccessLog(
      card_id=card_id,
      user_name=user_name,
      status_message="Access Granted (Success)",
  )
  db.add(log_entry)
  db.commit()

  return JSONResponse(
      status_code=200,
      content={
          "access": True,
          "message": "Access Granted",
          "user_name": user_name,
          "card_id": card_id,
      },
  )


# ==============================================================================
# 6. مسارات الإدارة والتليجرام Webhook
# ==============================================================================
@app.get("/api/logs")
async def get_access_logs(db: Session = Depends(get_db)):
  logs = db.query(AccessLog).order_by(AccessLog.timestamp.desc()).all()
  return {
      "status": "success",
      "total_logs": len(logs),
      "logs": [
          {
              "id": log.id,
              "user_name": log.user_name,
              "card_id": log.card_id,
              "status": log.status_message,
              "timestamp": log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
          }
          for log in logs
      ],
  }


@app.post("/telegram/webhook")
async def telegram_webhook(request: Request, db: Session = Depends(get_db)):
  """استقبال رسائل تيليجرام (يمكن للمستخدم إرسال /start لربط حسابه تلقائياً)"""
  data = await request.json()
  if "message" in data:
    chat_id = data["message"]["chat"]["id"]
    text = data["message"].get("text", "")

    if text == "/start":
      async with httpx.AsyncClient() as client:
        await client.post(
            f"https://api.telegram.org/bot{CONFIG['TELEGRAM_BOT_TOKEN']}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": (
                    "مرحباً بك في نظام Smart Lock. لاستلام التنبيهات الأمنية،"
                    " يرجى ربط حسابك عبر التطبيق أو تزويدنا برمزك التعريفي"
                    f" (Chat ID الخاص بك هو: {chat_id})."
                ),
            },
        )
  return {"status": "ok"}


@app.post("/api/device/{device_id}/poll-command")
async def poll_remote_command(device_id: str, db: Session = Depends(get_db)):
  device = db.query(Device).filter(Device.device_id == device_id).first()
  if device and device.unlock_requested:
    device.unlock_requested = False
    db.commit()
    return {"command": "UNLOCK"}
  return {"command": "IDLE"}


@app.post("/api/device/{device_id}/remote-unlock")
async def trigger_remote_unlock(device_id: str, db: Session = Depends(get_db)):
  device = db.query(Device).filter(Device.device_id == device_id).first()
  if not device:
    device = Device(device_id=device_id, unlock_requested=True)
    db.add(device)
  else:
    device.unlock_requested = True
  db.commit()
  return {"status": "success", "message": "تم إرسال أمر الفتح عن بعد بنجاح"}


@app.post("/api/cards/add")
async def add_card(
    user_id: int,
    card_id: str,
    is_temporary: bool = False,
    expiry_time: datetime = None,
    start_hour: int = 0,
    end_hour: int = 24,
    db: Session = Depends(get_db),
):
  existing_card = db.query(Card).filter(Card.card_id == card_id).first()
  if existing_card:
    raise HTTPException(status_code=400, detail="هذه البطاقة مسجلة مسبقاً")

  new_card = Card(
      user_id=user_id,
      card_id=card_id,
      is_temporary=is_temporary,
      expiry_time=expiry_time,
      start_hour=start_hour,
      end_hour=end_hour,
      is_active=True,
  )
  db.add(new_card)
  db.commit()
  return {"status": "success", "message": "تمت إضافة البطاقة وتفعيلها بنجاح"}


@app.post("/api/users/toggle-status")
async def toggle_user_status(user_id: int, is_active: bool, db: Session = Depends(get_db):
  user = db.query(User).filter(User.id == user_id).first()
  if not user:
    raise HTTPException(status_code=404, detail="المستخدم غير موجود")
  user.is_active = is_active
  db.commit()
  status_text = "تم تفعيل" if is_active else "تم حظر"
  return {"status": "success", "message": f"{status_text} المستخدم بنجاح"}


# ==============================================================================
# 7. نقطة تشغيل السيرفر
# ==============================================================================
if __name__ == "__main__":
  print(f"🚀 Starting Smart Lock SaaS Pro Server on port {CONFIG['PORT']}...")
  uvicorn.run(app, host="0.0.0.0", port=CONFIG["PORT"])
