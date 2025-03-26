import os
from dotenv import load_dotenv
from yandex_cloud_ml_sdk import YCloudML

load_dotenv()

CHAT_ID = os.getenv("CHAT_ID")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
YANDEX_CLOUD_FOLDER_ID = os.getenv("YANDEX_CLOUD_FOLDER_ID")
YANDEX_CLOUD_OAUTH_TOKEN = os.getenv("YANDEX_CLOUD_OAUTH_TOKEN")

ycloud = YCloudML(folder_id=YANDEX_CLOUD_FOLDER_ID, auth=YANDEX_CLOUD_OAUTH_TOKEN)
file = ycloud.files.upload("lsa.docx", ttl_days=5, expiration_policy="static")
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
    "PXE-загрузка", "KVM", "LiveCD", "флешка", "флешку", "загрузочная флешка", "USB", "образ системы", "ISO",
    "запись образа", "lsa"
]

SHORT_REPLIES = ["не помогло", "что дальше?", "какие ещё варианты?", "это не работает",
                 "данные рекомендации не помогли", "Не помогло", "Что дальше?", "Какие ещё варианты?",
                 "Это не работает", "Данные рекомендации не помогли"]

STATISTICS_FILE = "feedback_statistics.txt"

CLARIFICATION_KEYWORDS = {
    "установка": ["ОС (Windows, Linux, Astra)?"],
    "не включается": ["Есть ли индикаторы? Пищит ли сервер?"],
    "синий экран": ["На каком этапе? Есть ли код ошибки?"],
    "RAID": ["Вы используете LSI, Intel или встроенный контроллер?"],
}
