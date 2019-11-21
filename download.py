import argparse
import calendar
import dateutil.parser
import logging
import os
import re
import time
from contextlib import closing
from datetime import datetime

from bs4 import BeautifulSoup
import pandas as pd
import requests
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.common.by import By


def get_content_from_url_using_cookies(url: str, cookies: str) -> object:
    """Simple get request using custom cookies.

    Parameters
    ----------
    url
        URL to get from.
    cookies
        Cookies defined in string.

    Returns
    -------
    object
        Content of the response of the request or None.
    """
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

    print('Scraping URL: ', url)

    try:
        with closing(requests.get(url, headers=headers, stream=True)) as resp:
            if is_good_response(resp):
                return resp.content
            else:
                return None

    except Exception as e:
        logging.error('During requests to: ' + url + '\n ' + str(e))
        return None


def is_good_response(resp: object) -> bool:
    """Simple response validity check.

    Checks the status code, content type and html tag.

    Parameters
    ----------
    resp
        Response object to check

    Returns
    -------
    bool
        True if the response is valid.
    """
    try:
        content_type = resp.headers['Content-Type'].lower()
        return (resp.status_code == 200
                and content_type is not None
                and content_type.find('html') > -1)

    except Exception as e:
        logging.error(str(e))
        return False


def get_urls_with_selenium_from(url: str) -> list:
    """Collect URLS from a page.

    Scrolls down the page till it can, then collects the urls defined in <a class="thumbportrait" href="...">s.

    Parameters
    ----------
    url
        URL of the page with urls.

    Returns
    -------
    list
        List of the collected urls.
    """
    try:
        with webdriver.Chrome(executable_path='/usr/bin/chromedriver') as driver:
            driver.get(url)
            results = WebDriverWait(driver, 10).until(ec.presence_of_element_located((By.ID, 'results')))

            length_of_page = driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
            match = False
            while not match:
                last_count = length_of_page
                loadingmore = WebDriverWait(driver, 10).until(ec.invisibility_of_element_located((By.ID, 'loadingmore')))
                length_of_page = driver.execute_script(
                    "window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
                if last_count == length_of_page:
                    match = True

            html = BeautifulSoup(driver.page_source, 'html.parser')
            hrefs = html.select('a.thumbportrait')

            urls = []
            for href in hrefs:
                urls.append(href['href'])

            return urls

    except Exception as e:
        logging.error('Getting urls with selenium from: ' + url + '\n' + str(e))
        return []


def get_cookies_with_selenium_from(url: str) -> str:
    """Get cookies from a page.

    Navigates to the side and saves the cookies.

    Parameters
    ----------
    url
        URL of the page to get cookies from.

    Returns
    -------
    str
        Cookies got from the page.
    """
    try:
        with webdriver.Chrome(executable_path='/usr/bin/chromedriver') as driver:
            driver.get(url)
            time.sleep(3)
            cookies_list_raw = driver.get_cookies()
            cookies_list = []
            for cookie_raw in cookies_list_raw:
                cookies_list.append(cookie_raw['name'] + '=' + cookie_raw['value'])
            return ';'.join(cookies_list)

    except Exception as e:
        logging.error('Getting cookies with selenium from: ' + url + '\n' + str(e))
        return ''


def parse_response(response: object) -> pd.DataFrame:
    """Parses the response got from request.

    identifies the page elements and arrange them into a dataframe.

    Parameters
    ----------
    response
        Response from a request

    Returns
    -------
    object
        Dataframe with the parsed date.
    """
    try:
        html = BeautifulSoup(response, 'html.parser')
        metadata = html.select('.content  .metadata  .wrap p')
        dishes = html.select('.content  .dishes tr')

        df = pd.DataFrame()
        sr = pd.Series()

        for p in metadata:
            values = list(filter(None, re.split('\n|\t', p.text)))

            if len(values) == 2:
                if values[0].lower() == 'date':
                    date = dateutil.parser.parse(values[1])
                    sr.at['date'] = date.strftime('%Y%m%d')
                    pass
                else:
                    sr.at[values[0].lower().replace(' ', '_')] = values[1]
            elif len(values) == 1 and p.select('strong'):
                sr.at['n_dishes'] = p.select('strong')[0].text
                pass

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

    except Exception as e:
        logging.error('Parsing response: ' + str(e))
        return pd.DataFrame()


def parse_arguments() -> object:
    """Parses the input arguments from command line.

    Returns
    -------
    object
        Object with the arguments.
    """
    try:
        ap = argparse.ArgumentParser(prog='download',
                                     usage='%(prog)s [options] path',
                                     description='Scrape menus from menus.nypl.org.')
        ap.add_argument('--start_date',
                        action='store',
                        type=str,
                        help='from what time to scrape the menus',
                        required=True)
        ap.add_argument('--end_date',
                        action='store',
                        type=str,
                        help='till what time to scrape the menus',
                        required=True)
        ap.add_argument('output_folder',
                        action='store',
                        type=str,
                        help='the path to the destination folder',
                        default='./data')
        return ap.parse_args()

    except Exception as e:
        logging.error('Parsing arguments: ' + str(e))
        return None


def parse_date(date_string: str) -> object:
    """Creates a datetime object from a string.

    Parameters
    ----------
    date_string
        Date in string YYYYMMDD format.

    Returns
    -------
    object
        Datetime.
    """
    try:
        date = []
        if len(date_string) == 8:
            date = datetime.strptime(date_string, '%Y%m%d')
        elif len(date_string) == 6:
            date = datetime.strptime(date_string, '%Y%m')
            date = date.replace(day=calendar.monthrange(date.year, date.month)[1])
        elif len(date_string) == 4:
            date = datetime.strptime(date_string, '%Y')
        else:
            date = datetime(1853, 1, 1)

        if date.year < 1853:
            date = date.replace(year=1853)
        if date.year > datetime.now().year:
            date = date.replace(year=datetime.now().year)

        return date

    except Exception as e:
        logging.error('Parsing date: ' + str(e))
        return None


if __name__ == '__main__':

    args = parse_arguments()

    start_date = parse_date(args.start_date)
    end_date = parse_date(args.end_date)
    output_folder = args.output_folder

    now = datetime.now()
    output_path = os.path.join(output_folder,
                               str(now.year),
                               str('{:02d}'.format(now.month)),
                               str('{:02d}'.format(now.day)),
                               str('{:02d}{:02d}{:02d}'.format(now.hour, now.minute, now.second)))

    print('Scraping \nfrom: ' + str(start_date.strftime('%Y.%m.%d.')) + ' ')
    print('to: ' + str(end_date.strftime('%Y.%m.%d.')) + ' ')
    print('path: ' + output_path)

    pages_to_get_urls_from = ['http://menus.nypl.org/menus/decade/' + str(start_date.year)]
    decade_year = start_date.year + 10
    while decade_year <= end_date.year:
        pages_to_get_urls_from.append('http://menus.nypl.org/menus/decade/' + str(decade_year))
        decade_year = decade_year + 10

    menu_urls = []
    for page in pages_to_get_urls_from:
        menu_urls.append(get_urls_with_selenium_from(page))
    menu_urls = [item for sublist in menu_urls for item in sublist]
    cookies_from_last_page = get_cookies_with_selenium_from(menu_urls[len(menu_urls) - 1])

    output_df = pd.DataFrame()
    for menu_url in menu_urls:
        output_df = output_df.append(
            parse_response(
                get_content_from_url_using_cookies(menu_url, cookies_from_last_page)),
            sort=False)

    output_df_filtered = output_df[(output_df['date'] >= start_date.strftime('%Y%m%d')) &
                                   (output_df['date'] <= end_date.strftime('%Y%m%d'))]

    if not os.path.exists(output_path):
        os.makedirs(output_path)
    output_df_filtered.to_csv(os.path.join(output_path, 'output.csv'), index=False)

    print('done.')
