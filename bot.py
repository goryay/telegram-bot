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

# Расширенные ключевые слова с многоуровневыми уточнениями
CLARIFICATION_KEYWORDS = {
    "установка": ["Выберите ОС:", "Windows", "Linux", "Astra"],
    "сервер": ["На какой ОС работает сервер?", "Windows", "Linux", "Astra"],
    "lsa": ["Где устанавливаете LSA?", "Сервер", "Рабочая станция"],
    "драйвер": ["Для какой ОС требуется драйвер?", "Windows", "Linux", "Astra"],
    "RAID": ["Какой тип RAID контроллера?", "LSI", "Intel", "Программный"]
}

FOLLOWUP_CLARIFICATIONS = {
    "Рабочая станция": ["Какая операционная система установлена на рабочей станции?", "Windows", "Linux", "Astra"],
    "Сервер": ["Какая операционная система установлена на сервере?", "Windows", "Linux", "Astra"]
}

OS_FILTERS = ["Windows", "Linux", "Ubuntu", "Astra"]
DEVICE_FILTERS = ["сервер", "рабочая станция", "компьютер"]


def extract_filters(question):
    os_hint = next((os for os in OS_FILTERS if os.lower() in question.lower()), None)
    device_hint = next((dev for dev in DEVICE_FILTERS if dev.lower() in question.lower()), None)
    return os_hint, device_hint


def generation_answer_via_assistant(question):
    os_hint, device_hint = extract_filters(question)
    instructions = []
    if os_hint:
        instructions.append(f"Инструкция должна быть только для {os_hint}. Не упоминай другие операционные системы.")
    if device_hint:
        instructions.append(
            f"Инструкция должна относиться к {device_hint}. Игнорируй сервер, если это рабочая станция, и наоборот.")
    instruction_filter = " ".join(instructions)

    previous_questions = thread.read()
    prompt = f"Контекст предыдущего обсуждения: {previous_questions}\n\nТекущий вопрос: {question}. {instruction_filter}" if previous_questions else f"Текущий вопрос: {question}. {instruction_filter}"

    thread.write(prompt)
    run = assistant.run(thread)
    result = run.wait()
    return result.text if result.text else "Извините, не удалось найти информацию."


def generation_answer_via_gpt(question):
    model = ycloud.models.completions("yandexgpt").configure(temperature=0.5)
    prompt = f"Пожалуйста, предоставьте конкретный ответ на следующий вопрос:\nВопрос: {question}\nОтвет:"
    result = model.run(prompt)
    return result[0].text.strip() if result else "Извините, не удалось найти информацию."


def generate_clarifying_question(question):
    model = ycloud.models.completions("yandexgpt").configure(temperature=0.7)
    prompt = f"Ты технический помощник. Пользователь задал неясный вопрос:\n\"{question}\"\nСформулируй один уточняющий вопрос, чтобы лучше понять проблему:"
    result = model.run(prompt)
    return result[0].text.strip() if result else None


def ask_for_clarification(chat_id, question):
    for keyword, clarifications in CLARIFICATION_KEYWORDS.items():
        if keyword in question.lower():
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            question_text = clarifications[0]
            options = clarifications[1:]
            markup.add(*[types.KeyboardButton(text=opt) for opt in options])
            bot.send_message(chat_id, question_text, reply_markup=markup)
            user_context[chat_id] = {"pending": question, "status": "waiting_clarification"}
            return

    # Если нет подходящего ключа — используем GPT для уточнения
    clarifying = generate_clarifying_question(question)
    if clarifying:
        bot.send_message(chat_id, clarifying)
        user_context[chat_id] = {"pending": question, "status": "waiting_dynamic_clarification"}
    else:
        bot.send_message(chat_id, "Пожалуйста, уточните ваш вопрос.")


@bot.message_handler(commands=["start", "restart"])
def start_message(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🛠 Справка", "💬 Задать вопрос", "ℹ️ О боте", "🔄 Перезапуск (Reset)")
    markup.add("🆘 Поддержка")
    bot.send_message(message.chat.id,
                     "Привет! Я бот технической поддержки. Напишите ваш вопрос, и я постараюсь Вам помочь.",
                     reply_markup=markup)


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

    # Обработка ответа на уточняющий вопрос от GPT
    if isinstance(user_context.get(chat_id), dict):
        ctx = user_context[chat_id]
        if ctx.get("status") == "waiting_dynamic_clarification":
            full_question = f"{ctx['pending']}, уточнение: {user_question}"
            user_context[chat_id] = full_question
            bot.send_message(chat_id, "🔍 Выполняется поиск...")
            assistant_answer = generation_answer_via_assistant(full_question)
            if assistant_answer:
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("Ответ помог", callback_data=f"helpful_{message.message_id}"))
                markup.add(
                    types.InlineKeyboardButton("Ответ не помог", callback_data=f"not_helpful_{message.message_id}"))
                bot.send_message(chat_id,
                                 f"**Ваш вопрос:** {clean_markdown_output(full_question)}\n\n"
                                 f"**Ответ:**\n{escape_markdown(assistant_answer)}",
                                 parse_mode="MarkdownV2",
                                 reply_markup=markup)
            else:
                gpt_answer = generation_answer_via_gpt(full_question)
                bot.send_message(chat_id, gpt_answer)
            return

        if ctx.get("status") == "waiting_clarification":
            original_question = ctx["pending"]
            combined_question = f"{original_question}, уточнение: {user_question}"

            if user_question in FOLLOWUP_CLARIFICATIONS:
                followup = FOLLOWUP_CLARIFICATIONS[user_question]
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                question_text = followup[0]
                options = followup[1:]
                markup.add(*[types.KeyboardButton(text=opt) for opt in options])
                bot.send_message(chat_id, question_text, reply_markup=markup)
                user_context[chat_id] = {"pending": combined_question, "status": "waiting_clarification"}
                return

            user_context[chat_id] = combined_question
            bot.send_message(chat_id, "🔍 Выполняется поиск...")
            assistant_answer = generation_answer_via_assistant(combined_question)
            if assistant_answer:
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("Ответ помог", callback_data=f"helpful_{message.message_id}"))
                markup.add(
                    types.InlineKeyboardButton("Ответ не помог", callback_data=f"not_helpful_{message.message_id}"))
                bot.send_message(chat_id,
                                 f"**Ваш вопрос:** {clean_markdown_output(combined_question)}\n\n"
                                 f"**Ответ:**\n{escape_markdown(assistant_answer)}",
                                 parse_mode="MarkdownV2",
                                 reply_markup=markup)
            else:
                gpt_answer = generation_answer_via_gpt(combined_question)
                bot.send_message(chat_id, gpt_answer)
            return

    # Сначала проверим, требует ли вопрос уточнение
    if any(keyword in normalize_question(user_question) for keyword in CLARIFICATION_KEYWORDS):
        ask_for_clarification(chat_id, user_question)
        return

    if chat_id in user_context and user_context[chat_id]:
        last_question = user_context[chat_id]
        if user_question in SHORT_REPLIES:
            user_question = f"{last_question} → {user_question}"
        else:
            user_context[chat_id] = user_question
    else:
        user_context[chat_id] = user_question

    if not is_technical_question(normalize_question(user_question), user_context.get(chat_id), TECHNICAL_KEYWORDS):
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
    else:
        gpt_answer = generation_answer_via_gpt(user_question)
        bot.send_message(chat_id, gpt_answer)


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
        user_context[chat_id] = question
        bot.send_message(chat_id, "Пожалуйста, уточните вашу проблему, и я постараюсь помочь.")


def ping_telegram():
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
