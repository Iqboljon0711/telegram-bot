import os
import time
from google import genai
import telebot

# Token va kalitlarni Railway Variables muhitidan o'qib olamiz
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
  raise ValueError(
      "TELEGRAM_TOKEN yoki GEMINI_API_KEY topilmadi! Railway Variables"
      " bo'limini tekshiring."
  )

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = genai.Client(api_key=GEMINI_API_KEY)

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
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"{SYSTEM_PROMPT}\n\nFoydalanuvchi savoli: {message.text}",
    )
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

    audio_file = client.files.upload(file=voice_path)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            audio_file,
            (
                f"{SYSTEM_PROMPT}\n\nUshbu ovozli xabarni tingla va"
                " foydalanuvchining savoliga o'zbek tilida qisqa javob ber."
            ),
        ],
    )
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

    image_file = client.files.upload(file=photo_path)
    caption_text = (
        message.caption if message.caption else "Rasmni tahlil qil"
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            image_file,
            (
                f"{SYSTEM_PROMPT}\n\nFoydalanuvchi rasmni yubordi. Izoh:"
                f" {caption_text}. Tahlil qilib javob yoz."
            ),
        ],
    )
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

    video_file = client.files.upload(file=video_path)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            video_file,
            (
                f"{SYSTEM_PROMPT}\n\nFoydalanuvchi videoni yubordi. Holatni"
                " tahlil qilib javob ber."
            ),
        ],
    )
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
  print("Bot toza token bilan muvaffaqiyatli ishga tushdi...")
  while True:
    try:
      bot.infinity_polling(skip_pending=True, timeout=60, long_polling_timeout=60)
    except Exception as e:
      print(f"Xatolik yuz berdi: {e}")
      time.sleep(5)
