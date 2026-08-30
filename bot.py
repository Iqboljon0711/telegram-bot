"""
SBD ERP.0 — Gemini AI asosidagi Telegram bot (Render.com uchun)
Matn, rasm, video, ovozli xabar va hujjatlarni tahlil qiladi.

===========================================================================
MUHIM: XAVFSIZLIK
===========================================================================
Bu faylda hech qanday token yoki API kalit YO'Q va bo'lmasligi kerak.
Barcha maxfiy qiymatlar Render Dashboard -> Environment bo'limida
o'rnatiladi (pastdagi "RENDER'DA SOZLASH" bo'limiga qarang).

Agar tokeningiz avval kodga yozilgan yoki chatga yuborilgan bo'lsa —
uni albatta bekor qiling (revoke) va yangisini oling:
    - Telegram: @BotFather -> /mybots -> botingiz -> API Token -> Revoke
    - Gemini:   Google Cloud Console -> API Keys -> shu kalitni o'chiring

===========================================================================
O'RNATISH (talab qilinadigan kutubxonalar)
===========================================================================
requirements.txt fayliga quyidagilarni yozing:

    pyTelegramBotAPI
    google-genai

===========================================================================
RENDER'DA SOZLASH
===========================================================================
1. Render Dashboard -> loyihangiz -> Web Service -> Environment
2. "Add Environment Variable" orqali qo'shing:
       TELEGRAM_TOKEN   = sizning yangi Telegram bot tokeningiz
       GEMINI_API_KEY   = sizning yangi Gemini API kalitingiz
3. "Save Changes" -> Render avtomatik qayta deploy qiladi.
4. Build Command:   pip install -r requirements.txt
   Start Command:   python bot.py

Render "Web Service" turi doimiy ochiq port kutadi, shuning uchun bu fayl
ichida engil HTTP server ham ishga tushiriladi (health-check uchun) —
buni pastda ko'rasiz, alohida sozlash shart emas.
"""

import os
import logging
import threading
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer

import telebot
from google import genai
from google.genai import types

# ---------------------------------------------------------------------
# LOGGING
# ---------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("sbd_erp_bot")

# ---------------------------------------------------------------------
# MUHIT O'ZGARUVCHILARI
# ---------------------------------------------------------------------

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
PORT = int(os.environ.get("PORT", "10000"))  # Render avtomatik beradi

missing = [
    name
    for name, value in [
        ("TELEGRAM_TOKEN", TELEGRAM_TOKEN),
        ("GEMINI_API_KEY", GEMINI_API_KEY),
    ]
    if not value
]
if missing:
    raise RuntimeError(
        f"Quyidagi muhit o'zgaruvchilari topilmadi: {', '.join(missing)}.\n"
        "Render Dashboard -> Environment bo'limida ularni qo'shing."
    )

MODEL_NAME = "gemini-3.6-flash"

SYSTEM_PROMPT = (
    "Sen SBD ERP.0 platformasining rasmiy aqlli yordamchisisan. "
    "SBD ERP.0 — korxona jarayonlarini avtomatlashtirish va boshqarish platformasi "
    "(https://isbd.uz/sbd-erp). "
    "Foydalanuvchilarga tizim va uning bo'limlari (savdo, ombor, moliya, HR) haqidagi "
    "savollariga har safar o'ziga xos, chiroyli va mukammal javoblar berasan. "
    "Agar foydalanuvchi rasm, video yoki ovozli xabar yuborsa, uni diqqat bilan tahlil qilib, "
    "SBD ERP kontekstida (masalan: hisobot skrinshoti, mahsulot rasmi, ombordagi jarayon video, "
    "ovozli savol) foydali va aniq izoh berasan. "
    "Agar narx, bog'lanish yoki qo'shimcha ma'lumot so'rasa, har doim veb-saytimizni "
    "(https://isbd.uz/sbd-erp) va telefon raqamimizni (+998903610711) eslatib o'tasan. "
    "Doimo o'zbek tilida xushmuomala va aniq javob ber."
)

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = genai.Client(api_key=GEMINI_API_KEY)

