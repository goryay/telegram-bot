import os
import re
import time
import types
import telebot
import threading
import requests.exceptions
from telebot import types
from dotenv import load_dotenv
from yandex_cloud_ml_sdk import YCloudML

load_dotenv()

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
    "система", "apt", "yum", "snap", "dpkg", "systemctl", "grub", "swap", "root", "boot", "sudo", "bash"
]


def is_technical_question(question):
    for keyword in TECHNICAL_KEYWORDS:
        if keyword.lower() in question.lower():
            print(f"[LOG] Вопрос '{question}' классифицирован как ТЕХНИЧЕСКИЙ ✅")
            return True

    print(f"[LOG] Вопрос '{question}' НЕ является техническим ❌")
    return False


def generation_answer_via_assistant(question):
    """
    Запрос в ассистент, который сначала ищет в файле, а затем в GPT.
    """
    thread.write(f"Предыдущие вопросы и ответы: {thread.read()}\n\nТекущий вопрос: {question}")
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


def clean_markdown_output(text):
    text = re.sub(r"^#+\s*", "**", text, flags=re.MULTILINE)
    text = re.sub(r"\\([.,()])", r"\1", text)
    text = re.sub(r"\\-", "-", text)
    text = re.sub(r"\\\*", "*", text)
    return text.strip()


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
    user_question = message.text

    if user_question in ["🛠 Справка", "💬 Задать вопрос", "ℹ️ О боте", "🔄 Перезапуск (Reset)", "🆘 Поддержка"]:
        if user_question == "🛠 Справка":
            bot.send_message(chat_id, "Я могу помочь с техническими вопросами. Просто напишите ваш вопрос.")
        elif user_question == "💬 Задать вопрос":
            bot.send_message(chat_id, "Напишите ваш вопрос, и я постараюсь найти ответ.")
        elif user_question == "ℹ️ О боте":
            bot.send_message(chat_id, "Я бот технической поддержки. Постараюсь помочь с Вашей проблемой.")
        elif user_question == "🆘 Поддержка":
            bot.send_message(chat_id, "Если остались вопросы, напишите на почту: .")
        elif user_question == "🔄 Перезапуск (Reset)":
            bot.send_message(chat_id, "Сброс выполнен. Вы можете задать новый вопрос.")
            start_message(message)
        return

    if not is_technical_question(user_question):
        bot.send_message(chat_id, "Этот запрос не относится к техническим вопросам. Пожалуйста, задайте другой вопрос.")
        return

    bot.send_message(chat_id, "🔍 Выполняется поиск...")

    assistant_answer = generation_answer_via_assistant(user_question)

    if assistant_answer:
        bot.send_message(chat_id,
                         f"**Ваш вопрос:** {clean_markdown_output(user_question)}\n\n"
                         f"**Ответ:**\n{clean_markdown_output(assistant_answer)}",
                         parse_mode="Markdown")
    else:
        gpt_answer = generation_answer_via_gpt(user_question)
        if gpt_answer:
            bot.send_message(chat_id,
                             f"**Ваш вопрос:** {clean_markdown_output(user_question)}\n\n"
                             f"**Ответ найден через Yandex GPT:**\n{clean_markdown_output(gpt_answer)}",
                             parse_mode="Markdown"
                             )
        else:
            bot.send_message(chat_id, "Извините, не удалось найти информацию по вашему запросу.")


if __name__ == "__main__":
    while True:
        try:
            print("🚀 Бот запущен!")
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
