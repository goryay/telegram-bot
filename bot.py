import os
import time
import string
import telebot
import threading
import requests.exceptions
from telebot import types
from dotenv import load_dotenv
from yandex_cloud_ml_sdk import YCloudML

load_dotenv()

CHAT_ID = os.getenv("CHAT_ID")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
YANDEX_CLOUD_FOLDER_ID = os.getenv("YANDEX_CLOUD_FOLDER_ID")
YANDEX_CLOUD_OAUTH_TOKEN = os.getenv("YANDEX_CLOUD_OAUTH_TOKEN")

ycloud = YCloudML(folder_id=YANDEX_CLOUD_FOLDER_ID, auth=YANDEX_CLOUD_OAUTH_TOKEN)
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

file = ycloud.files.upload("qa.md", ttl_days=5, expiration_policy="static")

operation = ycloud.search_indexes.create_deferred([file])
search_index = operation.wait()

tool = ycloud.tools.search_index(search_index)
assistant = ycloud.assistants.create("yandexgpt", tools=[tool])
thread = ycloud.threads.create()

TECHNICAL_KEYWORDS = [
    "IPMI", "BIOS", "RAID", "вентилятор", "сервер", "контроллер", "ОС", "сеть", "SSH", "драйвер", "API",
    "Windows", "Linux", "Ubuntu", "Debian", "Arch", "CentOS", "Fedora", "виндовс", "винду", "переустановка",
    "восстановление", "диагностика", "логи", "видеокарта", "VGA", "SSD", "HDD", "UEFI", "POST", "разгон",
    "установка", "железо", "процессор", "чипсет", "интерфейс", "настройка", "оперативная память", "режим",
    "порт", "дисковая система", "материнская плата", "разгон", "хранилище", "охлаждение", "конфигурация",
    "система", "apt", "yum", "snap", "dpkg", "systemctl", "grub", "swap", "root", "boot", "sudo", "bash",
    "Astra", "Astra Linux", "Clonezilla", "Supermicro", "IPDROM", "RAID-контроллер", "гипервизор", "GPT",
    "PXE-загрузка", "KVM", "LiveCD"
]

# Словарь для хранения контекста беседы
user_context = {}

def normalize_question(question):
    return question.translate(str.maketrans("", "", string.punctuation)).lower()

def is_technical_question(question):
    normalized_question = normalize_question(question)

    for keyword in TECHNICAL_KEYWORDS:
        if keyword.lower() in normalized_question:
            print(f"[LOG] Вопрос '{question}' классифицирован как ТЕХНИЧЕСКИЙ ✅ (ключевое слово: {keyword})")
            return True

    print(f"[LOG] Вопрос '{question}' НЕ является техническим ❌")
    return False

def generation_answer_via_assistant(question):
    """
    Запрос в ассистент, который сначала ищет в файле, а затем в GPT.
    """
    previous_questions = user_context.get("previous_question", "")

    if previous_questions:
        prompt = f"Контекст предыдущего обсуждения: {previous_questions}\n\nТекущий вопрос: {question}"
    else:
        prompt = f"Текущий вопрос: {question}"

    thread.write(prompt)
    run = assistant.run(thread)
    result = run.wait()

    return result.text if result.text else "Извините, не удалось найти информацию."

def generation_answer_via_gpt(question):
    """
    Генерация ответа через Yandex GPT (если в файле ничего не найдено).
    """
    model = ycloud.models.completions("yandexgpt").configure(temperature=0.5)
    prompt = f"Пожалуйста, предоставьте конкретный ответ на следующий вопрос:\nВопрос: {question}\nОтвет:"
    result = model.run(prompt)
    return result[0].text.strip() if result else "Извините, не удалось найти информацию."

def escape_markdown_v2(text):
    """
    Экранирование спецсимволов для MarkdownV2 в Telegram.
    """
    escape_chars = r"_*[]()~`>#+-=|{}.!"
    return "".join(f"\\{char}" if char in escape_chars else char for char in text).strip()

