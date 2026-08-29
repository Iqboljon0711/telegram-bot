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

    # Xavfsiz tekshiruv (candidates bor-yo'qligini tekshirish)
    if "candidates" in res_json and len(res_json["candidates"]) > 0:
      candidate = res_json["candidates"][0]
      if (
          "content" in candidate
          and "parts" in candidate["content"]
          and len(candidate["content"]["parts"]) > 0
      ):
        return candidate["content"]["parts"][0]["text"]

    # Agar boshqa tuzilishda yoki xato xabar kelsa
    return f"Javobni o'qishda xatolik: {res_json}"
  except Exception as e:
    return f"Xatolik yuz berdi: {str(e)}"
