import string
from config import OS_FILTERS, DEVICE_FILTERS
from telebot import types

def normalize_question(question):
    """Удаляет пунктуацию и приводит текст к нижнему регистру."""
    return question.translate(str.maketrans("", "", string.punctuation)).lower()

def is_technical_question(question, last_question=None, technical_keywords=None):
    """Определяет, является ли вопрос техническим на основе ключевых слов."""
    normalized_question = normalize_question(question)

    for keyword in technical_keywords:
        if keyword.lower() in normalized_question or any(
                kw in normalized_question for kw in keyword.lower().split()
        ):
            print(f"[LOG] Вопрос '{question}' классифицирован как ТЕХНИЧЕСКИЙ ✅ (ключевое слово: {keyword})")
            return True

    if last_question:
        normalized_last_question = normalize_question(last_question)
        common_words = set(normalized_question.split()) & set(normalized_last_question.split())
        similarity = len(common_words) / max(len(normalized_question.split()), 1)

        if similarity > 0.5:
            print(f"[LOG] '{question}' воспринимается как уточнение '{last_question}', считаем его техническим ✅")
            return True

    print(f"[LOG] Вопрос '{question}' НЕ является техническим ❌")
    return False

def clean_markdown_output(text):
    """Экранирует специальные символы Markdown в тексте."""
    escape_chars = r"_*[]()~`>#+-=|{}.!\\-"
    return "".join(f"\\{char}" if char in escape_chars else char for char in text).strip()

def escape_markdown(text):
    """Экранирует специальные символы Markdown в тексте."""
    escape_chars = r"_*[]()~`>#+-=|{}.!\\-"
    return "".join(f"\\{char}" if char in escape_chars else char for char in text)

def log_feedback(question, answer, feedback, statistics_file):
    """Логирует отзыв пользователя в файл."""
    with open(statistics_file, "a", encoding="utf-8") as file:
        file.write(f"Вопрос: {question}\nОтвет: {answer}\nОтзыв: {feedback}\n{'-' * 40}\n")

def safe_send_message(bot, chat_id, text):
    """Безопасная отправка сообщения пользователю с обработкой потенциальных ошибок."""
    try:
        bot.send_message(chat_id, text, parse_mode="MarkdownV2")
    except Exception as e:
        print(f"⚠️ Ошибка при отправке сообщения: {e}")
        bot.send_message(chat_id, "⚠️ Ошибка при обработке сообщения. Попробуйте ещё раз.")

def extract_filters(question):
    """Извлечение подсказок о типе ОС и устройства из вопроса."""
    os_hint = next((os for os in OS_FILTERS if os.lower() in question.lower()), None)
    device_hint = next((dev for dev in DEVICE_FILTERS if dev.lower() in question.lower()), None)
    return os_hint, device_hint

def generate_instructions(os_hint, device_hint):
    """Генерация инструкций на основе извлеченных фильтров."""
    instructions = []
    if os_hint:
        instructions.append(f"Инструкция должна быть только для {os_hint}. Не упоминай другие операционные системы.")
    if device_hint:
        instructions.append(
            f"Инструкция должна относиться к {device_hint}. Игнорируй сервер, если это рабочая станция, и наоборот."
        )
    return " ".join(instructions)
