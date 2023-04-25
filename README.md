# Python-Telegram-Broadcast-Bot

## Objective
This repo is created to share real code example of many Telegram API
which is related to broadcast. 

## Prerequisite
1. Get a Bot Token from BotFather, may refer to [site](https://help.zoho.com/portal/en/kb/desk/support-channels/instant-messaging/telegram/articles/telegram-integration-with-zoho-desk#Telegram_Integration)

## Reference
Any user of this repo should always refer to [official-site](https://docs.python-telegram-bot.org/en/stable/#telegram-api-support) for the most accurate information. At the point of writing, I refer to [v20.1](https://docs.python-telegram-bot.org/en/v20.1/). 

## Test The Code
### Environment
\
OS: Ubuntu 22.04\
Python: Python 3.10.6\
PS: I suppose it will also work on Windows 11, but I never been able to try them out.

### Commands
\
Copy and run command below.
```
git clone git@github.com:JonahTzuChi/Python-Telegram-Broadcast-Bot.git
```
```
cd Python-Telegram-Broadcast-Bot
```
```
pip3 install -r requirements.txt
```
```
python3 ./bot/bot.py
```

### Try Different API
\
Go to ./bot/bot.py and uncomment section you would like to run. 

# Remarks
1. timeout exception, just run the code again
2. `asyncio` is very important, async/await related code won't run without `asyncio.run(main())`