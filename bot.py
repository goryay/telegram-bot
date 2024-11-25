import os
from dotenv import load_dotenv
import telebot
from telebot import types
from docx import Document
from yandex_cloud_ml_sdk import YCloudML
import difflib

# Загрузка переменных из .env
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
YANDEX_CLOUD_FOLDER_ID = os.getenv("YANDEX_CLOUD_FOLDER_ID")
YANDEX_CLOUD_OAUTH_TOKEN = os.getenv("YANDEX_CLOUD_OAUTH_TOKEN")

# Инициализация SDK и Telegram-бота
ycloud = YCloudML(folder_id=YANDEX_CLOUD_FOLDER_ID, auth=YANDEX_CLOUD_OAUTH_TOKEN)
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Хранилище состояний диалога
user_states = {}


# Функция для загрузки документа
def load_document(filepath):
    doc = Document(filepath)
    return [paragraph.text.strip() for paragraph in doc.paragraphs if paragraph.text.strip()]


# Загрузка документа с вопросами и ответами
document_data = load_document("qa.docx")


# Функция для поиска наиболее подходящего контекста
def find_relevant_context(question, document):
    matches = difflib.get_close_matches(question.lower(), [p.lower() for p in document], n=1, cutoff=0.1)
    if matches:
        return next(p for p in document if p.lower() == matches[0])
    return None


# Функция для обработки текста, чтобы убрать лишние символы
def clean_response(response):
    if hasattr(response, "text"):
        return response.text.strip()
    return "Извините, произошла ошибка с форматом ответа."


# Функция для генерации ответа через YandexGPT
def generate_answer(question, context):
    model = ycloud.models.completions("yandexgpt").configure(temperature=0.7)
    prompt = f"Вопрос: {question}\nКонтекст: {context}\nОтвет:"
    result = model.run(prompt)
    if result:
        return clean_response(result[0])
    return "Извините, не удалось сгенерировать ответ."


# Приветственное сообщение и меню
@bot.message_handler(commands=["start"])
def start_message(message):
    # Инициализируем состояние пользователя
    user_states[message.chat.id] = {"context": None, "previous_question": None}

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("🛠 Справка")
    btn2 = types.KeyboardButton("💬 Задать вопрос")
    btn3 = types.KeyboardButton("ℹ️ О боте")
    markup.add(btn1, btn2, btn3)

    bot.send_message(
        message.chat.id,
        "Привет! Я бот технической поддержки. Выберите нужную опцию из меню ниже:",
        reply_markup=markup,
    )


# Обработчик текстовых сообщений
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id

    if message.text == "🛠 Справка":
        bot.send_message(
            message.chat.id,
            "Я могу помочь с техническими вопросами. Просто напишите ваш вопрос или выберите другую опцию.",
        )
    elif message.text == "💬 Задать вопрос":
        bot.send_message(
            message.chat.id,
            "Напишите ваш вопрос, и я постараюсь найти ответ."
        )
    elif message.text == "ℹ️ О боте":
        bot.send_message(
            message.chat.id,
            "Я бот технической поддержки, созданный для помощи с вашими запросами. "
            "Моя база данных содержит решения для различных проблем. Задайте ваш вопрос!"
        )
    elif message.text.lower() == "продолжить":
        # Проверяем, есть ли сохраненный контекст
        if chat_id in user_states and user_states[chat_id]["context"]:
            previous_context = user_states[chat_id]["context"]
            bot.send_message(
                message.chat.id,
                f"Хорошо, продолжим с этим контекстом:\n{previous_context}\n\nПожалуйста, уточните ваш вопрос.",
            )
        else:
            bot.send_message(
                message.chat.id,
                "Контекста для продолжения нет. Пожалуйста, задайте новый вопрос."
            )
    else:
        user_question = message.text

        # Найти релевантный контекст
        relevant_context = find_relevant_context(user_question, document_data)

        if not relevant_context:
            bot.send_message(message.chat.id, "Контекст для вашего вопроса не найден.")
            return

        # Генерация ответа
        answer = generate_answer(user_question, relevant_context)

        # Сохранение состояния пользователя
        user_states[chat_id] = {
            "context": relevant_context,
            "previous_question": user_question,
        }

        # Форматируем сообщение перед отправкой
        formatted_message = f"**Ваш вопрос:**\n{user_question}\n\n**Ответ:**\n{answer}\n\nЕсли ответ частично подходит, напишите 'Продолжить', чтобы уточнить вопрос."
        bot.send_message(message.chat.id, formatted_message, parse_mode="Markdown")


# Запуск бота
if __name__ == "__main__":
    bot.polling()
