import logging
import time
import praw
import asyncio
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from deep_translator import GoogleTranslator
import threading

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Настройка Telegram бота и Reddit API
TELEGRAM_TOKEN = '8113878862:AAE4tqI7IunnrcLHdiXT92yJYaRUt-4rhlc'  # Ваш токен
reddit = praw.Reddit(
    client_id='kmg4Hwfv7eBW6Y8v4K2nVA',  # Ваш client_id
    client_secret='NuMvnCiBa60AeqIAQSChtW8H2BOehA',  # Ваш client_secret
    user_agent='script:ktkmbt:1.0 (by /u/ktkmbt)'  # Ваш user_agent
)

subreddit_name = ''  # Имя сабреддита
check_interval = 600  # Интервал проверки в секундах
last_post_id = None  # ID последнего поста
def translate_text(text, dest_language='ru'):
    try:
        translated = GoogleTranslator(source='auto', target=dest_language).translate(text)
        return translated
    except Exception as e:
        logging.error(f"Error during translation: {e}")
        return text  # Возвращаем оригинальный текст в случае ошибки

async def send_reddit_posts(chat_id):
    global last_post_id
    try:
        submission = next(reddit.subreddit(subreddit_name).new(limit=1))
        if submission.id != last_post_id:
            last_post_id = submission.id
            title = submission.title
            
            # Перевод заголовка
            translated_title = translate_text(title)

            # Проверка, является ли пост изображением или видео
            if submission.url.endswith(('.jpg', '.jpeg', '.png', '.gif')):
                await bot.send_photo(chat_id=chat_id, photo=submission.url, caption=translated_title)
            elif submission.is_video:
                await bot.send_video(chat_id=chat_id, video=submission.media['reddit_video']['fallback_url'], caption=translated_title)
    except Exception as e:
        logging.error(f"Error while sending post: {e}")

async def check_for_new_posts(chat_id):
    while True:
        await send_reddit_posts(chat_id)
        await asyncio.sleep(check_interval)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    await context.bot.send_message(chat_id=chat_id, text="Бот запущен! Вы будете получать обновления из сабреддита.")
    # Запускаем проверку новых постов в отдельном потоке
    threading.Thread(target=asyncio.run, args=(check_for_new_posts(chat_id),), daemon=True).start()

async def set_subreddit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global subreddit_name
    subreddit_name = context.args[0] if context.args else subreddit_name
    await update.message.reply_text(f"Сабреддит изменен на: {subreddit_name}")

async def get_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subreddit = subreddit_name  # Используем глобальную переменную для текущего сабреддита
    try:
        submission = next(reddit.subreddit(subreddit).new(limit=1))
        
        # Перевод заголовка
        translated_title = translate_text(submission.title)

        # Проверка, является ли пост изображением или видео
        if submission.url.endswith(('.jpg', '.jpeg', '.png', '.gif')):
            await update.message.reply_photo(photo=submission.url, caption=translated_title)
        elif submission.is_video:
            await update.message.reply_video(video=submission.media['reddit_video']['fallback_url'], caption=translated_title)
    except Exception as e:
        await update.message.reply_text("Не удалось получить пост. Попробуйте позже.")
        logging.error(f"Error while fetching post: {e}")

def main():
    global bot
    bot = Bot(token=TELEGRAM_TOKEN)
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("set_subreddit", set_subreddit))
    application.add_handler(CommandHandler("get_post", get_post))
    
    application.run_polling()

if __name__ == '__main__':
    main()