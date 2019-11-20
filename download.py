import re
import time
from datetime import datetime
from contextlib import closing

import requests
from bs4 import BeautifulSoup
import pandas as pd
from selenium import webdriver


def log_error(e):
    print(e)


def get_content_from_url_using_cookies(url, cookies):
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


def get_cookies_and_urls_with_selenium_from(decade_url):
    with webdriver.Chrome(executable_path='/usr/bin/chromedriver') as driver:
        driver.get(decade_url)
        time.sleep(3)
        cookies_list_raw = driver.get_cookies()
        cookies_list = []
        for cookie_raw in cookies_list_raw:
            cookies_list.append(cookie_raw['name'] + '=' + cookie_raw['value'])

        length_of_page = driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
        match = False
        while not match:
            last_count = length_of_page
            time.sleep(3)
            length_of_page = driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
            if last_count == length_of_page:
                match = True

        html = BeautifulSoup(driver.page_source, 'html.parser')
        hrefs = html.select('a.thumbportrait')

        urls = []
        for href in hrefs:
            urls.append(href['href'])

        return ';'.join(cookies_list), urls


def parse_response(response):
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

    return df


if __name__ == '__main__':
    output_folder_input = 'data'
    start_date_input = '18530220'
    end_date_input = '18700510'
    # /data/local/yyyy/MM/dd/HHmmss/output.csv (when the script ran)

    start_year = datetime.strptime(start_date_input, '%Y%m%d').year
    end_year = datetime.strptime(end_date_input, '%Y%m%d').year
    now = datetime.now()
    folder_year = now.year
    folder_month = now.month
    folder_day = now.day

    # 1873 contains menus from 1873 to 1882
    pages_to_get_urls_from = ['http://menus.nypl.org/menus/decade/' + str(start_year)]
    decade_year = start_year + 10
    while decade_year < end_year:
        pages_to_get_urls_from.append('http://menus.nypl.org/menus/decade/' + str(decade_year))
        decade_year = decade_year + 10

    cookies = []
    urls = []
    for page in pages_to_get_urls_from:
        cookies, urls = get_cookies_and_urls_with_selenium_from(page)

    df = pd.DataFrame()
    for url in urls:
        df = df.append( parse_response(get_content_from_url_using_cookies(url, cookies)))

    df.to_csv('output.csv', index=False)
    print('done.')
