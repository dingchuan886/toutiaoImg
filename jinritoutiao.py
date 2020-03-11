import json
import os
import re
import requests
import hashlib
from requests.exceptions import RequestException
import pymongo
from bs4 import BeautifulSoup
import html
from urllib.parse import urlencode
import ssl
import warnings
from config import *
from multiprocessing import Pool

client = pymongo.MongoClient(host=MONGO_URL, port=MONGO_PORT)
db = client[MONGO_DB]
warnings.filterwarnings('ignore')

headers = {
    'cookie': 'tt_webid=6802117486239401479; ttcid=4caaca002b7b4288b621fef8a6342b8528; SLARDAR_WEB_ID=33c1d7e8-c748-4c99-9857-57fd7935445f; WEATHER_CITY=%E5%8C%97%E4%BA%AC; tt_webid=6802117486239401479; csrftoken=2ead47779767254bf06dd2938b9b1f72; s_v_web_id=verify_k7mqpanj_LuZ7IWnV_yA6f_4zqO_B8DJ_JgZ5al9PXMJN; __tasessionId=sbwruri3x1583913645529; tt_scid=1IGqeQIIC4j-of4f8tTMS5RWA6vIKBr1A6vRedF5lsQtjUbdhBfRAvYPdURVbxLDbd0e',
    'referer': 'https://www.toutiao.com/search/?keyword=%E8%A1%97%E6%8B%8D',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.87 Safari/537.36',
    'x-requested-with': 'XMLHttpRequest',
    'Pragma': 'no-cache'
}


def get_page_index(offset, keyword):
    ssl._create_default_https_context = ssl._create_unverified_context
    data = {
        'aid': 24,
        'app_name': 'web_search',
        'offset': offset,
        'format': 'json',
        'keyword': keyword,
        'autoload': 'true',
        'count': 20,
        'en_qc': 1,
        'cur_tab': 1,
        'from': 'search_tab',
        'pd': 'synthesis',
        'timestamp': 1583849183622,
        '_signature': 'uIPpDAAgEBB-1FCBLbs84riCqBAAObyCGS4h-CW0BDHz.QVElW2wsFf17Vwg9vNH5hLi.AsdJ7VxAg1s0SigBPYirGZ.HFshItsPCFVDI1QLHHCxQeu8RSCBBWrVxtF8Gql'
    }
    url = "https://www.toutiao.com/api/search/content/?" + urlencode(data)
    try:
        response = requests.get(url, headers=headers, verify=False)
        if response.status_code == 200:
            return response.text
    except RequestException:
        print('请求索引页出错')
        return None
    return None


def parse_page_index(htmlStr):
    data = json.loads(htmlStr)
    if data and 'data' in data.keys() and data.get('data'):
        for img_list in data.get('data'):
            if img_list.get('article_url'):
                yield img_list.get('article_url')


def get_page_detail(url):
    ssl._create_default_https_context = ssl._create_unverified_context
    try:
        response = requests.get(url, headers=headers, verify=False)
        if response.status_code == 200:
            return response.text
    except RequestException:
        print('请求详情页出错')
        return None


def parse_page_detail(htmlStr, url):
    soup = BeautifulSoup(htmlStr, 'lxml')
    if soup.select('title'):
        title = soup.select('title')[0].get_text()
        pattern = re.compile('gallery: JSON.parse\("(.*?)"\)')
        result = re.search(pattern, htmlStr)
        if result:
            # 将json数据转换为python的字典对象
            data = json.loads(result.group(1).encode('ascii').decode('unicode_escape'))
            if data and not isinstance(data, str) and 'sub_images' in data.keys():
                sub_images = data.get('sub_images')
                images = [item.get('url') for item in sub_images]
                for image in images:
                    download_img(image)
                yield {
                    'title': title,
                    'url': url,
                    'images': images
                }
        else:
            imgPattern = re.compile("articleInfo: .*?content: (.*?)groupId", re.S)
            imgtext = re.search(imgPattern, htmlStr)
            decodeImg = imgtext.group(1).encode('utf-8').decode('unicode_escape')
            decodeImg = html.unescape(decodeImg)
            decodePattern = re.compile('<img src=\\\\"(.*?)\\\\"')
            imgs = re.findall(decodePattern, decodeImg)
            for image in imgs:
                download_img(image)
            yield {
                'title': title,
                'url': url,
                'images': imgs
            }


def save_to_mongo(result):
    try:
        if db[MONGO_TABLE].insert(result):
            print("存储到Mongo成功", result)
            return True
    except Exception:
        pass
    return False


def download_img(url):
    print("正在下载", url)
    ssl._create_default_https_context = ssl._create_unverified_context
    try:
        response = requests.get(url, headers=headers, verify=False)
        if response.status_code == 200:
            save_img_to_disk(response.content)
    except RequestException:
        print('请求图片出错')
        return None


def save_img_to_disk(content):
    file_name = '{0}/{1}.{2}'.format(os.getcwd() + '/img', hashlib.md5(content).hexdigest(), 'jpg')  # 路径、文件名、后缀
    if not os.path.exists(os.path.dirname(file_name)):
        os.mkdir(os.path.dirname(file_name))
    if not os.path.exists(file_name):
        with open(file_name, 'wb')as f:
            f.write(content)
            f.close()


def main(offset):
    #关键字搜索
    for url in parse_page_index(get_page_index(offset, '风景')):
        htmlStr = get_page_detail(url)
        if htmlStr:
            result = parse_page_detail(htmlStr, url)
            if result:
                save_to_mongo(result)


if __name__ == '__main__':
    pool = Pool()
    grades = [x * 20 for x in range(START, END)]
    pool.map(main, grades)