# Har bir foydalanuvchi uchun suhbat tarixi (xotirada saqlanadi, cheklangan uzunlikda)
chat_histories: dict[int, list] = {}
MAX_HISTORY_MESSAGES = 20


def get_history(chat_id: int) -> list:
    return chat_histories.setdefault(chat_id, [])


def push_history(chat_id: int, role: str, parts: list):
    history = get_history(chat_id)
    history.append({"role": role, "parts": parts})
    if len(history) > MAX_HISTORY_MESSAGES:
        del history[: len(history) - MAX_HISTORY_MESSAGES]


def ask_gemini(chat_id: int, parts: list) -> str:
    """Gemini'ga so'rov yuboradi va javobni matn ko'rinishida qaytaradi."""
    push_history(chat_id, "user", parts)
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=get_history(chat_id),
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
            ),
        )
        reply_text = response.text or "Kechirasiz, javob shakllantirib bo'lmadi."
    except Exception:
        logger.error("Gemini so'rovida xato:\n%s", traceback.format_exc())
        reply_text = "Kechirasiz, hozircha javob bera olmadim. Birozdan so'ng qayta urinib ko'ring."
        # Xato bo'lganda suhbat tarixini shikastlamaslik uchun oxirgi user xabarini olib tashlaymiz
        get_history(chat_id).pop()
        return reply_text

    push_history(chat_id, "model", [{"text": reply_text}])
    return reply_text


def download_telegram_file(file_id: str) -> bytes:
    file_info = bot.get_file(file_id)
    return bot.download_file(file_info.file_path)


# ---------------------------------------------------------------------
# BUYRUQLAR
# ---------------------------------------------------------------------

@bot.message_handler(commands=["start"])
def send_welcome(message):
    chat_histories.pop(message.chat.id, None)
    welcome_text = (
        "Assalomu alaykum! Men SBD ERP.0 sun'iy intellekt yordamchisiman 🤖\n\n"
        "Menga quyidagilarni yuborishingiz mumkin:\n"
        "📝 Matnli savol\n"
        "🖼 Rasm (masalan, hisobot skrinshoti)\n"
        "🎥 Video\n"
        "🎤 Ovozli xabar\n"
        "📄 Hujjat\n\n"
        "🌐 Veb-sayt: https://isbd.uz/sbd-erp\n"
        "📞 Telefon: +998903610711"
    )
    bot.reply_to(message, welcome_text)


@bot.message_handler(commands=["reset"])
def reset_history(message):
    chat_histories.pop(message.chat.id, None)
    bot.reply_to(message, "Suhbat tarixi tozalandi. ✅")


# ---------------------------------------------------------------------
# MATN
# ---------------------------------------------------------------------

@bot.message_handler(content_types=["text"])
def handle_text(message):
    bot.send_chat_action(message.chat.id, "typing")
    reply_text = ask_gemini(message.chat.id, [{"text": message.text}])
    bot.reply_to(message, reply_text)


# ---------------------------------------------------------------------
# RASM
# ---------------------------------------------------------------------

@bot.message_handler(content_types=["photo"])
def handle_photo(message):
    bot.send_chat_action(message.chat.id, "typing")
    try:
        file_id = message.photo[-1].file_id
        image_bytes = download_telegram_file(file_id)
        caption = message.caption or "Ushbu rasmni SBD ERP kontekstida tahlil qilib bering."
        parts = [
            {"text": caption},
            {"inline_data": {"mime_type": "image/jpeg", "data": image_bytes}},
        ]
        reply_text = ask_gemini(message.chat.id, parts)
    except Exception:
        logger.error("Rasmni yuklab olishda xato:\n%s", traceback.format_exc())
        reply_text = "Kechirasiz, rasmni tahlil qilishda xatolik yuz berdi."
    bot.reply_to(message, reply_text)


# ---------------------------------------------------------------------
# VIDEO
# ---------------------------------------------------------------------

