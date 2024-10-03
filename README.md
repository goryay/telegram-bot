# telegram-bot
**Telegram bot for technical support**

# Description
**The idea behind the bot is to help solve some problems in a short period of time. If the bot can not cope with it, then a specialist is involved in the problem. The bot uses AI for training and working with documentation to be able to solve and find a solution to the problem.**

### This is a bot designed to solve problems such as:
**1.** *Technical problems;*

**2.** *To solve customization problems;*

## Dependencies used *requirements.txt*
```
python-telegram-bot==13.15
requests
python-dotenv
urllib3==1.26.5
certifi
six
```

## Setting dependencies
```shell
pip install -r requirements.txt
```

## Starting the bot
```shell
python bot.py
```
###
**Python-dotenv reads key-value pairs from the `.env` file and can set them as environment variables. In this file, we create variables where we will store the keys from TG and Yandex.**
```.env
TELEGRAM_BOT_TOKEN=YOUR_TOKEN
YANDEX_CLOUD_OAUTH_TOKEN=YOUR_TOKEN
```
