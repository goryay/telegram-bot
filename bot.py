import os
from dotenv import load_dotenv
import telebot
from telebot import types
from yandex_cloud_ml_sdk import YCloudML
import re

# Загрузка переменных из .env
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
YANDEX_CLOUD_FOLDER_ID = os.getenv("YANDEX_CLOUD_FOLDER_ID")
YANDEX_CLOUD_OAUTH_TOKEN = os.getenv("YANDEX_CLOUD_OAUTH_TOKEN")

ycloud = YCloudML(folder_id=YANDEX_CLOUD_FOLDER_ID, auth=YANDEX_CLOUD_OAUTH_TOKEN)
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)


# Функция для загрузки документа
def load_document(filepath):
    with open(filepath, "r", encoding="utf-8") as file:
        return file.read()  # Читаем весь файл как строку


# Загрузка документа
document_data = load_document("qa.md")


# Функция для поиска релевантного раздела
def find_relevant_context(question, document):
    """
    Ищет релевантный раздел в документации
    """
    sections = re.split(r"\n# \d+\.", document)  # Разбиваем по заголовкам ("# 1.", "# 2.", и т.д.)

    best_match = None
    best_score = 0

    for section in sections:
        section_lower = section.lower()
        question_words = set(question.lower().split())

        match_score = sum(1 for word in question_words if word in section_lower)

        if match_score > best_score:
            best_score = match_score
            best_match = section.strip()

    return best_match if best_match else None


# Функция для определения технического вопроса (расширенная)
def is_technical_question(question, document):
    """
    Проверяет, является ли вопрос техническим, используя:
    1) Поиск в документации.
    2) Проверку ключевых технических терминов.
    """
    # Если найден релевантный раздел в документации — это технический вопрос
    if find_relevant_context(question, document):
        return True

    # Расширенный список технических терминов
    technical_keywords = [
        "IPMI", "BIOS", "RAID", "вентилятор", "сервер", "контроллер", "ОС", "сеть", "SSH", "драйвер", "API",
        "Windows", "Linux", "Ubuntu", "Debian", "Arch", "CentOS", "Fedora", "переустановка", "восстановление",
        "диагностика", "логи", "видеокарта", "VGA", "SSD", "HDD", "UEFI", "POST", "разгон", "установка",
        "железо", "процессор", "чипсет", "интерфейс", "настройка", "оперативная память", "режим", "порт",
        "дисковая система", "BIOS", "материнская плата", "разгон", "хранилище", "охлаждение", "конфигурация",
        "система", "apt", "yum", "snap", "dpkg", "systemctl", "grub", "swap", "root", "boot", "sudo", "bash"
    ]

    # Проверяем, содержатся ли ключевые слова в вопросе
    for keyword in technical_keywords:
        if keyword.lower() in question.lower():
            return True

    return False  # Если ни документация, ни ключевые слова не подходят

# Генерация ответа через Yandex GPT
def generate_answer_via_gpt(question):
    """
    Генерация ответа через Yandex GPT
    """
    model = ycloud.models.completions("yandexgpt").configure(temperature=0.5)
    prompt = f"Пожалуйста, предоставьте конкретный ответ на следующий вопрос:\nВопрос: {question}\nОтвет:"
    result = model.run(prompt)
    if result:
        return result[0].text.strip()
    return "Извините, не удалось найти информацию по вашему запросу."


# Экранирование Markdown
def escape_markdown(text):
    """
    Экранирует символы Markdown, чтобы Telegram корректно отображал текст
    """
    return re.sub(r'([_*[\]()~>#+\-=|{}.!])', r'\\\1', text)


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

    # Обработка кнопок
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

    # Проверяем, является ли вопрос техническим
    if not is_technical_question(user_question, document_data):
        bot.send_message(chat_id, "Этот запрос не относится к техническим вопросам. Пожалуйста, задайте другой вопрос.")
        return

    # Поиск в документации
    relevant_section = find_relevant_context(user_question, document_data)

    if relevant_section:
        formatted_message = (
            f"**Ваш вопрос:**\n{escape_markdown(user_question)}\n\n"
            f"**Ответ из документации:**\n{escape_markdown(relevant_section)}"
        )
        bot.send_message(chat_id, formatted_message, parse_mode="Markdown")
    else:
        # Использование Yandex GPT только если ничего не нашли в документации
        bot.send_message(chat_id, "Выполняется поиск...")
        gpt_answer = generate_answer_via_gpt(user_question)
        formatted_message = (
            f"**Ваш вопрос:**\n{escape_markdown(user_question)}\n\n"
            f"**Ответ найден:**\n{escape_markdown(gpt_answer)}"
        )
        bot.send_message(chat_id, formatted_message, parse_mode="Markdown")


if __name__ == "__main__":
    bot.polling()
