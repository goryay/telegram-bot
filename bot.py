import os
from dotenv import load_dotenv
import telebot
from telebot import types
from docx import Document
from yandex_cloud_ml_sdk import YCloudML
import difflib
import re

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
YANDEX_CLOUD_FOLDER_ID = os.getenv("YANDEX_CLOUD_FOLDER_ID")
YANDEX_CLOUD_OAUTH_TOKEN = os.getenv("YANDEX_CLOUD_OAUTH_TOKEN")

ycloud = YCloudML(folder_id=YANDEX_CLOUD_FOLDER_ID, auth=YANDEX_CLOUD_OAUTH_TOKEN)
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)


# Функция для загрузки документа
def load_document(filepath):
    doc = Document(filepath)
    return [paragraph.text.strip() for paragraph in doc.paragraphs if paragraph.text.strip()]


document_data = load_document("qa.docx")


# Функция для поиска релевантного контекста
def find_relevant_context(question, document, cutoff=0.5):
    matches = difflib.get_close_matches(question.lower(), [p.lower() for p in document], n=1, cutoff=cutoff)
    if matches:
        return next(p for p in document if p.lower() == matches[0])
    return None


# Функция для определения технического вопроса
def is_technical_question(question, document):
    relevant_context = find_relevant_context(question, document, cutoff=0.3)
    if relevant_context:
        return True

    technical_keywords = [
        "IPMI", "BIOS", "RAID", "вентилятор", "сервер", "контроллер", "OC", "сеть", "SSH", "драйвер", "API"
    ]
    for keyword in technical_keywords:
        if keyword.lower() in question.lower():
            return True
    return False


# Генерация ответа через Yandex GPT
def generate_answer_via_gpt(question):
    model = ycloud.models.completions("yandexgpt").configure(temperature=0.5)
    prompt = f"Пожалуйста, предоставьте конкретный ответ на следующий вопрос:\nВопрос: {question}\nОтвет:"
    result = model.run(prompt)
    if result:
        return result[0].text.strip()
    return "Извините, не удалось найти информацию по вашему запросу."


# Экранирование Markdown
def escape_markdown(text):
    return re.sub(r'([_*[\]()~`>#+\-=|{}.!])', r'\\\1', text)


# Приветственное сообщение
@bot.message_handler(commands=["start", "restart"])
def start_message(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🛠 Справка", "💬 Задать вопрос", "ℹ️ О боте", "🔄 Перезапуск (Reset)")

    bot.send_message(
        message.chat.id,
        "Привет! Я бот технической поддержки. Выберите нужную опцию из меню ниже:",
        reply_markup=markup,
    )


# Обработка текстовых сообщений
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    user_question = message.text

    if user_question in ["🛠 Справка", "💬 Задать вопрос", "ℹ️ О боте", "🔄 Перезапуск (Reset)"]:
        if user_question == "🛠 Справка":
            bot.send_message(chat_id, "Я могу помочь с техническими вопросами. Просто напишите ваш вопрос.")
        elif user_question == "💬 Задать вопрос":
            bot.send_message(chat_id, "Напишите ваш вопрос, и я постараюсь найти ответ.")
        elif user_question == "ℹ️ О боте":
            bot.send_message(chat_id, "Я бот технической поддержки. Сначала ищу информацию в документации.")
        elif user_question == "🔄 Перезапуск (Reset)":
            bot.send_message(chat_id, "Сброс выполнен. Вы можете задать новый вопрос.")
            start_message(message)
        return

    if not is_technical_question(user_question, document_data):
        bot.send_message(chat_id, "Этот запрос не относится к техническим вопросам. Пожалуйста, задайте другой вопрос.")
        return

    relevant_context = find_relevant_context(user_question, document_data)
    if relevant_context:
        formatted_message = (
            f"**Ваш вопрос:**\n{escape_markdown(user_question)}\n\n"
            f"**Ответ из документации:**\n{escape_markdown(relevant_context)}"
        )
        bot.send_message(chat_id, formatted_message, parse_mode="Markdown")
    else:
        bot.send_message(chat_id, "Выполняется поиск...")
        gpt_answer = generate_answer_via_gpt(user_question)
        formatted_message = (
            f"**Ваш вопрос:**\n{user_question}\n\n"
            f"**Ответ найден:**\n{gpt_answer}"
        )
        bot.send_message(chat_id, formatted_message, parse_mode="Markdown")


if __name__ == "__main__":
    bot.polling()
