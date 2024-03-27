from aiogram import Bot
import logging
from config import TOKEN, CHAT_ID

logger = logging.getLogger('tg_feedbacks_sender')
logger.setLevel(logging.INFO)

bot = Bot(token=TOKEN)


async def send_tg_message(message):
    await bot.send_message(CHAT_ID, message, parse_mode="html")