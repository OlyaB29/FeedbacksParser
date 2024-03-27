import aiohttp
import asyncio
import threading
from openpyxl import load_workbook
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
from dateutil.parser import parse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from tg_feedbacks_sender import send_tg_message
chrome_options = Options()
# chrome_options.add_argument("--headless=new")
driver = webdriver.Chrome(options=chrome_options)


def _start_background_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()


_LOOP = asyncio.new_event_loop()
_LOOP_THREAD = threading.Thread(
    target=_start_background_loop, args=(_LOOP,), daemon=True
)
_LOOP_THREAD.start()


def get_content(url):
    # Получаем страницу
    driver.get(url)
    try:
        # Ждем пока не появится на странице тэг с id app
        element = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "apppp")))
    finally:
        # Возвращаем текст страницы
        return driver.page_source


# Отдельным запросом получаем всю информацию об отзывах
async def get_feedbacks_info(imtId):
    fb_url = "https://feedbacks1.wb.ru/feedbacks/v1/{}".format(imtId)
    async with aiohttp.ClientSession() as session:
        async with session.get(fb_url) as resp:
            fb_resp = await resp.json()
            current_valuation = fb_resp["valuation"]
            feedbacks = fb_resp["feedbacks"]
    return current_valuation, feedbacks


# Отправка в группу ТГ всех отобранных негативных отзывов по данному товару
async def send(product_title, SKU, current_valuation, last_negative_feedbacks):
    for fb in last_negative_feedbacks:
        # Формируем сообщение и отправляем с помощью бота в группу Телеграмм
        msg = f"<b>Негативный отзыв</b>\n<i>Название товара: </i>{product_title}\n" + \
              f"<i>SKU товара: </i>{SKU}\n<i>Оценка: </i>{fb['productValuation']}\n<i>Текст отзыва: </i>{fb['text']}\n" + \
              f"<i>Текущий рейтинг товара: </i>{current_valuation}"
        await send_tg_message(msg)


# Получаем информацию по артикулу
def get_article_info(SKU, last_parsing_date):
    url = "https://www.wildberries.ru/catalog/{}/detail.aspx".format(SKU)
    content = get_content(url)
    html = BeautifulSoup(content, 'html.parser')
    product_title = html.find('h1', class_='product-page__title').text.strip()
    fb_link = html.find('a', class_='product-review j-wba-card-item')['href']
    imtId = fb_link.split('=')[1]

    current_valuation, feedbacks = asyncio.run(get_feedbacks_info(imtId))
    # Отбираем только негативные отзывы, созданные(обновленные) с момента последнего парсинга
    last_negative_feedbacks = list(filter(lambda fb: parse(fb["updatedDate"])>last_parsing_date and fb["productValuation"]<=4, feedbacks))
    # Запускаем отправку отзывов
    asyncio.run_coroutine_threadsafe(send(product_title, SKU, current_valuation, last_negative_feedbacks), _LOOP).result()


def run_parsing():
    # В Excel-файле хранятся SKU товаров и дата последнего парсинга
    wb = load_workbook("./data.xlsx")
    last_parsing_date = parse(wb["Sheet1"]["B1"].value)
    for cell in wb.active['A'][:2]:
        SKU = str(cell.value)
        get_article_info(SKU, last_parsing_date)
    # Записываем новую дату
    wb["Sheet1"]["B1"] = (datetime.now(timezone(timedelta(hours=3), name='МСК'))).strftime('%Y-%m-%dT%H:%M:%S%z')
    wb.save("./data.xlsx")
    wb.close()



