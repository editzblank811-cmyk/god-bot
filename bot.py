import re
import requests
import asyncio
import os
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import edge_tts

TOKEN = os.getenv("TOKEN")

headers = {"User-Agent": "Mozilla/5.0"}

# -------- SCRAPER --------
def fetch_text(url):
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "lxml")

        if "fanmtl.com" in url:
            content = soup.find("div", class_="entry-content")
        elif "wtr-lab.com" in url:
            content = soup.find("div", id="chapter-content")
        else:
            content = soup.find("body")

        if not content:
            return None

        return content.get_text("\n")
    except:
        return None

def get_novel_info(url):
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "lxml")

    title = soup.find("h1").text.strip()

    links = []
    for a in soup.find_all("a", href=True):
        if "chapter" in a["href"]:
            links.append(a["href"])

    links = list(set(links))

    def get_num(link):
        m = re.search(r'chapter[-_/ ]?(\d+)', link)
        return int(m.group(1)) if m else 0

    links.sort(key=get_num)

    return title, links

# -------- SPLIT --------
def split_text(text, max_chars=2000):
    parts = []
    while len(text) > max_chars:
        split_at = text[:max_chars].rfind(".")
        if split_at == -1:
            split_at = max_chars
        parts.append(text[:split_at])
        text = text[split_at:]
    parts.append(text)
    return parts

# -------- TTS --------
async def generate_audio(text, filename):
    communicate = edge_tts.Communicate(
        text=text,
        voice="en-IN-PrabhatNeural"
    )
    await communicate.save(filename)

# -------- COMMAND --------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 Audiobook Bot Ready!\n\nSend:\n/audiobook <link>"
    )

async def audiobook(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("Send link after command")

    url = context.args[0]

    await update.message.reply_text("📚 Detecting novel...")

    title, chapters = get_novel_info(url)

    max_chapters = 20
    chapters = chapters[:max_chapters]

    total = len(chapters)

    await update.message.reply_text(
        f"🎧 Audiobook Started\n\n📖 {title}\nChapters: {total}"
    )

    for i, ch_url in enumerate(chapters):
        await update.message.reply_text(f"⏳ {i+1}/{total}")

        text = fetch_text(ch_url)
        if not text:
            continue

        parts = split_text(text)

        for j, part in enumerate(parts):
            filename = f"voice_{i}_{j}.mp3"

            await generate_audio(part, filename)

            await update.message.reply_audio(
                open(filename, "rb"),
                caption=f"{title}\nChapter {i+1} Part {j+1}"
            )

            await asyncio.sleep(2)

    await update.message.reply_text("✅ Completed!")

# -------- RUN --------
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("audiobook", audiobook))

app.run_polling()
