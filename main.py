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


# جدول المستخدمين
class User(Base):
  __tablename__ = "users"
  id = Column(Integer, primary_key=True, index=True)
  email = Column(String, unique=True, index=True)
  name = Column(String)
  password_hash = Column(String, nullable=True)
  is_admin = Column(Boolean, default=False)
  is_active = Column(Boolean, default=True)


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


# جدول الأجهزة (ESP32) لإدارة حالة القفل وأوامر الفتح عن بعد
class Device(Base):
  __tablename__ = "devices"
  id = Column(Integer, primary_key=True, index=True)
  device_id = Column(String, unique=True, index=True)  # معرف قفل الباب أو الـ ESP32
  unlock_requested = Column(Boolean, default=False)  # هل طلب المستخدم الفتح عن بعد؟
  is_online = Column(Boolean, default=True)


# إنشاء الجداول
Base.metadata.create_all(bind=engine)


def get_db():
  db = SessionLocal()
  try:
    yield db
  finally:
    db.close()


# ==============================================================================
# 2. إعداد المتغيرات البيئية والتكوين
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

app = FastAPI(
    title="Smart Lock SaaS Platform",
    description=(
        "Advanced SaaS Backend with DB, Schedules, Permissions & Remote Unlock"
    ),
    version="2.1.0",
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
      ],
  }


# ==============================================================================
# 4. مسارات المصادقة وتسجيل الدخول
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
    user = User(email=email, name=name, is_admin=is_admin, is_active=True)
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


# ==============================================================================
# 5. مسارات أجهزة ESP32 (التحقق من البطاقات والأوامر عن بعد)
# ==============================================================================
@app.get("/api/cards/check")
async def check_card_access(card_id: str, db: Session = Depends(get_db)):
  """فحص البطاقة الواردة من ESP32 والتحقق من صلاحيتها"""
  card = db.query(Card).filter(Card.card_id == card_id).first()

  if not card or not card.is_active:
    return JSONResponse(
        status_code=403,
        content={"access": False, "message": "Access Denied: Card Inactive"},
    )

  user = db.query(User).filter(User.id == card.user_id).first()
  if not user or not user.is_active:
    return JSONResponse(
        status_code=403,
        content={"access": False, "message": "Access Denied: User Blocked"},
    )

  if card.is_temporary and card.expiry_time:
    if datetime.now() > card.expiry_time:
      return JSONResponse(
          status_code=403,
          content={
              "access": False,
              "message": "Access Denied: Temporary Card Expired",
          },
      )

  current_hour = datetime.now().hour
  if not (card.start_hour <= current_hour < card.end_hour):
    return JSONResponse(
        status_code=403,
        content={
            "access": False,
            "message": "Access Denied: Outside Work Hours",
        },
    )

  return JSONResponse(
      status_code=200,
      content={
          "access": True,
          "message": "Access Granted",
          "user_name": user.name,
          "card_id": card_id,
      },
  )


@app.get("/api/device/{device_id}/poll-command")
async def poll_remote_command(device_id: str, db: Session = Depends(get_db)):
  """
  يستعلم جهاز ESP32 دورياً (كل بضع ثوانٍ) لمعرفة
  ما إذا كان هناك أمر فتح صدر من التطبيق عن بعد
  """
  device = db.query(Device).filter(Device.device_id == device_id).first()

  if device and device.unlock_requested:
    # إعادة تعيين الحالة فور قراءتها لكي يفتح الباب مرة واحدة فقط
    device.unlock_requested = False
    db.commit()
    return {"command": "UNLOCK"}

  return {"command": "IDLE"}


# ==============================================================================
# 6. مسارات التحكم والإدارة (للأمشرف أو التطبيق)
# ==============================================================================
@app.post("/api/device/{device_id}/remote-unlock")
async def trigger_remote_unlock(device_id: str, db: Session = Depends(get_db)):
  """
  زر الفتح عن بعد: يضغط المستخدم في التطبيق على 'فتح الباب'
  فيقوم هذا المسار بتغيير حالة الجهاز ليتم فتح القفل فوراً عند استعلام ESP32 القادم
  """
  device = db.query(Device).filter(Device.device_id == device_id).first()
  if not device:
    # إنشاء السجل تلقائياً في حال لم يكن مسجلاً
    device = Device(device_id=device_id, unlock_requested=True)
    db.add(device)
  else:
    device.unlock_requested = True

  db.commit()
  return {
      "status": "success",
      "message": "تم إرسال أمر الفتح عن بعد إلى القفل بنجاح",
  }


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
async def toggle_user_status(user_id: int, is_active: bool, db: Session = Depends(get_db)):
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
