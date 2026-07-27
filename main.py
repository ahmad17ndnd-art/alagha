import os
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# ==============================================================================
# 1. إعداد المتغيرات البيئية والمفاتيح الخاصة بمشروعك (Config & Credentials)
# ==============================================================================
CONFIG = {
    "PORT": 3000,
    "SECRET_KEY": "super_secret_saas_key_2026_python",
    
    # Google OAuth Keys
    "GOOGLE_CLIENT_ID": "034269901652-sftbqggk6morgtebdmchkubbt4ohuuci.apps.googleusercontent.com",
    "GOOGLE_CLIENT_SECRET": "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",
    "GOOGLE_REDIRECT_URI": "http://localhost:3000/auth/google/callback",
    
    # Super Admin Details
    "SUPER_ADMIN_EMAIL": "ahmad17ndnd@gmail.com",
    "SUPER_ADMIN_PHONE": "0956718984",
    
    # Telegram Integration (تم تحديث التوكن)
    "TELEGRAM_BOT_TOKEN": "8915690581:AAH15aBE6EvmjQQcRN1Pdyjrh7uQIJijkmo"
}

# ==============================================================================
# 2. تهيئة تطبيق FastAPI وإعدادات CORS
# ==============================================================================
app = FastAPI(
    title="Smart Lock SaaS Platform",
    description="Full Backend Application for Smart Lock Management",
    version="1.0.0"
)

# السماح بالاتصالات الخارجية من أي نطاق (CORS)
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
        "system": "Smart Lock SaaS Platform",
        "engine": "Python FastAPI",
        "endpoints": {
            "google_login": "/auth/google/login",
            "esp32_check_card": "/api/user/{user_id}/check-card?card_id=A1B2C3D4",
            "telegram_webhook": "/telegram/webhook"
        }
    }

# ==============================================================================
# 4. مسارات المصادقة وتسجيل الدخول عبر جوجل (Google OAuth Routes)
# ==============================================================================
@app.get("/auth/google/login")
async def google_login():
    """توجيه المستخدم لتسجيل الدخول بـ Google"""
    google_auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={CONFIG['GOOGLE_CLIENT_ID']}&"
        f"redirect_uri={CONFIG['GOOGLE_REDIRECT_URI']}&"
        "response_type=code&"
        "scope=openid%20email%20profile"
    )
    return RedirectResponse(url=google_auth_url)


@app.get("/auth/google/callback")
async def google_callback(code: str):
    """استقبال الكود وتبادله للحصول على بيانات حساب المستخدم"""
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": CONFIG["GOOGLE_CLIENT_ID"],
        "client_secret": CONFIG["GOOGLE_CLIENT_SECRET"],
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": CONFIG["GOOGLE_REDIRECT_URI"],
    }

    async with httpx.AsyncClient() as client:
        # تبادل الكود والحصول على Access Token
        token_response = await client.post(token_url, data=data)
        token_json = token_response.json()

        if "error" in token_json:
            raise HTTPException(status_code=400, detail=token_json.get("error_description"))

        access_token = token_json.get("access_token")

        # طلب بيانات ملف المستخدم الشخصي
        user_info_response = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        user_data = user_info_response.json()

    # التحقق هل المستخدم هو الـ Super Admin
    is_admin = user_data.get("email") == CONFIG["SUPER_ADMIN_EMAIL"]

    return {
        "status": "success",
        "message": "تم تسجيل الدخول بنجاح",
        "is_super_admin": is_admin,
        "user_details": {
            "name": user_data.get("name"),
            "email": user_data.get("email"),
            "profile_pic": user_data.get("picture")
        }
    }

# ==============================================================================
# 5. مسار فحص أجهزة ESP32 (Hardware API Endpoint)
# ==============================================================================
@app.get("/api/user/{user_id}/check-card")
async def check_card(user_id: str, card_id: str):
    """
    استقبال طلب القفل من ESP32
    مثال الاستدعاء: /api/user/101/check-card?card_id=A1B2C3D4
    """
    # كروت مسموح بها تجريبياً
    ALLOWED_CARDS = ["A1B2C3D4", "99887766", "12345678"]

    if card_id in ALLOWED_CARDS:
        return JSONResponse(
            status_code=200,
            content={
                "access": True,
                "message": "Access Granted",
                "user_id": user_id,
                "card_id": card_id
            }
        )
    
    return JSONResponse(
        status_code=403,
        content={
            "access": False,
            "message": "Access Denied",
            "user_id": user_id,
            "card_id": card_id
        }
    )

# ==============================================================================
# 6. مسار استقبال تحديثات بوت التليجرام (Telegram Bot Webhook)
# ==============================================================================
@app.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    """استقبال التنبيهات والأوامر من بوت Telegram"""
    data = await request.json()
    
    # معالجة الرسائل الواردة من التليجرام
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        # رد تلقائي للأمر /start
        if text == "/start":
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"https://api.telegram.org/bot{CONFIG['TELEGRAM_BOT_TOKEN']}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": "مرحباً بك في نظام Smart Lock! يمكنك التحكم في أقفالك المربوطة من هنا."
                    }
                )

    return {"status": "ok"}

# ==============================================================================
# 7. نقطة تشغيل السيرفر (Execution Point)
# ==============================================================================
if __name__ == "__main__":
    print(f"🚀 Starting Smart Lock SaaS Server on port {CONFIG['PORT']}...")
    uvicorn.run(app, host="0.0.0.0", port=CONFIG["PORT"])
