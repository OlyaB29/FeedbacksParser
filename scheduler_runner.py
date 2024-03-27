import schedule
import time
from config import PARSE_EVERY_HOURS
from datetime import datetime, timedelta, timezone
from fb_parser import run_parsing


def run():
    print(f'Парсинг отзывов начался: {datetime.now(timezone(timedelta(hours=3), name="МСК"))}')
    run_parsing()


schedule.every(PARSE_EVERY_HOURS).hours.do(run)

while True:
    schedule.run_pending()
    time.sleep(1)
