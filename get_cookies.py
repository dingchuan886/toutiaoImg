import json

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time


def main():
    browser = webdriver.Chrome()
    browser.get("https://www.taobao.com")
    time.sleep(30)
    with open('cookie.txt', 'w') as f:
        f.write(json.dumps(browser.get_cookies()))

    browser.close()


if __name__ == '__main__':
    main()