@bot.message_handler(content_types=["video"])
def handle_video(message):
    bot.send_chat_action(message.chat.id, "typing")
    try:
        file_id = message.video.file_id
        video_bytes = download_telegram_file(file_id)
        caption = message.caption or "Ushbu videoni SBD ERP kontekstida tahlil qilib bering."
        parts = [
            {"text": caption},
            {"inline_data": {"mime_type": "video/mp4", "data": video_bytes}},
        ]
        reply_text = ask_gemini(message.chat.id, parts)
    except Exception:
        logger.error("Videoni yuklab olishda xato:\n%s", traceback.format_exc())
        reply_text = "Kechirasiz, videoni tahlil qilishda xatolik yuz berdi."
    bot.reply_to(message, reply_text)


# ---------------------------------------------------------------------
# OVOZLI XABAR VA AUDIO
# ---------------------------------------------------------------------

@bot.message_handler(content_types=["voice"])
def handle_voice(message):
    bot.send_chat_action(message.chat.id, "typing")
    try:
        file_id = message.voice.file_id
        audio_bytes = download_telegram_file(file_id)
        parts = [
            {"text": "Ushbu ovozli xabarni tinglab, mazmunini SBD ERP kontekstida tushunib javob bering."},
            {"inline_data": {"mime_type": "audio/ogg", "data": audio_bytes}},
        ]
        reply_text = ask_gemini(message.chat.id, parts)
    except Exception:
        logger.error("Ovozli xabarni yuklab olishda xato:\n%s", traceback.format_exc())
        reply_text = "Kechirasiz, ovozli xabarni tahlil qilishda xatolik yuz berdi."
    bot.reply_to(message, reply_text)


@bot.message_handler(content_types=["audio"])
def handle_audio(message):
    bot.send_chat_action(message.chat.id, "typing")
    try:
        file_id = message.audio.file_id
        audio_bytes = download_telegram_file(file_id)
        parts = [
            {"text": message.caption or "Ushbu audio faylni tahlil qilib bering."},
            {"inline_data": {"mime_type": "audio/mpeg", "data": audio_bytes}},
        ]
        reply_text = ask_gemini(message.chat.id, parts)
    except Exception:
        logger.error("Audio faylni yuklab olishda xato:\n%s", traceback.format_exc())
        reply_text = "Kechirasiz, audio faylni tahlil qilishda xatolik yuz berdi."
    bot.reply_to(message, reply_text)


# ---------------------------------------------------------------------
# HUJJATLAR
# ---------------------------------------------------------------------

@bot.message_handler(content_types=["document"])
def handle_document(message):
    bot.send_chat_action(message.chat.id, "typing")
    try:
        doc = message.document
        mime_type = doc.mime_type or "application/octet-stream"
        file_bytes = download_telegram_file(doc.file_id)
        parts = [
            {"text": message.caption or f"Ushbu faylni ({doc.file_name}) tahlil qilib bering."},
            {"inline_data": {"mime_type": mime_type, "data": file_bytes}},
        ]
        reply_text = ask_gemini(message.chat.id, parts)
    except Exception:
        logger.error("Hujjatni yuklab olishda xato:\n%s", traceback.format_exc())
        reply_text = "Kechirasiz, faylni tahlil qilishda xatolik yuz berdi."
    bot.reply_to(message, reply_text)


# ---------------------------------------------------------------------
# RENDER UCHUN ENGIL HTTP SERVER (health-check)
# Render "Web Service" turi doimiy ochiq portni talab qiladi.
# ---------------------------------------------------------------------

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write("SBD ERP.0 AI Bot ishlab turibdi ✅".encode("utf-8"))

    def log_message(self, format, *args):
        pass  # Health-check so'rovlarini logga chiqarmaymiz


def run_health_server():
    server = HTTPServer(("0.0.0.0", PORT), HealthCheckHandler)
    logger.info("Health-check server %s portda ishga tushdi", PORT)
    server.serve_forever()


# ---------------------------------------------------------------------
# ISHGA TUSHIRISH
# ---------------------------------------------------------------------

if __name__ == "__main__":
    threading.Thread(target=run_health_server, daemon=True).start()
    logger.info("SBD ERP.0 AI Bot muvaffaqiyatli ishga tushdi...")
    bot.infinity_polling(skip_pending=True)
