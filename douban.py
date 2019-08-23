import requests
from lxml import etree
import re
import json
import random
import time
import tqdm
import pandas as pd


headers = {
    "Host": "accounts.douban.com",
    "Origin": "https://accounts.douban.com",
    "Referer": "https://accounts.douban.com/login?source=group",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.139 Safari/537.36",
}


data = {
    "ck": "0Sg3",
    "source": "None",
    "redir": "https://www.douban.com",
    "form_email": "1553526263@qq.com",
    "form_password": "hou19910922",
    "login": "登录",
}


# from requests.auth import HTTPBasicAuth
# auth = HTTPBasicAuth('1553526263@qq.com', 'hou19910922')

post_url = "https://accounts.douban.com/login"

s = requests.Session()
s.post(post_url, headers=headers, data=data)

# url = 'https://www.douban.com/group/592830/discussion?start=0'
def GetPostList(url):
    res = s.get(url)
    x = etree.HTML(res.text)
    title = x.xpath('//table[@class="olt"]//td[@class="title"]/a/@title')
    href = x.xpath('//table[@class="olt"]//td[@class="title"]/a/@href')
    author = [
        i.xpath("string()")
        for i in x.xpath('//table[@class="olt"]//td[@nowrap="nowrap"]/a[@class]')
    ]
    response = [
        i.xpath("string()")
        for i in x.xpath('//table[@class="olt"]//td[@nowrap="nowrap" and @class][1]')
    ]
    last_time = [
        i.xpath("string()")
        for i in x.xpath('//table[@class="olt"]//td[@nowrap="nowrap" and @class][2]')
    ]
    return title, href, author, response, last_time


title_ls, href_ls, author_ls, response_ls, last_time_ls = [], [], [], [], []
i = 0
for i in tqdm.tqdm(range(100)):
    # 上海无中介租房
    # url = 'https://www.douban.com/group/592830/discussion?start={}'.format(i*25)
    # 上海租房@地铁沿线租房
    # url = 'https://www.douban.com/group/592831/discussion?start={}'.format(i*25)
    # 上海租房（不良中介勿扰）
    url = "https://www.douban.com/group/shzf/discussion?start={}".format(i * 25)
    # 上海租房
    # url = 'https://www.douban.com/group/shanghaizufang/discussion?start={}'.format(i*25)
    # 上海租房---房子是租来的
    # url = 'https://www.douban.com/group/homeatshanghai/discussion?start={}'.format(i*25)
    print(url)
    try:
        title, href, author, response, last_time = GetPostList(url)
        title_ls.extend(title)
        href_ls.extend(href)
        author_ls.extend(author)
        response_ls.extend(response)
        last_time_ls.extend(last_time)
    except Exception as e:
        print(e)
    time.sleep(random.random())
    i += 1

df = pd.DataFrame(
    {
        "title": title_ls,
        "href": href_ls,
        "author": author_ls,
        "response": response_ls,
        "last_time": last_time_ls,
    }
)

df.to_excel("上海租房（不良中介勿扰）_page100.xlsx", index=False)
