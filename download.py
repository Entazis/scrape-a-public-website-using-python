from contextlib import closing
import re

import requests
from bs4 import BeautifulSoup
import pandas as pd


def log_error(e):
    print(e)


def simple_get(url):
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'hu,en-US;q=0.7,en;q=0.3',
        'Cache-Control': 'max-age=0',
        'Connection': 'keep-alive',
        'Cookie': '_menus_session=BAh7B0kiD3Nlc3Npb25faWQGOgZFVEkiJWI5YmI0OWFkMjNmOWY2NmVkMDI3NWM2OTg3OWMzYzFkBjsAVEkiEF9jc3JmX3Rva2VuBjsARkkiMWdhUFpSUVRzMXdEREZhL0kwbk1GWlZhYnJ3YkJlZjVnNmpXSlhxUnJzVWc9BjsARg%3D%3D--aff80691c3ea5119918bc4e9899181a8e89e0775; visid_incap_23338=ssEKo17PSsKuUVKNjqrbG41Z0l0AAAAAQUIPAAAAAAAqLB9Rq19FD5NfizkGKbok; nlbi_23338=MJ42ayLFdR7k4hLGnkdPnAAAAAD8d4QJj5D1LNMab4w29ihX; incap_ses_1077_23338=0tdnHj24qT4jQ+qaTUbyDqtk0l0AAAAAr+R5DLISP3H7NxsyQA5jjw==; __utma=121363604.619817368.1574066576.1574066576.1574069420.2; __utmc=121363604; __utmz=121363604.1574066576.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none); __utmb=121363604.1.10.1574069420; __utmt=1',
        'Host': 'menus.nypl.org',
        'If-None-Match': '"343e975a1dcbf254a0329017a2a31c1a"',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:70.0) Gecko/20100101 Firefox/70.0',
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


if __name__ == '__main__':
    response = simple_get('http://menus.nypl.org/menus/25602')
    html = BeautifulSoup(response, 'html.parser')
    metadata = html.select('.content  .metadata  .wrap p')
    dishes = html.select('.content  .dishes tr')

    df = pd.DataFrame()
    sr = pd.Series()

    for p in metadata:
        values = list(filter(None, re.split('\n|\t', p.text)))

        if len(values) == 2:
            sr.at[values[0]] = values[1]
            print(values[0] + ': ' + values[1])

    print('done.')
