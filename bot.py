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
    os_hint, device_hint = extract_filters(question)
    instructions = generate_instructions(os_hint, device_hint)

    previous_questions = thread.read()
    if previous_questions:
        prompt = f"{instructions}\n\nКонтекст предыдущего обсуждения: {previous_questions}\n\nТекущий вопрос: {question}"
    else:
        prompt = f"{instructions}\n\nТекущий вопрос: {question}"

    thread.write(prompt)
    run = assistant.run(thread)
    result = run.wait()
    return result.text if result.text else "Извините, не удалось найти информацию."


def generation_answer_via_gpt(question):
    model = ycloud.models.completions("yandexgpt").configure(temperature=0.5)
    prompt = f"Пожалуйста, предоставьте конкретный ответ на следующий вопрос:\nВопрос: {question}\nОтвет:"
    result = model.run(prompt)
    return result[0].text.strip() if result else "Извините, не удалось найти информацию."


def ask_for_clarification(chat_id, question):
    os_hint, _ = extract_filters(question)
    if not os_hint:
        markup = types.InlineKeyboardMarkup()
        for os_name in OS_FILTERS:
            markup.add(types.InlineKeyboardButton(text=os_name, callback_data=f"os_{os_name}"))
        bot.send_message(chat_id, "Уточните, пожалуйста, для какой ОС вам нужна инструкция:", reply_markup=markup)
        user_context[chat_id] = {"pending": question, "status": "waiting_os_selection"}
        return

    clarifying = generate_clarifying_question(question)
    if clarifying:
        bot.send_message(chat_id, clarifying)
        user_context[chat_id] = {"pending": question, "status": "waiting_dynamic_clarification"}
    else:
        bot.send_message(chat_id, "Пожалуйста, уточните ваш вопрос.")


def generate_clarifying_question(question):
    model = ycloud.models.completions("yandexgpt").configure(temperature=0.7)
    prompt = f"Ты технический помощник. Пользователь задал неясный вопрос:\n\"{question}\"\nСформулируй один уточняющий вопрос, чтобы лучше понять проблему:"
    result = model.run(prompt)
    return result[0].text.strip() if result else None


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
    if isinstance(last_question, str) and user_question in SHORT_REPLIES:
        user_question = f"{last_question} → {user_question}"
    else:
        user_context[chat_id] = user_question

    if not is_technical_question(normalize_question(user_question), last_question, TECHNICAL_KEYWORDS):
        ask_for_clarification(chat_id, user_question)
        return

    os_hint, _ = extract_filters(user_question)
    if not os_hint:
        ask_for_clarification(chat_id, user_question)
        return

    bot.send_message(chat_id, "🔍 Выполняется поиск...")

    assistant_answer = generation_answer_via_assistant(user_question)
    if assistant_answer:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Ответ помог", callback_data=f"helpful_{message.message_id}"))
        markup.add(types.InlineKeyboardButton("Ответ не помог", callback_data=f"not_helpful_{message.message_id}"))
        bot.send_message(chat_id,
                         f"**Ваш вопрос:** {clean_markdown_output(user_question)}\n\n"
                         f"**Ответ:**\n{escape_markdown(assistant_answer)}",
                         parse_mode="MarkdownV2",
                         reply_markup=markup)
        return

    gpt_answer = generation_answer_via_gpt(user_question)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Ответ помог", callback_data=f"helpful_{message.message_id}"))
    markup.add(types.InlineKeyboardButton("Ответ не помог", callback_data=f"not_helpful_{message.message_id}"))
    bot.send_message(chat_id,
                     f"**Ваш вопрос:** {clean_markdown_output(user_question)}\n\n"
                     f"**Ответ найден через Yandex GPT:**\n{escape_markdown(gpt_answer)}",
                     parse_mode="MarkdownV2",
                     reply_markup=markup)


@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    data = call.data

    if data.startswith("os_"):
        os_choice = data.replace("os_", "")
        pending = user_context.get(chat_id, {}).get("pending")
        if pending:
            full_question = f"{pending} {os_choice}"
            bot.send_message(chat_id, f"Спасибо! Продолжаю поиск для: *{full_question}*", parse_mode="Markdown")
            assistant_answer = generation_answer_via_assistant(full_question)
            bot.send_message(chat_id, f"**Ответ:**\n{escape_markdown(assistant_answer)}", parse_mode="MarkdownV2")
            user_context[chat_id] = full_question

    elif data.startswith("helpful_") or data.startswith("not_helpful_"):
        message_id = call.message.message_id
        parts = call.message.text.split("\n\n")
        question = parts[0].replace("**Ваш вопрос:** ", "").strip()
        answer = parts[1].replace("**Ответ:**\n", "").strip()

        if data.startswith("helpful_"):
            bot.answer_callback_query(call.id, "Спасибо за отзыв!")
            bot.edit_message_reply_markup(chat_id, message_id, reply_markup=None)
            log_feedback(question, answer, "Ответ помог", STATISTICS_FILE)
        elif data.startswith("not_helpful_"):
            bot.answer_callback_query(call.id, "Спасибо за отзыв! Попробуем улучшить ответ.")
            bot.edit_message_reply_markup(chat_id, message_id, reply_markup=None)
            log_feedback(question, answer, "Ответ не помог", STATISTICS_FILE)
            user_context[chat_id] = question
            bot.send_message(chat_id, "Пожалуйста, уточните вашу проблему, и я постараюсь помочь.")


def ping_telegram():
    while True:
        try:
            bot.get_me()
            print("✅ API Telegram работает!")
        except Exception as e:
            print(f"⚠️ Ошибка API Telegram: {e}")
        time.sleep(300)  # 5 минут


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
