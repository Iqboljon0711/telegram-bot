from google import genai
import telebot
import os
from gtts import gTTS

TELEGRAM_TOKEN = "8657456868:AAHeypCVp-qfofC8x_cBjWI4asApHiJuN4M".strip()
GEMINI_API_KEY = "AQ.Ab8RN6IvOgXCwsV6RDqtXBJWLLhA2YOQ082FAoG2O7IFCamLPQ".strip()

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """
Sen SBD ERP.0 (https://isbd.uz/sbd-erp) korxona resurslarini rejalashtirish dasturining aqlli yordamchi assistentisan.
Sening vazifang foydalanuvchilarning savollariga o'zbek tilida qisqa, aniq va tushunarli javob berish.
"""

# Ovozli xabar yuborishni kafolatlaydigan yaxshilangan funksiya
def send_voice_reply(message, text_response):
    audio_path = "reply_voice.ogg"
    try:
        # Matnni ovozga aylantiramiz
        tts = gTTS(text=text_response, lang='uz', slow=False)
        tts.save(audio_path)
        
        # Telegramga ovozli xabar sifatida yuboramiz
        with open(audio_path, 'rb') as audio:
            bot.send_voice(message.chat.id, audio, reply_to_message_id=message.message_id)
            
        # Baribir qulay bo'lishi uchun matnni ham birga yuborib qo'yamiz
        bot.reply_to(message, f"📝 *Matnli javob:* \n{text_response}", parse_mode="Markdown")
    except Exception as e:
        print(f"Ovoz chiqarishda xatolik: {e}")
        # Agar ovozda xato bo'lsa, hech bo'lmasa matn chiqishini ta'minlaymiz
        bot.reply_to(message, text_response)
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)

@bot.message_handler(commands=["start"])
def send_welcome(message):
    bot.reply_to(message, "Assalomu alaykum! SBD ERP.0 yordamchi botiga xush kelibsiz. Menga istalgan savolni yuboring, ovozli javob qaytaraman! 🎙️")

# Matnli xabarlar uchun
@bot.message_handler(content_types=['text'])
def handle_text(message):
    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=f"{SYSTEM_PROMPT}\n\nFoydalanuvchi savoli: {message.text}",
        )
        send_voice_reply(message, response.text)
    except Exception as e:
        print(f"Xatolik: {e}")
        bot.reply_to(message, "Kechirasiz, xatolik yuz berdi. 🤖")

# Ovozli xabarlar uchun
@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    voice_path = "voice_msg.ogg"
    try:
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        with open(voice_path, "wb") as f:
            f.write(downloaded_file)
            
        audio_file = client.files.upload(file=voice_path)
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=[audio_file, f"{SYSTEM_PROMPT}\n\nUshbu ovozli xabarni tingla va foydalanuvchining savoliga o'zbek tilida qisqa javob ber."]
        )
        send_voice_reply(message, response.text)
    except Exception as e:
        print(f"Ovozli xatolik: {e}")
        bot.reply_to(message, "Kechirasiz, ovozli xabarni o'qishda xatolik yuz berdi. 🤖")
    finally:
        if os.path.exists(voice_path):
            os.remove(voice_path)

# Rasmlar uchun
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    photo_path = "photo_msg.jpg"
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        with open(photo_path, "wb") as f:
            f.write(downloaded_file)
            
        image_file = client.files.upload(file=photo_path)
        caption_text = message.caption if message.caption else "Rasmni tahlil qil"
        
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=[image_file, f"{SYSTEM_PROMPT}\n\nFoydalanuvchi rasmni yubordi. Izoh: {caption_text}. Tahlil qilib javob yoz."]
        )
        send_voice_reply(message, response.text)
    except Exception as e:
        print(f"Rasm xatoligi: {e}")
        bot.reply_to(message, "Kechirasiz, rasmni tahlil qilishda xatolik yuz berdi. 🤖")
    finally:
        if os.path.exists(photo_path):
            os.remove(photo_path)

# Videolar uchun
@bot.message_handler(content_types=['video_note', 'video'])
def handle_video(message):
    video_path = "video_msg.mp4"
    try:
        file_id = message.video_note.file_id if message.content_type == 'video_note' else message.video.file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        with open(video_path, "wb") as f:
            f.write(downloaded_file)
            
        video_file = client.files.upload(file=video_path)
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=[video_file, f"{SYSTEM_PROMPT}\n\nFoydalanuvchi videoni yubordi. Holatni tahlil qilib javob ber."]
        )
        send_voice_reply(message, response.text)
    except Exception as e:
        print(f"Video xatoligi: {e}")
        bot.reply_to(message, "Kechirasiz, videoni tahlil qilishda xatolik yuz berdi. 🤖")
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)

print("Bot ovozli javob berish rejimida ishga tushdi...")
bot.infinity_polling()