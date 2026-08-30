import os
import logging
import threading
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer

import telebot
from google import genai
from google.genai import types

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("sbd_erp_bot")

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
PORT = int(os.environ.get("PORT", "10000"))

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
        f"Quyidagi muhit o'zgaruvchilari topilmadi: {', '.join(missing)}. "
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
    "SBD ERP kontekstida foydali va aniq izoh berasan. "
    "Agar narx, bog'lanish yoki qo'shimcha ma'lumot so'rasa, har doim veb-saytimizni "
    "(https://isbd.uz/sbd-erp) va telefon raqamimizni (+998903610711) eslatib o'tasan. "
    "Doimo o'zbek tilida xushmuomala va aniq javob ber."
)

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = genai.Client(api_key=GEMINI_API_KEY)

chat_histories = {}
MAX_HISTORY_MESSAGES = 20


def get_history(chat_id):
    return chat_histories.setdefault(chat_id, [])


def push_history(chat_id, role, parts):
    history = get_history(chat_id)
    history.append({"role": role, "parts": parts})
    if len(history) > MAX_HISTORY_MESSAGES:
        del history[: len(history) - MAX_HISTORY_MESSAGES]


def ask_gemini(chat_id, parts):
    push_history(chat_id, "user", parts)
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=get_history(chat_id),
            config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
        )
        reply_text = response.text or "Kechirasiz, javob shakllantirib bo'lmadi."
    except Exception:
        logger.error("Gemini so'rovida xato:\n%s", traceback.format_exc())
        get_history(chat_id).pop()
        return "Kechirasiz, hozircha javob bera olmadim. Birozdan so'ng qayta urinib ko'ring."

    push_history(chat_id, "model", [{"text": reply_text}])
    return reply_text


def download_telegram_file(file_id):
    file_info = bot.get_file(file_id)
    return bot.download_file(file_info.file_path)


@bot.message_handler(commands=["start"])
def send_welcome(message):
    chat_histories.pop(message.chat.id, None)
    welcome_text = (
        "Assalomu alaykum! Men SBD ERP.0 sun'iy intellekt yordamchisiman 🤖\n\n"
        "Menga quyidagilarni yuborishingiz mumkin:\n"
        "📝 Matnli savol\n"
        "🖼 Rasm\n"
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


@bot.message_handler(content_types=["text"])
def handle_text(message):
    bot.send_chat_action(message.chat.id, "typing")
    reply_text = ask_gemini(message.chat.id, [{"text": message.text}])
    bot.reply_to(message, reply_text)


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


class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write("SBD ERP.0 AI Bot ishlab turibdi ✅".encode("utf-8"))

    def log_message(self, format, *args):
        pass


def run_health_server():
    server = HTTPServer(("0.0.0.0", PORT), HealthCheckHandler)
    logger.info("Health-check server %s portda ishga tushdi", PORT)
    server.serve_forever()


if __name__ == "__main__":
    threading.Thread(target=run_health_server, daemon=True).start()
    logger.info("SBD ERP.0 AI Bot muvaffaqiyatli ishga tushdi...")
    bot.infinity_polling(skip_pending=True)
