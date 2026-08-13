const I18N = {
  ar: {
    dir: "rtl",
    brand_name: "بوابة",
    brand_sub: "نظام التحكم بالدخول",
    email: "البريد الإلكتروني",
    password: "كلمة المرور",
    login_btn: "تسجيل الدخول",
    or: "أو",
    forgot_password: "نسيت كلمة المرور؟",
    back_to_login: "الرجوع لتسجيل الدخول",
    set_password_title: "حدد كلمة مرور جديدة",
    set_password_desc: "هاي أول مرة تسجل دخول. حدد كلمة مرور تستخدمها بالمرات الجاية.",
    confirm: "تأكيد",
    forgot_title: "استعادة كلمة المرور",
    forgot_desc: "بنبعتلك رمز تحقق عبر الإيميل",
    send_code: "إرسال الرمز",
    reset_title: "إدخال الرمز وكلمة المرور الجديدة",
    code: "رمز التحقق",
    new_password: "كلمة المرور الجديدة",
    save: "حفظ",

    nav_overview: "لوحة التحكم",
    nav_cards: "البطاقات",
    nav_emergency: "الطوارئ",
    nav_logs: "السجل",
    nav_notifications: "الإشعارات",
    nav_settings: "الإعدادات",
    logout: "تسجيل الخروج",

    door_status_online: "الجهاز متصل",
    door_status_offline: "الجهاز غير متصل",
    open_door: "فتح الباب",
    opening: "جارِ الفتح...",
    door_opened: "تم إرسال أمر الفتح ✔",

    stat_total_cards: "إجمالي البطاقات",
    stat_allowed: "مسموح لهم",
    stat_today_events: "حركات اليوم",
    stat_unread_notif: "إشعارات غير مقروءة",

    add_card: "+ إضافة بطاقة",
    table_uid: "رقم البطاقة",
    table_name: "الاسم",
    table_status: "الحالة",
    table_type: "النوع",
    table_emergency: "طوارئ",
    table_actions: "إجراءات",
    edit: "تعديل",
    delete: "حذف",
    allowed: "مسموح",
    denied: "ممنوع",
    permanent: "دائمة",
    temporary: "مؤقتة",
    yes: "نعم",
    no: "لا",

    modal_add_card_title: "إضافة بطاقة جديدة",
    modal_edit_card_title: "تعديل البطاقة",
    field_uid: "رقم البطاقة (UID)",
    field_name: "اسم الشخص",
    field_status: "الحالة",
    field_type: "نوع البطاقة",
    field_valid_from: "صالحة من",
    field_valid_to: "صالحة إلى",
    field_emergency: "بطاقة طوارئ (تشتغل بدون إنترنت)",
    cancel: "إلغاء",
    save_card: "حفظ البطاقة",
    confirm_delete: "متأكد إنك بدك تحذف هاي البطاقة؟",

    emergency_desc: "البطاقات هون بتشتغل حتى لو انقطع النت عن الجهاز، لأنها محفوظة محلياً على ESP32.",

    table_time: "الوقت",
    table_event: "الحدث",
    table_reason: "السبب",
    entry: "دخول",
    exit: "خروج",
    granted: "مسموح",
    offline_badge: "أوفلاين",

    mark_all_read: "تحديد الكل كمقروء",
    no_notifications: "لا يوجد إشعارات حالياً",

    settings_notif_title: "إعدادات الإشعارات",
    notify_email_enabled: "إرسال إشعارات عبر الإيميل",
    notify_on_denied: "محاولة دخول غير مصرح بها",
    notify_on_door_open: "فتح الباب عن بعد",
    notify_on_emergency: "استخدام بطاقة طوارئ أثناء انقطاع النت",
    settings_lang_title: "اللغة",

    err_generic: "صار في خطأ، حاول مرة تانية",
    err_login: "البريد أو كلمة المرور غلط",
  },
  en: {
    dir: "ltr",
    brand_name: "Gateway",
    brand_sub: "Access Control System",
    email: "Email",
    password: "Password",
    login_btn: "Sign In",
    or: "or",
    forgot_password: "Forgot password?",
    back_to_login: "Back to sign in",
    set_password_title: "Set a new password",
    set_password_desc: "This is your first sign-in. Set a password to use next time.",
    confirm: "Confirm",
    forgot_title: "Reset password",
    forgot_desc: "We'll email you a verification code",
    send_code: "Send code",
    reset_title: "Enter the code and new password",
    code: "Verification code",
    new_password: "New password",
    save: "Save",

    nav_overview: "Overview",
    nav_cards: "Cards",
    nav_emergency: "Emergency",
    nav_logs: "Logs",
    nav_notifications: "Notifications",
    nav_settings: "Settings",
    logout: "Log out",

    door_status_online: "Device online",
    door_status_offline: "Device offline",
    open_door: "Open Door",
    opening: "Opening...",
    door_opened: "Open command sent ✔",

    stat_total_cards: "Total Cards",
    stat_allowed: "Allowed",
    stat_today_events: "Today's Events",
    stat_unread_notif: "Unread Notifications",

    add_card: "+ Add Card",
    table_uid: "Card UID",
    table_name: "Name",
    table_status: "Status",
    table_type: "Type",
    table_emergency: "Emergency",
    table_actions: "Actions",
    edit: "Edit",
    delete: "Delete",
    allowed: "Allowed",
    denied: "Denied",
    permanent: "Permanent",
    temporary: "Temporary",
    yes: "Yes",
    no: "No",

    modal_add_card_title: "Add New Card",
    modal_edit_card_title: "Edit Card",
    field_uid: "Card UID",
    field_name: "Person Name",
    field_status: "Status",
    field_type: "Card Type",
    field_valid_from: "Valid From",
    field_valid_to: "Valid To",
    field_emergency: "Emergency card (works offline)",
    cancel: "Cancel",
    save_card: "Save Card",
    confirm_delete: "Are you sure you want to delete this card?",

    emergency_desc: "These cards keep working even if the device loses internet, since they're cached locally on the ESP32.",

    table_time: "Time",
    table_event: "Event",
    table_reason: "Reason",
    entry: "Entry",
    exit: "Exit",
    granted: "Granted",
    offline_badge: "Offline",

    mark_all_read: "Mark all as read",
    no_notifications: "No notifications yet",

    settings_notif_title: "Notification Settings",
    notify_email_enabled: "Send notifications by email",
    notify_on_denied: "Unauthorized access attempt",
    notify_on_door_open: "Remote door open",
    notify_on_emergency: "Emergency card used offline",
    settings_lang_title: "Language",

    err_generic: "Something went wrong, please try again",
    err_login: "Invalid email or password",
  }
};

let currentLang = localStorage.getItem("lang") || "ar";

function t(key) {
  return I18N[currentLang][key] || key;
}

function applyI18n() {
  document.documentElement.setAttribute("lang", currentLang);
  document.documentElement.setAttribute("dir", I18N[currentLang].dir);
  document.querySelectorAll("[data-i18n]").forEach(el => {
    el.textContent = t(el.getAttribute("data-i18n"));
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
    el.placeholder = t(el.getAttribute("data-i18n-placeholder"));
  });
}

function setLang(lang) {
  currentLang = lang;
  localStorage.setItem("lang", lang);
  applyI18n();
  if (window.onLangChange) window.onLangChange();
}
