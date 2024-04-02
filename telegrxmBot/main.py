import os
import re
import logging
import tweepy

from dotenv import load_dotenv
from telegram import Update, Message
from telegram.ext import Application, ContextTypes, MessageHandler, filters

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_KEY = os.environ.get("API_KEY")
API_KEY_SECRET = os.environ.get("API_KEY_SECRET")
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.environ.get("ACCESS_TOKEN_SECRET")
BEARER_TOKEN = os.environ.get("BEARER_TOKEN")
MANAGER_CHAT_ID = os.environ.get("MANAGER_CHAT_ID")
INFO_CHAT_ID = os.environ.get("INFO_CHAT_ID")
PUBLISH_CHAT_ID = os.environ.get("PUBLISH_CHAT_ID")

twitter_client = None
media_client = None
bot = None

# Bot function handlers
async def echo_message(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    global twitter_client
    global media_client
    if update.effective_chat.id == int(PUBLISH_CHAT_ID):
        if twitter_client is None or media_client is None:
            media_client, twitter_client = init_twitter()
        try:
            await publish_in_twitter(update.effective_message)
        except tweepy.TwitterServerError as e:
            await bot.send_message(chat_id=INFO_CHAT_ID, text="Error: " + e)
        except Exception as Argument:
            logger.error("Error: " + Argument)
    else:
        if update.effective_message.effective_attachment is None:
            await bot.send_message(chat_id=MANAGER_CHAT_ID, text="username: " + update.effective_chat.username + ", id: " + str(update.effective_chat.id) + "\n\n" + update.effective_message.text_html)
        else:
            await bot.send_message(chat_id=MANAGER_CHAT_ID, text="username: " + update.effective_chat.username + ", id: " + str(update.effective_chat.id) + "\n\n" + update.effective_message.caption_html)

# Non-bot functions related
async def publish_in_twitter(message: Message) -> None:
    if message.effective_attachment is None:
        new_text = removed_html_tags(message.text_html)
        logger.info(len(new_text))
        if len(new_text) <= 280:
            twitter_client.create_tweet(text=new_text)
            await bot.send_message(chat_id=INFO_CHAT_ID, text="Tweet published successfully")
        else:
            await bot.send_message(chat_id=INFO_CHAT_ID, text="This tweet is too long, cannot be posted")
    else:
        new_file = await message.effective_attachment[-1].get_file()
        file = await new_file.download_to_drive()
        media_id = media_client.media_upload(file).media_id
        new_text = removed_html_tags(message.caption_html)
        logger.info(len(new_text))
        if len(new_text) <= 280:
            twitter_client.create_tweet(text=new_text, media_ids=[media_id])
            remove_jpgs()
            await bot.send_message(chat_id=INFO_CHAT_ID, text="Tweet published successfully")
        else:
            await bot.send_message(chat_id=INFO_CHAT_ID, text="This tweet is too long, cannot be posted")

def init_twitter():
    oauthV1 = tweepy.OAuth1UserHandler(consumer_key=API_KEY, consumer_secret=API_KEY_SECRET, access_token=ACCESS_TOKEN, access_token_secret=ACCESS_TOKEN_SECRET)
    client_v1 = tweepy.API(oauthV1)
    client_v2 = tweepy.Client(bearer_token=BEARER_TOKEN, consumer_key=API_KEY, consumer_secret=API_KEY_SECRET, access_token=ACCESS_TOKEN, access_token_secret=ACCESS_TOKEN_SECRET)
    return client_v1, client_v2

def removed_html_tags(text: str):
    clean = re.compile('<[^aA](.*?)>')
    return re.sub(clean, '', text)

def remove_jpgs():
    dir_name = "./"
    fileNames = os.listdir(dir_name)

    for file in fileNames:
        if file.endswith(".jpg"):
            os.remove(os.path.join(dir_name, file))

def main() -> None:
    """Start the bot."""
    # Bot token
    global bot
    application = Application.builder().token(BOT_TOKEN).build()
    bot = application.bot

    # Commands
    # application.add_handler(CommandHandler("example", example))

    # On every message avoiding commands
    application.add_handler(MessageHandler((filters.TEXT | filters.ATTACHMENT) & ~filters.COMMAND, echo_message))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES, poll_interval=5)

if __name__ == "__main__":
    main()