import os
import asyncio
from flask import Flask
from pyrogram import Client, filters
from pytgcalls import PyTgCalls
from pytgcalls.types import AudioPiped
from yt_dlp import YoutubeDL
from openai import OpenAI

# --- CONFIGURATION ---
API_ID = int(os.environ.get("API_ID", "12345")) # Get from my.telegram.org
API_HASH = os.environ.get("API_HASH", "")       # Get from my.telegram.org
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")     # From @BotFather
HF_TOKEN = os.environ.get("HF_TOKEN", "")       # Hugging Face Token

# --- FLASK SERVER (For Render) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Music Bot is Running!"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# --- AI SETUP ---
ai_client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=HF_TOKEN
)

# --- TELEGRAM BOT SETUP ---
# We use a combined Bot + Userbot approach
bot = Client(
    "MusicBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

call_py = PyTgCalls(bot)

# Youtube-DL options
ytdl_opts = {
    "format": "bestaudio/best",
    "quiet": True,
    "no_warnings": True,
}

# --- MUSIC COMMAND ---
@bot.on_message(filters.command("play") & filters.group)
async def play_music(client, message):
    if len(message.command) < 2:
        return await message.reply("❌ Please provide a song name.\nExample: `/play Blinding Lights`")

    query = " ".join(message.command[1:])
    m = await message.reply("🔎 Searching on YouTube...")

    try:
        with YoutubeDL(ytdl_opts) as ytdl:
            info_dict = ytdl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
            url = info_dict['url']
            title = info_dict['title']

        await call_py.join_group_call(
            message.chat.id,
            AudioPiped(url)
        )
        await m.edit(f"🎶 **Playing:** {title}")
    except Exception as e:
        await m.edit(f"❌ Error: {str(e)}")

# --- AI COMMAND (DeepSeek) ---
@bot.on_message(filters.command("ai") & filters.group)
async def ai_chat(client, message):
    if len(message.command) < 2:
        return await message.reply("Ask me something! Example: `/ai how to bake a cake?`")

    user_input = " ".join(message.command[1:])
    
    try:
        chat_completion = ai_client.chat.completions.create(
            model="deepseek-ai/DeepSeek-R1:novita",
            messages=[{"role": "user", "content": user_input}],
            max_tokens=500
        )
        response = chat_completion.choices[0].message.content
        await message.reply(response)
    except Exception as e:
        await message.reply(f"❌ AI Error: {str(e)}")

# --- STOP COMMAND ---
@bot.on_message(filters.command("stop") & filters.group)
async def stop_music(client, message):
    try:
        await call_py.leave_group_call(message.chat.id)
        await message.reply("⏹ Stopped music and left Voice Chat.")
    except:
        await message.reply("❌ No music playing.")

# --- START THE BOT ---
async def start_bot():
    import threading
    threading.Thread(target=run_flask, daemon=True).start()
    
    await bot.start()
    await call_py.start()
    print("Bot is online!")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(start_bot())
