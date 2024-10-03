import logging
import os
from dotenv import load_dotenv

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import requests

load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
YANDEX_CLOUD_OAUTH_TOKEN = os.getenv('YANDEX_CLOUD_OAUTH_TOKEN')

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def get_yandex_gpt_response(user_input):
    try:
        endpoint = ''

        headers = {
            'Authorization': f'Bearer {YANDEX_CLOUD_OAUTH_TOKEN}',
            'Content-Type': 'application/json'
        }

        payload = {
            "text": user_input,
            "temperature": 0.7,
            "maxTokens": 150,
            "topP": 0.95,
            "topK": 50,
        }

        response = requests.post(endpoint, headers=headers, json=payload)
        response.raise_for_status()

        data = response.json()
        generated_text = data.get('predictions', [{}])[0].get('text', '').strip()
        return generated_text if generated_text else 'Извините, я не смог сгенерировать ответ.'
    except Exception as e:
        logger.error(f"Ошибка при обращении к Yandex GPT API: {e}")
        return "Извините, возникла проблема при обработке вашего запроса. Пожалуйста, попробуйте позже."


def start(update, context):
    update.message.reply_text(
        'Здравствуйте! Я бот технической поддержки. Опишите, пожалуйста, вашу проблему, и я постараюсь помочь.'
    )


def help_command(update, context):
    update.message.reply_text(
        'Вы можете задать мне любой вопрос, связанный с технической поддержкой, и я постараюсь помочь.'
    )


def handle_message(update, context):
    user_message = update.message.text
    user_id = update.effective_chat.id

    logger.info(f"Получено сообщение от пользователя {user_id}: {user_message}")

    reply = get_yandex_gpt_response(user_message)
    update.message.reply_text(reply)


def main():
    print(f"Токен Telegram бота: {TELEGRAM_BOT_TOKEN}")
    if TELEGRAM_BOT_TOKEN is None:
        logger.error("Токен Telegram бота не найден. Установите переменную окружения TELEGRAM_BOT_TOKEN.")
        return

    updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('help', help_command))

    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()
    logger.info("Бот запущен и ожидает сообщений...")

    updater.idle()


if __name__ == '__main__':
    main()