@bot.message_handler(commands=["start", "restart"])
def start_message(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🛠 Справка", "💬 Задать вопрос", "ℹ️ О боте", "🔄 Перезапуск (Reset)")
    markup.add("🆘 Поддержка")

    bot.send_message(
        message.chat.id,
        "Привет! Я бот технической поддержки. Напишите ваш вопрос, и я постараюсь Вам помочь.",
        reply_markup=markup,
    )

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    user_question = message.text.strip()

    if user_question in ["🛠 Справка", "💬 Задать вопрос", "ℹ️ О боте", "🔄 Перезапуск (Reset)", "🆘 Поддержка"]:
        if user_question == "🛠 Справка":
            bot.send_message(chat_id, "Я могу помочь с техническими вопросами. Просто напишите ваш вопрос.")
        elif user_question == "💬 Задать вопрос":
            bot.send_message(chat_id, "Напишите ваш вопрос, и я постараюсь найти ответ.")
        elif user_question == "ℹ️ О боте":
            bot.send_message(chat_id, "Я бот технической поддержки. Постараюсь помочь с Вашей проблемой.")
        elif user_question == "🆘 Поддержка":
            bot.send_message(chat_id, "Если остались вопросы, напишите на почту: mtrx@ipdrom.ru.",
                             parse_mode="MarkdownV2")
        elif user_question == "🔄 Перезапуск (Reset)":
            bot.send_message(chat_id, "Сброс выполнен. Вы можете задать новый вопрос.")
            start_message(message)
        return

    # Проверка на продолжение диалога
    last_question = user_context.get(chat_id)

    # Если текущий вопрос не технический и нет предыдущего вопроса — отклоняем
    if not is_technical_question(user_question) and not last_question:
        bot.send_message(chat_id, "Этот запрос не относится к техническим вопросам. Пожалуйста, задайте другой вопрос.")
        return

    # Если предыдущий вопрос был задан недавно и текущий короткий, рассматриваем его как продолжение
    if last_question and len(user_question) < 20:
        print(f"[LOG] '{user_question}' рассматривается как продолжение диалога ✅")
        user_question = f"{last_question} → {user_question}"

    # Сохраняем текущий вопрос в контексте
    user_context[chat_id] = user_question

    bot.send_message(chat_id, "🔍 Выполняется поиск...")

    assistant_answer = generation_answer_via_assistant(user_question)

    if assistant_answer:
        bot.send_message(chat_id,
                         f"*Ваш вопрос:* {escape_markdown_v2(user_question)}\n\n"
                         f"*Ответ:*\n{escape_markdown_v2(assistant_answer)}",
                         parse_mode="MarkdownV2")
    else:
        gpt_answer = generation_answer_via_gpt(user_question)
        if gpt_answer:
            bot.send_message(chat_id,
                             f"*Ваш вопрос:* {escape_markdown_v2(user_question)}\n\n"
                             f"*Ответ найден через Yandex GPT:*\n{escape_markdown_v2(gpt_answer)}",
                             parse_mode="MarkdownV2")
        else:
            bot.send_message(chat_id, "Извините, не удалось найти информацию по вашему запросу.")


# Функция для периодического пинга Telegram API
def ping_telegram():
    while True:
        try:
            bot.get_me()
            print("✅ API Telegram работает!")
        except Exception as e:
            print(f"⚠️ Ошибка API Telegram: {e}")
        time.sleep(300)  # 5 минут


# Запускаем фоновые задачи
threading.Thread(target=ping_telegram, daemon=True).start()

if __name__ == "__main__":
    while True:
        try:
            print("🚀 Бот запущен!")
            bot.infinity_polling(timeout=60, long_polling_timeout=30)
        except requests.exceptions.ReadTimeout:
            print("⚠️ ReadTimeout! Telegram API не отвечает, пробуем снова через 10 секунд...")
            time.sleep(10)
        except requests.exceptions.ConnectionError:
            print("⚠️ ConnectionError! Проблема с подключением к Telegram API. Повтор через 15 секунд...")
            time.sleep(15)
        except Exception as e:
            print(f"⚠️ Ошибка: {e}")
            time.sleep(5)
        except KeyboardInterrupt:
            print("Завершение работы бота")
            bot.stop_polling()
            time.sleep(5)
            break
