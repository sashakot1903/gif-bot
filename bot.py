import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from ddgs import DDGS
from flask import Flask
import threading
import os

# ========== ТОКЕНЫ ==========
TOKEN = "8805622551:AAHfWYzYxRIu6yvscAR2di8i3uVNgA2Jj7k"
GIPHY_API_KEY = "Kcl6ZiWCQv056JOPBEz7km6MFpYG0Z40"

# ========== НАСТРОЙКА ==========
bot = Bot(token=TOKEN)
dp = Dispatcher()
app = Flask(__name__)

# ========== ПОИСК ГИФОК ==========
async def search_giphy(query: str, limit: int = 30):
    url = "https://api.giphy.com/v1/gifs/search"
    params = {
        "api_key": GIPHY_API_KEY,
        "q": query,
        "limit": limit,
        "rating": "r",
        "lang": "ru"
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as resp:
                data = await resp.json()
                if data.get("data"):
                    return [item["images"]["original"]["url"] for item in data["data"]]
    except Exception as e:
        print(f"GIPHY error: {e}")
    return []

async def search_ddg(query: str, limit: int = 15):
    try:
        with DDGS() as ddgs:
            results = list(ddgs.images(query, max_results=limit))
            gifs = [res["image"] for res in results if res["image"].endswith(".gif")]
            return gifs
    except Exception as e:
        print(f"DDG error: {e}")
    return []

# ========== ОБРАБОТЧИКИ ==========
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(
        "🎬 Привет! Я ищу гифки без цензуры!\n\n"
        f"Просто напиши в любом чате:\n"
        f"`@{bot.username} кот`\n\n"
        "И я покажу гифки по твоему запросу.",
        parse_mode="Markdown"
    )

@dp.inline_query()
async def inline_gif(inline_query: types.InlineQuery):
    query = inline_query.query.strip()
    if not query:
        await inline_query.answer([], cache_time=1)
        return

    gifs = await search_giphy(query)
    if not gifs:
        gifs = await search_ddg(query)

    if not gifs:
        result = types.InlineQueryResultArticle(
            id="not_found",
            title="😅 Ничего не найдено",
            description=f"По запросу «{query}» гифок нет",
            input_message_content=types.InputTextMessageContent(
                f"🤷♂️ Ни одной гифки по запросу «{query}»"
            )
        )
        await inline_query.answer([result], cache_time=10)
        return

    results = []
    for i, url in enumerate(gifs[:50]):
        results.append(
            types.InlineQueryResultGif(
                id=str(i),
                gif_url=url,
                thumbnail_url=url,
                title=f"Гифка #{i+1}"
            )
        )
    await inline_query.answer(results, cache_time=300)

# ========== Flask для health check ==========
@app.route('/')
def health():
    return "Bot is running! 🚀"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# ========== ЗАПУСК ==========
async def main():
    # Запускаем Flask в отдельном потоке (для health check на Render)
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    print("🤖 Bot is starting...")
    # Запускаем бота в polling режиме
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
