#!/usr/bin/env python
# -*- coding: utf-8 -*-

# @Author  : wzdnzd
# @Time    : 2018-04-25

import re
import warnings
import urllib
import urllib.request
import urllib.parse
import base64
import multiprocessing
import os
import json

warnings.filterwarnings('ignore')

HEADER = {
    "user-agent":
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36 Edg/91.0.864.54",
    "accept": "application/json, text/javascript, */*; q=0.01",
    "accept-language": "zh-CN,zh;q=0.9",
    "dnt": "1",
    "Connection": "keep-alive",
    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
    "x-requested-with": "XMLHttpRequest"
}

RETRY_NUM = 5

PATH = os.path.abspath(os.path.dirname(__file__))


def extract_domain(url):
    if not url:
        return ""

    start = url.find("//")
    if start == -1:
        start = -2

    end = url.find("/", start + 2)
    if end == -1:
        end = len(url) - 1

    return url[start + 2:end]


def login(url, params, headers, retry):
    try:
        data = urllib.parse.urlencode(params).encode(encoding='UTF8')

        request = urllib.request.Request(url,
                                         data=data,
                                         headers=headers,
                                         method='POST')

        response = urllib.request.urlopen(request)
        print(response.read().decode('unicode_escape'))

        if response.getcode() == 200:
            return response.getheader('Set-Cookie')

    except Exception as e:
        print(str(e))
        retry -= 1

        if retry > 0:
            login(url, params, headers, retry)

        print("[LoginError] URL: {}".format(extract_domain(url)))
        return ''


def checkin(url, headers, retry):
    try:
        request = urllib.request.Request(url, headers=headers, method='POST')

        response = urllib.request.urlopen(request)
        data = response.read().decode('unicode_escape')
        print("[CheckInFinished] URL: {}\t\tResult:{}".format(
            extract_domain(url), data))

    except Exception as e:
        print(str(e))
        retry -= 1

        if retry > 0:
            checkin(url, headers, retry)

        print("[CheckInError] URL: {}".format(extract_domain(url)))


def get_cookie(text):
    regex = "(__cfduid|uid|email|key|ip|expire_in)=(.+?);"
    if not text:
        return ''

    content = re.findall(regex, text)
    cookie = ';'.join(['='.join(x) for x in content]).strip()

    return cookie


def config_load(filename):
    if not os.path.exists(filename) or os.path.isdir(filename):
        return

    config = open(filename, 'r').read()
    return json.loads(config)


def flow(domain, params, headers):
    domain = base64.b64decode(domain).decode("utf8")
    print('start to checkin, domain: {}'.format(domain))

    domain = domain.strip()
    regex = "(?i)^(https?:\\/\\/)?(www.)?([^\\/]+\\.[^.]*$)"
    flag = re.search(regex, domain)

    if not flag:
        return False

    login_url = domain + base64.b64decode(
        params.get("login", "L2F1dGgvbG9naW4=")).decode("utf8")
    checkin_url = domain + base64.b64decode(
        params.get("checkin", "L3VzZXIvY2hlY2tpbg==")).decode("utf8")
    headers["origin"] = domain
    headers["referer"] = login_url

    user_info = {
        "email": base64.b64decode(params['email']),
        "passwd": base64.b64decode(params['passwd'])
    }

    text = login(login_url, user_info, headers, RETRY_NUM)
    if not text:
        return False

    cookie = get_cookie(text)
    if len(cookie) <= 0:
        return False

    headers["referer"] = domain + "/user"
    headers["cookie"] = cookie

    checkin(checkin_url, headers, RETRY_NUM)


def wrapper(args):
    flow(args["domain"], args["param"], HEADER)


def main():
    config = config_load(os.path.join(PATH, 'config.json'))
    if "retry" in config and config["retry"] > 0:
        RETRY_NUM = int(config["retry"])

    params = config["domains"]
    for args in params:
        wrapper(args)

    # cpu_count = multiprocessing.cpu_count()
    # num = len(params) if len(params) <= cpu_count else cpu_count

    # pool = multiprocessing.Pool(num)
    # pool.map(wrapper, params)
    # pool.close()


if __name__ == '__main__':
    main()
