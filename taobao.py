import json

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pyquery import PyQuery as pq
import re
import pymongo
from config import *

options = Options()
options.add_argument('--headless')
options.add_argument('–disable-images')
# options.add_experimental_option('excludeSwitches', ['enable-automation'])
options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

browser = webdriver.Chrome(executable_path='chromedriver', options=options)
wait = WebDriverWait(browser, 15)
client = pymongo.MongoClient(host=MONGO_URL, port=MONGO_PORT, connect=False)
db = client[MONGO_DB]


def search():
    browser.get("https://www.taobao.com")
    set_cookie()
    # 等待，直到页面加载完毕，超过10秒抛出异常
    try:
        input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#q')))
        submit = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '#J_TSearchForm > div.search-button > button')))
        input.send_keys('美食')
        submit.click()
        total = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > div.total')))
        return total.text
    except TimeoutException:
        search()


def set_cookie():
    with open('cookie.txt', 'r') as f:
        cookies_list = json.load(f)
        for cookie in cookies_list:
            if 'expiry' in cookie:
                del cookie['expiry']
            browser.add_cookie(cookie)


def next_page(page_num):
    try:
        input = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > div.form > input')))
        submit = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > div.form > span.btn.J_Submit')))
        input.clear()
        input.send_keys(page_num)
        submit.click()
        wait.until(EC.text_to_be_present_in_element(
            (By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > ul > li.item.active > span'), str(page_num)))
        get_products()
    except TimeoutException:
        next_page(page_num)


def get_products():
    wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, '#mainsrp-itemlist .items .item')))
    html = browser.page_source
    doc = pq(html)
    items = doc('#mainsrp-itemlist .items .item').items()
    for item in items:
        product = {
            'image': item.find('.pic img').attr('data-src'),
            'price': item.find('.price').text(),
            'deal-cnt': item.find('.deal-cnt').text()[:-3],
            'title': item.find('.title').text(),
            'shop': item.find('.shop').text(),
            'location': item.find('.location').text()
        }
        save_to_monge(product)


def save_to_monge(result):
    try:
        if db[MONGO_TABLE].insert(result):
            print("保存到mongo成功", result)
            return True
    except Exception as e:
        print("保存mongo出错", repr(e))
        pass
    return False


def main():
    total = search()
    total = int(re.compile('(\d+)').search(total).group(1))
    for i in range(2, total + 1):
        next_page(i)


if __name__ == '__main__':
    main()
