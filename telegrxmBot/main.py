import os
import re
import logging
import html
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
        except tweepy.TwitterServerError as tError:
            await bot.send_message(chat_id=MANAGER_CHAT_ID, text="Twitter error: " + str(tError))
        except Exception as error:
            await bot.send_message(chat_id=MANAGER_CHAT_ID, text="Error: " + str(error))
    else:
        if update.effective_message.effective_attachment is None:
            await bot.send_message(chat_id=MANAGER_CHAT_ID, text="username: " + update.effective_chat.username + ", id: " + str(update.effective_chat.id) + "\n\n" + update.effective_message.text_html)
        else:
            await bot.send_message(chat_id=MANAGER_CHAT_ID, text="username: " + update.effective_chat.username + ", id: " + str(update.effective_chat.id) + "\n\n" + update.effective_message.caption_html)

# Non-bot functions related
async def publish_in_twitter(message: Message) -> None:
    if message.effective_attachment is None:
        formatted_text = format_text(message.text_html)
        if len(formatted_text) <= 280:
            twitter_client.create_tweet(text=formatted_text)
            await bot.send_message(chat_id=INFO_CHAT_ID, text="Tweet published successfully")
        else:
            await bot.send_message(chat_id=INFO_CHAT_ID, text="This tweet is too long, cannot be posted. Max: 280")
    else:
        formatted_text = format_text(message.caption_html)
        if len(formatted_text) <= 280:
            if type(message.effective_attachment) is tuple:
                new_file = await message.effective_attachment[-1].get_file()
                file = await new_file.download_to_drive()
                media_id = media_client.media_upload(file).media_id_string
                twitter_client.create_tweet(text=formatted_text, media_ids=[media_id])
                remove_uploaded_files()
                await bot.send_message(chat_id=INFO_CHAT_ID, text="Tweet published successfully")
            else:
                await bot.send_message(chat_id=INFO_CHAT_ID, text="Attachment not allowed")
        else:
            await bot.send_message(chat_id=INFO_CHAT_ID, text="This tweet is too long, cannot be posted. Max: 280")

def init_twitter():
    oauthV1 = tweepy.OAuth1UserHandler(consumer_key=API_KEY, consumer_secret=API_KEY_SECRET, access_token=ACCESS_TOKEN, access_token_secret=ACCESS_TOKEN_SECRET)
    client_v1 = tweepy.API(oauthV1, wait_on_rate_limit=True)
    client_v2 = tweepy.Client(bearer_token=BEARER_TOKEN, consumer_key=API_KEY, consumer_secret=API_KEY_SECRET, access_token=ACCESS_TOKEN, access_token_secret=ACCESS_TOKEN_SECRET, wait_on_rate_limit=True)
    return client_v1, client_v2

def format_text(text: str):
    unescaped_text = html.unescape(text)
    pattern = r'<(?!/?(a|A)\b)[^>]*>'
    return extract_href_from_a(re.sub(pattern, '', unescaped_text))

def extract_href_from_a(text: str):
    pattern = r'<a\s+href="([^"]*)"[^>]*>(.*?)<\/a>'
    def replace_tag(match):
        href = match.group(1)
        content = match.group(2)
        return f'{content} ({href})'

    return re.sub(pattern, replace_tag, text)

def remove_uploaded_files():
    dir_name = "./"
    fileNames = os.listdir(dir_name)

    for file in fileNames:
        if file.endswith((".jpg", ".mp4")):
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