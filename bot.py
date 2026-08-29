import os
import time
import google.generativeai as genai
import telebot

TELEGRAM_TOKEN = "8657456868:AAHeypCVp-qfofC8x_cBjWI4asApHiJuN4M".strip()
GEMINI_API_KEY = (
    "AQ.Ab8RN6LnLgjddJdCceWzCo9ihSDlB91QcQk4UdWt0YVDXGbJ5w".strip()
)

bot = telebot.TeleBot(TELEGRAM_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel("gemini-1.5-flash")

SYSTEM_PROMPT = """
Sen SBD ERP.0 (https://isbd.uz/sbd-erp) korxona resurslarini rejalashtirish dasturining aqlli yordamchi assistentisan.
Sening vazifang foydalanuvchilarning savollariga o'zbek tilida qisqa, aniq va tushunarli javob berish.
"""


@bot.message_handler(commands=["start"])
def send_welcome(message):
  bot.reply_to(
      message,
      "Assalomu alaykum! SBD ERP.0 yordamchi botiga xush kelibsiz. Menga istalgan"
      " savolni yuboring, javob beraman! 🤖",
  )


@bot.message_handler(content_types=["text"])
def handle_text(message):
  try:
    prompt = f"{SYSTEM_PROMPT}\n\nFoydalanuvchi savoli: {message.text}"
    response = model.generate_content(prompt)
    bot.reply_to(
        message, f"📝 *Javob:* \n{response.text}", parse_mode="Markdown"
    )
  except Exception as e:
    print(f"Xatolik: {e}")
    bot.reply_to(message, "Kechirasiz, xatolik yuz berdi. 🤖")


@bot.message_handler(content_types=["voice"])
def handle_voice(message):
  voice_path = "voice_msg.ogg"
  try:
    file_info = bot.get_file(message.voice.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    with open(voice_path, "wb") as f:
      f.write(downloaded_file)

    audio_file = genai.upload_file(voice_path)
    prompt = [
        audio_file,
        (
            f"{SYSTEM_PROMPT}\n\nUshbu ovozli xabarni tingla va"
            " foydalanuvchining savoliga o'zbek tilida qisqa javob ber."
        ),
    ]
    response = model.generate_content(prompt)
    bot.reply_to(
        message, f"📝 *Javob:* \n{response.text}", parse_mode="Markdown"
    )
  except Exception as e:
    print(f"Ovozli xatolik: {e}")
    bot.reply_to(
        message, "Kechirasiz, ovozli xabarni o'qishda xatolik yuz berdi. 🤖"
    )
  finally:
    if os.path.exists(voice_path):
      os.remove(voice_path)


@bot.message_handler(content_types=["photo"])
def handle_photo(message):
  photo_path = "photo_msg.jpg"
  try:
    file_info = bot.get_file(message.photo[-1].file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    with open(photo_path, "wb") as f:
      f.write(downloaded_file)

    image_file = genai.upload_file(photo_path)
    caption_text = (
        message.caption if message.caption else "Rasmni tahlil qil"
    )
    prompt = [
        image_file,
        (
            f"{SYSTEM_PROMPT}\n\nFoydalanuvchi rasmni yubordi. Izoh:"
            f" {caption_text}. Tahlil qilib javob yoz."
        ),
    ]
    response = model.generate_content(prompt)
    bot.reply_to(
        message, f"📝 *Javob:* \n{response.text}", parse_mode="Markdown"
    )
  except Exception as e:
    print(f"Rasm xatoligi: {e}")
    bot.reply_to(
        message, "Kechirasiz, rasmni tahlil qilishda xatolik yuz berdi. 🤖"
    )
  finally:
    if os.path.exists(photo_path):
      os.remove(photo_path)


@bot.message_handler(content_types=["video_note", "video"])
def handle_video(message):
  video_path = "video_msg.mp4"
  try:
    file_id = (
        message.video_note.file_id
        if message.content_type == "video_note"
        else message.video.file_id
    )
    file_info = bot.get_file(file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    with open(video_path, "wb") as f:
      f.write(downloaded_file)

    video_file = genai.upload_file(video_path)
    prompt = [
        video_file,
        (
            f"{SYSTEM_PROMPT}\n\nFoydalanuvchi videoni yubordi. Holatni"
            " tahlil qilib javob ber."
        ),
    ]
    response = model.generate_content(prompt)
    bot.reply_to(
        message, f"📝 *Javob:* \n{response.text}", parse_mode="Markdown"
    )
  except Exception as e:
    print(f"Video xatoligi: {e}")
    bot.reply_to(
        message, "Kechirasiz, videoni tahlil qilishda xatolik yuz berdi. 🤖"
    )
  finally:
    if os.path.exists(video_path):
      os.remove(video_path)


if __name__ == "__main__":
  print("Bot eski formatdagi barqaror rejimda ishga tushdi...")
  while True:
    try:
      bot.infinity_polling(skip_pending=True, timeout=60, long_polling_timeout=60)
    except Exception as e:
      print(f"Xatolik yuz berdi: {e}")
      time.sleep(5)
