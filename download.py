from contextlib import closing
import re
import time

import requests
from bs4 import BeautifulSoup
import pandas as pd
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait


def log_error(e):
    print(e)


def simple_get(url, cookies):
    headers = {
        'Host': 'menus.nypl.org',
        'Connection': 'keep-alive',
        'Cache-Control': 'max-age=0',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.97 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'en-US,en;q=0.9',
        'Cookie': cookies,
        'If-None-Match': '"7cceab85b82369f56e93bec759d9a879"'
    }

    proxies = {
        'http': 'http://194.226.34.132:5555',
        'https': 'http://194.226.34.132:5555'
    }

    try:
        with closing(requests.get(url, headers=headers, stream=True)) as resp:
            if is_good_response(resp):
                return resp.content
            else:
                return None

    except:
        log_error('Error during requests to: ...')
        return None


def is_good_response(resp):
    content_type = resp.headers['Content-Type'].lower()
    return (resp.status_code == 200
            and content_type is not None
            and content_type.find('html') > -1)


def get_cookies_with_selenium():
    with webdriver.Chrome(executable_path='/usr/bin/chromedriver') as driver:
        wait = WebDriverWait(driver, 10)
        driver.get('http://menus.nypl.org/menus/25602')
        time.sleep(5)
        cookies_list_raw = driver.get_cookies()

        cookies_list = []
        for cookie_raw in cookies_list_raw:
            cookies_list.append(cookie_raw['name'] + '=' + cookie_raw['value'])
        cookies = ';'.join(cookies_list)

        return cookies


if __name__ == '__main__':
    cookies = get_cookies_with_selenium()

    response = simple_get('http://menus.nypl.org/menus/25602', cookies)
    response2 = simple_get('http://menus.nypl.org/menus/29285', cookies)

    html = BeautifulSoup(response, 'html.parser')
    metadata = html.select('.content  .metadata  .wrap p')
    dishes = html.select('.content  .dishes tr')

    df = pd.DataFrame()
    sr = pd.Series()

    for p in metadata:
        values = list(filter(None, re.split('\n|\t', p.text)))

        if len(values) == 2:
            sr.at[values[0].lower()] = values[1]
            print(values[0] + ': ' + values[1])

    for tr in dishes:
        name = tr.select('.name')[0].text
        page = tr.select('.page a')[0]['href'] if tr.select('.page a') else None
        price = tr.select('.price')[0].text

        if name and page and price:
            sr.at['dish'] = name
            sr.at['page'] = page
            sr.at['price'] = price
            df = df.append(sr, ignore_index=True)
            print(name, page, price)

    df.to_csv('output.csv', index=False)
    print('done.')
