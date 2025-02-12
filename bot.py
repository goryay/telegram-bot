import os
import re
import time
import datetime
import telebot
import difflib
import threading
import requests.exceptions
from telebot import types
from dotenv import load_dotenv
from difflib import SequenceMatcher
from yandex_cloud_ml_sdk import YCloudML

load_dotenv()

CHAT_ID = os.getenv("CHAT_ID")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
YANDEX_CLOUD_FOLDER_ID = os.getenv("YANDEX_CLOUD_FOLDER_ID")
YANDEX_CLOUD_OAUTH_TOKEN = os.getenv("YANDEX_CLOUD_OAUTH_TOKEN")

ycloud = YCloudML(folder_id=YANDEX_CLOUD_FOLDER_ID, auth=YANDEX_CLOUD_OAUTH_TOKEN)
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

start_time = datetime.datetime.now()


def get_uptime():
    """Возвращает, сколько времени бот работает (формат: Часы:Минуты:Секунды)"""
    uptime = datetime.datetime.now() - start_time
    return str(uptime).split('.')[0]


def load_document(filepath):
    with open(filepath, "r", encoding="utf-8") as file:
        return file.read()


document_data = load_document("qa.md")


def is_technical_question(question):
    """
    Проверяет, относится ли вопрос к техническим темам.
    """
    technical_keywords = [
        "IPMI", "BIOS", "RAID", "вентилятор", "сервер", "контроллер", "ОС", "сеть", "SSH", "драйвер", "API",
        "Windows", "Linux", "Ubuntu", "Debian", "Arch", "CentOS", "Fedora", "виндовс", "винду", "переустановка",
        "восстановление",
        "диагностика", "логи", "видеокарта", "VGA", "SSD", "HDD", "UEFI", "POST", "разгон", "установка",
        "железо", "процессор", "чипсет", "интерфейс", "настройка", "оперативная память", "режим", "порт",
        "дисковая система", "материнская плата", "разгон", "хранилище", "охлаждение", "конфигурация",
        "система", "apt", "yum", "snap", "dpkg", "systemctl", "grub", "swap", "root", "boot", "sudo", "bash"
    ]

    for keyword in technical_keywords:
        if keyword.lower() in question.lower():
            print(f"[LOG] Вопрос '{question}' классифицирован как ТЕХНИЧЕСКИЙ ✅")
            return True

    print(f"[LOG] Вопрос '{question}' НЕ является техническим ❌")
    return False


def find_relevant_context(question, document, cutoff=0.4):
    """
    Ищет наиболее релевантный раздел в документации.
    """
    sections = re.split(r"\n# \d+\.", document)

    section_titles = []
    section_mapping = {}

    for section in sections:
        lines = section.strip().split("\n")
        if lines:
            title = lines[0]
            section_titles.append(title)
            section_mapping[title] = section

    # Ищем топ-3 наиболее похожих заголовка
    best_matches = difflib.get_close_matches(question, section_titles, n=3, cutoff=cutoff)

    best_match = None
    best_score = 0

    for match in best_matches:
        score = SequenceMatcher(None, question.lower(), match.lower()).ratio()
        if score > best_score:
            best_score = score
            best_match = match

    print(f"[LOG] Вопрос: {question} | Найден: {best_match} | Совпадение: {best_score:.2f}")

    if best_score < 0.3:
        return None

    return section_mapping[best_match]


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


# Очистка Markdown
def clean_markdown_output(text):
    """
    Очищает текст перед отправкой в Telegram, убирая лишние символы Markdown.
    """
    text = re.sub(r"^#+\s*", "**", text, flags=re.MULTILINE)  # Убираем `#` из заголовков
    text = re.sub(r"\\([.,()])", r"\1", text)  # Убираем обратные слэши перед знаками препинания
    text = re.sub(r"\\-", "-", text)  # Убираем лишние слэши перед `-`, чтобы списки выглядели нормально
    text = re.sub(r"\\\*", "*", text)  # Убираем экранирование `*`, если не используется в Markdown
    return text.strip()


# Команда /uptime (время работы бота)
@bot.message_handler(commands=["uptime"])
def uptime_message(message):
    bot.send_message(message.chat.id, f"⏳ Бот работает уже {get_uptime()}")


def send_alive_message():
    """
    Каждые 30 минут бот отправляет сообщение о том, что он работает.
    """
    chat_id = CHAT_ID
    while True:
        time.sleep(1800)  # 30 минут
        bot.send_message(chat_id, f"✅ Бот всё ещё работает! ⏳ Аптайм: {get_uptime()}")


threading.Thread(target=send_alive_message, daemon=True).start()


# Команда /start и /restart
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

    if not is_technical_question(user_question):
        bot.send_message(chat_id, "Этот запрос не относится к техническим вопросам. Пожалуйста, задайте другой вопрос.")
        return

    relevant_section = find_relevant_context(user_question, document_data)

    if relevant_section:
        bot.send_message(chat_id,
                         f"**Ваш вопрос:**\n{clean_markdown_output(user_question)}\n\n"
                         f"**Ответ из документации:**\n{clean_markdown_output(relevant_section)}",
                         parse_mode="Markdown")
    else:
        bot.send_message(chat_id, "Выполняется поиск...")
        gpt_answer = generate_answer_via_gpt(user_question)
        bot.send_message(chat_id,
                         f"**Ваш вопрос:**\n{clean_markdown_output(user_question)}\n\n"
                         f"**Ответ найден:**\n{clean_markdown_output(gpt_answer)}",
                         parse_mode="Markdown")


def ping_telegram():
    """Каждые 5 минут бот делает пустой запрос к API Telegram, чтобы не зависать."""
    while True:
        try:
            bot.get_me()
            print("✅ API Telegram работает!")
        except Exception as e:
            print(f"⚠️ Ошибка API Telegram: {e}")
        time.sleep(300)


threading.Thread(target=ping_telegram, daemon=True).start()
if __name__ == "__main__":
    while True:
        try:
            print("🚀 Бот запущен!")
            # bot.infinity_polling(timeout=30, long_polling_timeout=25)
            bot.infinity_polling(none_stop=True)
        except requests.exceptions.ReadTimeout:
            print("⚠️ ReadTimeout! Telegram API не отвечает, пробуем снова...")
            time.sleep(5)
        except Exception as e:
            print(f"⚠️ Ошибка: {e}")
            time.sleep(5)
        except KeyboardInterrupt:
            print(f"Завершение работы бота")
            bot.stop_polling()
            time.sleep(5)
            break
