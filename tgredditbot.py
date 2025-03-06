import logging
import praw
import asyncio
from deep_translator import GoogleTranslator
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Настройка Telegram бота и Reddit API
TELEGRAM_TOKEN = '8113878862:AAE4tqI7IunnrcLHdiXT92yJYaRUt-4rhlc'  # Ваш токен
reddit = praw.Reddit(
    client_id='kmg4Hwfv7eBW6Y8v4K2nVA',  # Ваш client_id
    client_secret='NuMvnCiBa60AeqIAQSChtW8H2BOehA',  # Ваш client_secret
    user_agent='script:ktkmbtkm:1.0 (by /u/ktkmbtkm)'  # Ваш user_agent
)

# Словарь для хранения сабреддитов для каждого чата
chat_settings = {}
check_interval = 10800  # Интервал проверки в секундах
last_post_id = {}  # Словарь для хранения ID последнего поста для каждого чата
last_message_id = {}  # Словарь для хранения ID последнего сообщения для каждого чата

def translate_text(text, target_language='ru'):
    try:
        translated = GoogleTranslator(source='auto', target=target_language).translate(text)
        return translated
    except Exception as e:
        logging.error(f"Error during translation: {e}")
        return text  # Возвращаем оригинальный текст в случае ошибки

async def send_reddit_posts(chat_id):
    global last_post_id
    try:
        if chat_id not in chat_settings or not chat_settings[chat_id]:
            return  # Если нет сабреддитов для этого чата, выходим

        for subreddit_name in chat_settings[chat_id]:
            submission = next(reddit.subreddit(subreddit_name).new(limit=1))
            if submission.id != last_post_id.get(chat_id):
                last_post_id[chat_id] = submission.id
                title = submission.title
                
                # Перевод заголовка
                translated_title = translate_text(title)

                # Проверка, является ли пост изображением или видео
                if submission.url.endswith(('.jpg', '.jpeg', '.png', '.gif')):
                    message = await bot.send_photo(chat_id=chat_id, photo=submission.url, caption=translated_title)
                elif submission.is_video:
                    message = await bot.send_video(chat_id=chat_id, video=submission.media['reddit_video']['fallback_url'], caption=translated_title)

                last_message_id[chat_id] = message.message_id
    except Exception as e:
        logging.error(f"Error while sending post: {e}")

async def check_for_new_posts(chat_id):
    while True:
        await send_reddit_posts(chat_id)
        await asyncio.sleep(check_interval)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    if chat_id not in chat_settings:
        chat_settings[chat_id] = []  # Инициализируем список сабреддитов для этого чата
    await context.bot.send_message(chat_id=chat_id, text="Бот запущен! Пропишите /help и ознакомьтесь с функционалом.")
    # Запускаем проверку новых постов
    asyncio.create_task(check_for_new_posts(chat_id))

async def set_subreddit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global chat_settings
    chat_id = update.message.chat.id
    if context.args:
        if chat_id not in chat_settings:
            chat_settings[chat_id] = []
        chat_settings[chat_id].append(context.args[0])
        await update.message.reply_text(f"Сабреддит {context.args[0]} добавлен для этого чата.")
    else:
        await update.message.reply_text("Пожалуйста, укажите имя сабреддита.")

async def remove_subreddit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global chat_settings
    chat_id = update.message.chat.id
    if context.args and chat_id in chat_settings and context.args[0] in chat_settings[chat_id]:
        chat_settings[chat_id].remove(context.args[0])
        await update.message.reply_text(f"Сабреддит {context.args[0]} удален из этого чата.")
    else:
        await update.message.reply_text("Сабреддит не найден или не указан.")

async def remove_all_subreddits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global chat_settings
    chat_id = update.message.chat.id
    if chat_id in chat_settings:
        chat_settings[chat_id] = []
        await update.message.reply_text("Все сабреддиты удалены из этого чата.")
    else:
        await update.message.reply_text("Нет сабреддитов для удаления.")

async def list_subreddits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    if chat_id in chat_settings and chat_settings[chat_id]:
        subreddits = ', '.join(chat_settings[chat_id])
        await update.message.reply_text(f"Сабреддиты для этого чата: {subreddits}")
    else:
        await update.message.reply_text("Нет сабреддитов для отслеживания в этом чате.")

async def get_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    try:
        if chat_id not in chat_settings or not chat_settings[chat_id]:
            await update.message.reply_text("Нет сабреддитов для отслеживания в этом чате.")
            return

        for subreddit_name in chat_settings[chat_id]:
            submission = next(reddit.subreddit(subreddit_name).new(limit=1))
            
            # Перевод заголовка
            translated_title = translate_text(submission.title)

            # Проверка, является ли пост изображением или видео
            if submission.url.endswith(('.jpg', '.jpeg', '.png', '.gif')):
                message = await update.message.reply_photo(photo=submission.url, caption=translated_title)
            elif submission.is_video:
                message = await update.message.reply_video(video=submission.media['reddit_video']['fallback_url'], caption=translated_title)

            last_message_id[chat_id] = message.message_id
    except Exception as e:
        await update.message.reply_text("Не удалось получить пост. Попробуйте позже.")
        logging.error(f"Error while fetching post: {e}")

async def edit_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id

    # Проверяем, есть ли последнее сообщение для редактирования
    if chat_id not in last_message_id or last_message_id[chat_id] is None:
        await update.message.reply_text("Не удалось найти последнее сообщение для редактирования.")
        return

    # Проверяем, есть ли текст для редактирования
    if not context.args:
        await update.message.reply_text("Пожалуйста, введите текст для редактирования заголовка.")
        return

    # Объединяем аргументы в один текстовый промт
    prompt = ' '.join(context.args)

    # Перевод заголовка
    translated_title = translate_text(prompt)

    # Отправка обновленного сообщения
    await context.bot.edit_message_caption(chat_id=chat_id, message_id=last_message_id[chat_id], caption=translated_title)
    await context.bot.send_message(chat_id=chat_id, text="Заголовок обновлен!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Доступные команды:\n"
        "/start - Запустить бота и получить обновления из сабреддита.\n"
        "/set_subreddit <имя_сабреддита> - Установить сабреддит для отслеживания.\n"
        "/remove_subreddit <имя_сабреддита> - Удалить сабреддит из отслеживания.\n"
        "/remove_all_subreddits - Удалить все сабреддиты из отслеживания.\n"
        "/list_subreddits - Показать все сабреддиты, которые отслеживаются.\n"
        "/get_post - Получить последний пост из всех установленных сабреддитов.\n"
        "/edit_mes <промт> - Редактировать последнее сообщение бота.\n"
        "/help - Показать это сообщение."
    )
    await update.message.reply_text(help_text)

def main():
    global bot
    bot = Bot(token=TELEGRAM_TOKEN)
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("set_subreddit", set_subreddit))
    application.add_handler(CommandHandler("remove_subreddit", remove_subreddit))
    application.add_handler(CommandHandler("remove_all_subreddits", remove_all_subreddits))
    application.add_handler(CommandHandler("list_subreddits", list_subreddits))
    application.add_handler(CommandHandler("get_post", get_post))
    application.add_handler(CommandHandler("edit_mes", edit_message))
    application.add_handler(CommandHandler("help", help_command))
    
    application.run_polling()

if __name__ == '__main__':
    main()