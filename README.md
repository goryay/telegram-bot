# telegram-bot
**Telegram bot for technical support**

# Description
**The idea behind the bot is to help solve some problems in a short period of time. If the bot can not cope with it, then a specialist is involved in the problem. The bot uses AI for training and working with documentation to be able to solve and find a solution to the problem.**

### This is a bot designed to solve problems such as:
**1.** *Technical problems;*

**2.** *To solve customization problems;*

## Dependencies used `requirements.txt`
```
telebot==4.26.0
requests==2.32.3
python-dotenv==1.0.1
yandex-cloud-ml-sdk==0.2.0
yandexcloud==0.326.0
```

## Setting dependencies
```shell
pip install -r requirements.txt
```

## The yandex-sdk library was also used to utilize YandexGPT. You can read more [here](https://github.com/yandex-cloud/yandex-cloud-ml-sdk).
```commandline
pip install yandex-cloud-ml-sdk
```

*To install all plugins at once*
```commandline
pip install python-dotenv telebot python-docx yandex-cloud-ml-sdk
```

## Starting the bot
```shell
python bot.py
```
###
**Python-dotenv reads key-value pairs from the `.env` file and can set them as environment variables. In this file, we create variables where we will store the keys from TG and Yandex.**
```.env
TELEGRAM_BOT_TOKEN=YOUR_TOKEN
YANDEX_CLOUD_FOLDER_ID=YOUR_FOLDER_ID
YANDEX_CLOUD_OAUTH_TOKEN=YOUR_TOKEN
```
