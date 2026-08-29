import os
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


def ask_gemini(prompt_text):
  try:
    # To'g'ridan-to'g'ri Gemini API'ga so'rov yuborish (token turidan qat'iy nazar ishlaydi)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{
            "parts": [{"text": f"{SYSTEM_PROMPT}\n\nSavol: {prompt_text}"}]
        }]
    }
    response = requests.post(url, headers=headers, json=data, timeout=30)
    res_json = response.json()
    return res_json["candidates"][0]["content"]["parts"][0]["text"]
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
  print("Bot HTTP so'rovlar rejimi bilan ishga tushdi...")
  while True:
    try:
      bot.infinity_polling(skip_pending=True, timeout=60, long_polling_timeout=60)
    except Exception as e:
      print(f"Polling xatoligi: {e}")
      time.sleep(5)
