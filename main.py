from datetime import datetime
import os
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
import httpx
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    create_engine,
)
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
  telegram_chat_id = Column(String, nullable=True)
  notifications_enabled = Column(Boolean, default=True)
  sound_enabled = Column(Boolean, default=True)


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
    "GOOGLE_REDIRECT_URI": "https://alagha-w1e2.onrender.com/auth/google/callback",
    "SUPER_ADMIN_EMAIL": "ahmad17ndnd@gmail.com",
    "TELEGRAM_BOT_TOKEN": "8915690581:AAH15aBE6EvmjQQcRN1Pdyjrh7uQIJijkmo",
}


async def send_telegram_alert(
    chat_id: str, message: str, sound_enabled: bool = True
):
  if not chat_id:
    return
  url = f"https://api.telegram.org/bot{CONFIG['TELEGRAM_BOT_TOKEN']}/sendMessage"
  payload = {
      "chat_id": chat_id,
      "text": message,
      "disable_notification": not sound_enabled,
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
# 3. مسار حالة النظام (API Status Endpoint)
# ==============================================================================
@app.get("/api/status")
async def api_status():
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
# 4. مسارات المصادقة وتسجيل الدخول عبر Google
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

  # إعادة توجيه المستخدم للواجهة مع تمرير المعرف
  return RedirectResponse(url=f"/?logged_in=true&user_id={user.id}&name={name}")


@app.post("/api/users/notification-settings")
async def update_notification_settings(
    user_id: int,
    notifications_enabled: bool,
    sound_enabled: bool,
    db: Session = Depends(get_db),
):
  user = db.query(User).filter(User.id == user_id).first()
  if not user:
    raise HTTPException(status_code=404, detail="المستخدم غير موجود")
  user.notifications_enabled = notifications_enabled
  user.sound_enabled = sound_enabled
  db.commit()
  return {"status": "success", "message": "تم تحديث إعدادات الإشعارات بنجاح"}


@app.post("/api/users/link-telegram")
async def link_telegram(
    user_id: int, telegram_chat_id: str, db: Session = Depends(get_db)
):
  user = db.query(User).filter(User.id == user_id).first()
  if not user:
    raise HTTPException(status_code=404, detail="المستخدم غير موجود")
  user.telegram_chat_id = telegram_chat_id
  db.commit()
  return {"status": "success", "message": "تم ربط حساب Telegram بنجاح"}


# ==============================================================================
# 5. مسارات أجهزة ESP32 والتحقق والتنبيهات
# ==============================================================================
async def notify_admins_or_user(db: Session, error_msg: str, card_id: str):
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
  card = db.query(Card).filter(Card.card_id == card_id).first()
  if not card or not card.is_active:
    error_reason = "Card Inactive / Not Found"
    db.add(
        AccessLog(
            card_id=card_id,
            user_name="مجهول",
            status_message=f"Denied: {error_reason}",
        )
    )
    db.commit()
    await notify_admins_or_user(db, error_reason, card_id)
    return JSONResponse(
        status_code=403, content={"access": False, "message": error_reason}
    )

  user = db.query(User).filter(User.id == card.user_id).first()
  user_name = user.name if user else "مستخدم غير معروف"

  if not user or not user.is_active:
    error_reason = "User Blocked"
    db.add(
        AccessLog(
            card_id=card_id, user_name=user_name, status_message=error_reason
        )
    )
    db.commit()
    await notify_admins_or_user(db, error_reason, card_id)
    return JSONResponse(
        status_code=403, content={"access": False, "message": error_reason}
    )

  if card.is_temporary and card.expiry_time:
    if datetime.now() > card.expiry_time:
      error_reason = "Temporary Card Expired"
      db.add(
          AccessLog(
              card_id=card_id, user_name=user_name, status_message=error_reason
          )
      )
      db.commit()
      await notify_admins_or_user(db, error_reason, card_id)
      return JSONResponse(
          status_code=403, content={"access": False, "message": error_reason}
      )

  current_hour = datetime.now().hour
  if not (card.start_hour <= current_hour < card.end_hour):
    error_reason = "Outside Work Hours"
    db.add(
        AccessLog(
            card_id=card_id, user_name=user_name, status_message=error_reason
        )
    )
    db.commit()
    await notify_admins_or_user(db, error_reason, card_id)
    return JSONResponse(
        status_code=403, content={"access": False, "message": error_reason}
    )

  db.add(
      AccessLog(
          card_id=card_id,
          user_name=user_name,
          status_message="Access Granted",
      )
  )
  db.commit()
  return JSONResponse(
      status_code=200,
      content={
          "access": True,
          "message": "Access Granted",
          "user_name": user_name,
      },
  )


# ==============================================================================
# 6. مسارات الإدارة وسجلات الدخول والتحكم
# ==============================================================================
@app.get("/api/logs")
async def get_access_logs(db: Session = Depends(get_db)):
  logs = db.query(AccessLog).order_by(AccessLog.timestamp.desc()).all()
  return {
      "status": "success",
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
                    "مرحباً بك في نظام Smart Lock. معرف الدردشة الخاص بك هو:"
                    f" {chat_id}"
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
    expiry_hours: int = 24,
    start_hour: int = 0,
    end_hour: int = 24,
    db: Session = Depends(get_db),
):
  existing = db.query(Card).filter(Card.card_id == card_id).first()
  if existing:
    raise HTTPException(status_code=400, detail="هذه البطاقة مسجلة مسبقاً")

  expiry_time = None
  if is_temporary:
    from datetime import timedelta

    expiry_time = datetime.now() + timedelta(hours=expiry_hours)

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
  return {"status": "success", "message": "تمت إضافة وتفعيل البطاقة بنجاح"}


@app.post("/api/users/toggle-status")
async def toggle_user_status(
    user_id: int, is_active: bool, db: Session = Depends(get_db)
):
  user = db.query(User).filter(User.id == user_id).first()
  if not user:
    raise HTTPException(status_code=404, detail="المستخدم غير موجود")
  user.is_active = is_active
  db.commit()
  status_text = "تفعيل" if is_active else "حظر"
  return {"status": "success", "message": f"تم {status_text} المستخدم بنجاح"}


# ==============================================================================
# 7. واجهة المستخدم المتكاملة (SaaS Dashboard HTML)
# ==============================================================================
@app.get("/", response_class=HTMLResponse)
async def dashboard():
  return """
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>لوحة تحكم القفل الذكي SaaS Pro</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-50 font-sans min-h-screen p-4 md:p-8">
        <div class="max-w-4xl mx-auto space-y-6">
            
            <!-- رأس الصفحة وتوثيق جوجل -->
            <div class="bg-white rounded-2xl shadow-sm p-6 flex flex-col md:flex-row justify-between items-center gap-4">
                <div>
                    <h1 class="text-2xl font-bold text-gray-800">🔒 لوحة تحكم الأقفال الذكية</h1>
                    <p class="text-sm text-gray-500 mt-1">SaaS Smart Lock Dashboard & Management</p>
                </div>
                <div id="authSection">
                    <a href="/auth/google/login" class="flex items-center gap-2 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 font-medium py-2 px-4 rounded-xl shadow-sm transition">
                        <svg class="w-5 h-5" viewBox="0 0 24 24"><path fill="#4285F4" d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.66-5.17 3.66-9.17z"/><path fill="#34A853" d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.13 0-5.78-2.11-6.73-4.96H1.18v3.15C3.16 21.32 7.23 24 12 24z"/><path fill="#FBBC05" d="M5.27 14.24c-.25-.72-.38-1.49-.38-2.24s.13-1.52.38-2.24V6.6H1.18C.43 8.13 0 9.87 0 12s.43 3.87 1.18 5.4l4.09-3.16z"/><path fill="#EA4335" d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.23 0 3.16 2.68 1.18 6.6l4.09 3.15c.95-2.85 3.6-4.96 6.73-4.96z"/></svg>
                        تسجيل الدخول باستخدام Google
                    </a>
                </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                
                <!-- قسم فتح القفل عن بعد -->
                <div class="bg-white rounded-2xl shadow-sm p-6 space-y-4">
                    <h2 class="text-lg font-semibold text-gray-700">🔓 التحكم بالأجهزة</h2>
                    <div>
                        <label class="block text-xs text-gray-500 mb-1">معرف الجهاز (Device ID)</label>
                        <input type="text" id="deviceId" value="ESP32_01" class="w-full px-4 py-2 border rounded-xl focus:ring-2 focus:ring-blue-500 outline-none">
                    </div>
                    <button onclick="triggerUnlock()" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 rounded-xl transition shadow-md">
                        إرسال أمر فتح الباب
                    </button>
                </div>

                <!-- قسم إدارة المستخدمين (تفعيل / حظر) -->
                <div class="bg-white rounded-2xl shadow-sm p-6 space-y-4">
                    <h2 class="text-lg font-semibold text-gray-700">👥 إدارة حالة المستخدم</h2>
                    <div>
                        <label class="block text-xs text-gray-500 mb-1">رقم المستخدم (User ID)</label>
                        <input type="number" id="userId" placeholder="مثال: 1" class="w-full px-4 py-2 border rounded-xl focus:ring-2 focus:ring-blue-500 outline-none">
                    </div>
                    <div class="flex gap-2 pt-2">
                        <button onclick="updateUserStatus(true)" class="flex-1 bg-green-600 hover:bg-green-700 text-white py-2.5 rounded-xl transition">تفعيل</button>
                        <button onclick="updateUserStatus(false)" class="flex-1 bg-red-600 hover:bg-red-700 text-white py-2.5 rounded-xl transition">حظر</button>
                    </div>
                </div>

            </div>

            <!-- قسم إضافة بطاقة وعمليات البطاقات المؤقتة -->
            <div class="bg-white rounded-2xl shadow-sm p-6 space-y-4">
                <h2 class="text-lg font-semibold text-gray-700">💳 إضافة بطاقة / صلاحية مؤقتة</h2>
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <input type="number" id="cardUserId" placeholder="رقم المستخدم (User ID)" class="px-4 py-2 border rounded-xl">
                    <input type="text" id="cardIdVal" placeholder="رقم البطاقة (Card UID)" class="px-4 py-2 border rounded-xl">
                    <select id="isTemp" class="px-4 py-2 border rounded-xl" onchange="toggleTempOptions()">
                        <option value="false">بطاقة دائمة</option>
                        <option value="true">بطاقة مؤقتة / زائر</option>
                    </select>
                </div>
                <div id="tempOptions" class="hidden grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
                    <div>
                        <label class="block text-xs text-gray-500 mb-1">عدد ساعات الصلاحية</label>
                        <input type="number" id="expiryHours" value="24" class="w-full px-4 py-2 border rounded-xl">
                    </div>
                    <div>
                        <label class="block text-xs text-gray-500 mb-1">ساعة البدء (0-23)</label>
                        <input type="number" id="startHour" value="0" class="w-full px-4 py-2 border rounded-xl">
                    </div>
                    <div>
                        <label class="block text-xs text-gray-500 mb-1">ساعة الانتهاء (0-23)</label>
                        <input type="number" id="endHour" value="24" class="w-full px-4 py-2 border rounded-xl">
                    </div>
                </div>
                <button onclick="addNewCard()" class="w-full bg-purple-600 hover:bg-purple-700 text-white py-3 rounded-xl transition shadow-md">
                    حفظ وإضافة البطاقة للنظام
                </button>
            </div>

            <!-- جدول سجلات الحركات (Access Logs) -->
            <div class="bg-white rounded-2xl shadow-sm p-6 space-y-4">
                <div class="flex justify-between items-center">
                    <h2 class="text-lg font-semibold text-gray-700">📊 سجلات الحركة والدخول</h2>
                    <button onclick="loadLogs()" class="text-sm bg-gray-100 hover:bg-gray-200 text-gray-600 px-3 py-1.5 rounded-lg transition">تحديث السجلات</button>
                </div>
                <div class="overflow-x-auto">
                    <table class="w-full text-right border-collapse">
                        <thead>
                            <tr class="border-b text-sm text-gray-500">
                                <th class="p-3">المستخدم</th>
                                <th class="p-3">رقم البطاقة</th>
                                <th class="p-3">الحالة / النتيجة</th>
                                <th class="p-3">التوقيت</th>
                            </tr>
                        </thead>
                        <tbody id="logsTableBody" class="text-sm text-gray-700">
                            <tr><td colspan="4" class="p-4 text-center text-gray-400">جاري تحميل السجلات...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- صندوق الإشعارات والتنبيهات -->
            <div id="responseMessage" class="hidden p-4 rounded-xl text-sm text-center font-medium shadow-sm"></div>

        </div>

        <script>
            // التحقق من حالة تسجيل الدخول عبر بارامترات الرابط
            window.onload = function() {
                const urlParams = new URLSearchParams(window.location.search);
                if (urlParams.get('logged_in') === 'true') {
                    const name = urlParams.get('name');
                    document.getElementById('authSection').innerHTML = `
                        <div class="flex items-center gap-3 bg-green-50 text-green-700 px-4 py-2 rounded-xl border border-green-200">
                            <span class="font-medium">👋 أهلاً بك، ${name}</span>
                        </div>
                    `;
                }
                loadLogs();
            };

            function toggleTempOptions() {
                const isTemp = document.getElementById('isTemp').value === 'true';
                const tempDiv = document.getElementById('tempOptions');
                if (isTemp) {
                    tempDiv.classList.remove('hidden');
                } else {
                    tempDiv.classList.add('hidden');
                }
            }

            async function showMessage(text, isSuccess) {
                const box = document.getElementById('responseMessage');
                box.textContent = text;
                box.className = `p-4 rounded-xl text-sm text-center font-medium shadow-sm ${isSuccess ? 'bg-green-100 text-green-700 border border-green-200' : 'bg-red-100 text-red-700 border border-red-200'}`;
                box.classList.remove('hidden');
                setTimeout(() => box.classList.add('hidden'), 5000);
            }

            async function triggerUnlock() {
                const deviceId = document.getElementById('deviceId').value || 'ESP32_01';
                try {
                    const res = await fetch(`/api/device/${deviceId}/remote-unlock`, { method: 'POST' });
                    const data = await res.json();
                    if (res.ok) showMessage(data.message, true);
                    else showMessage("فشل فتح الباب", false);
                } catch (e) {
                    showMessage("خطأ في الاتصال بالخادم", false);
                }
            }

            async function updateUserStatus(isActive) {
                const userId = document.getElementById('userId').value;
                if (!userId) { showMessage("الرجاء إدخال رقم المستخدم", false); return; }
                try {
                    const res = await fetch(`/api/users/toggle-status?user_id=${userId}&is_active=${isActive}`, { method: 'POST' });
                    const data = await res.json();
                    if (res.ok) showMessage(data.message, true);
                    else showMessage("فشل تحديث حالة المستخدم", false);
                } catch (e) {
                    showMessage("خطأ في الاتصال بالخادم", false);
                }
            }

            async function addNewCard() {
                const userId = document.getElementById('cardUserId').value;
                const cardId = document.getElementById('cardIdVal').value;
                const isTemp = document.getElementById('isTemp').value;
                const expiryHours = document.getElementById('expiryHours').value;
                const startHour = document.getElementById('startHour').value;
                const endHour = document.getElementById('endHour').value;

                if (!userId || !cardId) {
                    showMessage("الرجاء إدخال رقم المستخدم ورقم البطاقة", false);
                    return;
                }

                try {
                    const url = `/api/cards/add?user_id=${userId}&card_id=${cardId}&is_temporary=${isTemp}&expiry_hours=${expiryHours}&start_hour=${startHour}&end_hour=${endHour}`;
                    const res = await fetch(url, { method: 'POST' });
                    const data = await res.json();
                    if (res.ok) {
                        showMessage(data.message, true);
                        loadLogs();
                    } else {
                        showMessage(data.detail || "فشل إضافة البطاقة", false);
                    }
                } catch (e) {
                    showMessage("خطأ في الاتصال بالخادم", false);
                }
            }

            async function loadLogs() {
                try {
                    const res = await fetch('/api/logs');
                    const data = await res.json();
                    const tbody = document.getElementById('logsTableBody');
                    if (data.logs && data.logs.length > 0) {
                        tbody.innerHTML = data.logs.map(log => `
                            <tr class="border-b hover:bg-gray-50">
                                <td class="p-3 font-medium">${log.user_name}</td>
                                <td class="p-3 text-gray-500">${log.card_id}</td>
                                <td class="p-3">
                                    <span class="px-2.5 py-1 rounded-full text-xs font-semibold ${log.status.includes('Granted') ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}">
                                        ${log.status}
                                    </span>
                                </td>
                                <td class="p-3 text-gray-400 text-xs">${log.timestamp}</td>
                            </tr>
                        `).join('');
                    } else {
                        tbody.innerHTML = `<tr><td colspan="4" class="p-4 text-center text-gray-400">لا توجد سجلات حركات حتى الآن</td></tr>`;
                    }
                } catch (e) {
                    console.error("Failed to load logs");
                }
            }
        </script>
    </body>
    </html>
    """


# ==============================================================================
# 8. نقطة تشغيل السيرفر
# ==============================================================================
if __name__ == "__main__":
  print(f"🚀 Starting Smart Lock SaaS Pro Server on port {CONFIG['PORT']}...")
  uvicorn.run(app, host="0.0.0.0", port=CONFIG["PORT"])
