import os
import time
import threading
import requests.exceptions
import telebot
from telebot import types
from config import *
from utils import *

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
user_context = {}


def generation_answer_via_assistant(question):
    """
    Запрос в ассистент, который сначала ищет в файле, а затем в GPT.
    """
    previous_questions = thread.read()

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
            bot.send_message(chat_id, "Если остались вопросы, напишите на почту: mtrx@ipdrom.ru.",
                             parse_mode="Markdown")
        elif user_question == "🔄 Перезапуск (Reset)":
            bot.send_message(chat_id, "Сброс выполнен. Вы можете задать новый вопрос.")
            start_message(message)
        return

    last_question = user_context.get(chat_id)

    if last_question and user_question in SHORT_REPLIES:
        print(f"[LOG] '{user_question}' воспринимается как продолжение '{last_question}' ✅")
        user_question = f"{last_question} → {user_question}"
    else:
        user_context[chat_id] = user_question

    if not is_technical_question(normalize_question(user_question), last_question, TECHNICAL_KEYWORDS):
        bot.send_message(chat_id, "Этот запрос не относится к техническим вопросам. Пожалуйста, задайте другой вопрос.")
        return

    bot.send_message(chat_id, "🔍 Выполняется поиск...")

    assistant_answer = generation_answer_via_assistant(user_question)

    if assistant_answer:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Ответ помог", callback_data=f"helpful_{message.message_id}"))
        markup.add(types.InlineKeyboardButton("Ответ не помог", callback_data=f"not_helpful_{message.message_id}"))

        # Отправляем ответ с сохранением форматирования Markdown
        bot.send_message(chat_id,
                         f"**Ваш вопрос:** {clean_markdown_output(user_question)}\n\n"
                         f"**Ответ:**\n{escape_markdown(assistant_answer)}",
                         parse_mode="MarkdownV2",
                         reply_markup=markup)
    else:
        gpt_answer = generation_answer_via_gpt(user_question)
        if gpt_answer:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("Ответ помог", callback_data=f"helpful_{message.message_id}"))
            markup.add(types.InlineKeyboardButton("Ответ не помог", callback_data=f"not_helpful_{message.message_id}"))

            bot.send_message(chat_id,
                             f"**Ваш вопрос:** {clean_markdown_output(user_question)}\n\n"
                             f"**Ответ найден через Yandex GPT:**\n{escape_markdown(gpt_answer)}",
                             parse_mode="MarkdownV2",
                             reply_markup=markup)
        else:
            bot.send_message(chat_id, "Извините, не удалось найти информацию по вашему запросу.")


@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    data = call.data
    question = call.message.text.split("\n\n")[0].replace("**Ваш вопрос:** ", "")
    answer = call.message.text.split("\n\n")[1].replace("**Ответ:**\n", "").strip()

    if data.startswith("helpful_"):
        bot.answer_callback_query(call.id, "Спасибо за отзыв!")
        bot.edit_message_reply_markup(chat_id, message_id, reply_markup=None)
        log_feedback(question, answer, "Ответ помог", STATISTICS_FILE)
    elif data.startswith("not_helpful_"):
        bot.answer_callback_query(call.id, "Спасибо за отзыв! Попробуем улучшить ответ.")
        bot.edit_message_reply_markup(chat_id, message_id, reply_markup=None)
        log_feedback(question, answer, "Ответ не помог", STATISTICS_FILE)
        bot.send_message(chat_id, "Пожалуйста, уточните вашу проблему, и я постараюсь помочь.")


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
