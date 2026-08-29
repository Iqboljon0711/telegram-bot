import os
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import time
import requests
import telebot

TELEGRAM_TOKEN = "8657456868:AAEAgeXPol6p0zJCsBc9JbKsxlXN1j3DKEk".strip()
GEMINI_API_KEY = (
    "AQ.Ab8RN6LdoSMwqsolpf4JgQjSnnqhHpgvNSLpdTg_nTglAY_u8g".strip()
)

bot = telebot.TeleBot(TELEGRAM_TOKEN)

SYSTEM_PROMPT = """
Sen SBD ERP.0 (https://isbd.uz/sbd-erp) korxona resurslarini rejalashtirish dasturining aqlli yordamchi assistentisan.
Sening vazifang foydalanuvchilarning savollariga o'zbek tilida qisqa, aniq va tushunarli javob berish.
"""


# Render Web Service talabini qondirish uchun kichik veb-server
class SimpleHandler(BaseHTTPRequestHandler):

  def do_GET(self):
    self.send_response(200)
    self.end_headers()
    self.wfile.write(b"Bot is alive!")


def run_server():
  port = int(os.environ.get("PORT", 10000))
  server = HTTPServer(("0.0.0.0", port), SimpleHandler)
  server.serve_forever()


# Veb-serverni alohida oqimda (thread) fonda ishga tushiramiz
threading.Thread(target=run_server, daemon=True).start()


def ask_gemini(prompt_text):
  try:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{
            "parts": [{"text": f"{SYSTEM_PROMPT}\n\nSavol: {prompt_text}"}]
        }]
    }
    response = requests.post(url, headers=headers, json=data, timeout=30)
    res_json = response.json()

    if "candidates" in res_json and len(res_json["candidates"]) > 0:
      candidate = res_json["candidates"][0]
      if (
          "content" in candidate
          and "parts" in candidate["content"]
          and len(candidate["content"]["parts"]) > 0
      ):
        return candidate["content"]["parts"][0]["text"]
    return f"Javobni o'qishda xatolik: {res_json}"
  except Exception as e:
    return f"Xatolik yuz berdi: {str(e)}"


@bot.message_handler(commands=["start"])
def send_welcome(message):
  bot.reply_to(
      message,
      "Assalomu alaykum! SBD ERP.0 yordamchi botiga xush kelibsiz. Menga istalgan"
      " savolni yuboring, javob beraman! 🤖",
  )


@bot.message_handler(content_types=["text"])
def handle_text(message):
  answer = ask_gemini(message.text)
  bot.reply_to(message, f"📝 *Javob:* \n{answer}", parse_mode="Markdown")


if __name__ == "__main__":
  print("Bot veb-server va Telegram polling bilan birga ishga tushdi...")
  while True:
    try:
      bot.infinity_polling(skip_pending=True, timeout=60, long_polling_timeout=60)
    except Exception as e:
      print(f"Polling xatoligi: {e}")
      time.sleep(5)
