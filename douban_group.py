import requests
from lxml import etree
import re
import json
import random
import time
import tqdm
import pandas as pd


headers = {
	'Host': 'accounts.douban.com',
	'Origin': 'https://accounts.douban.com',
	'Referer': 'https://accounts.douban.com/login?source=group',
	'Upgrade-Insecure-Requests': '1',
	'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.139 Safari/537.36'
}



data = {
	'ck': '0Sg3',
	'source': 'None',
	'redir': 'https://www.douban.com',
	'form_email': '1553526263@qq.com',
	'form_password': 'hou19910922',
	'login': '登录'
}


# from requests.auth import HTTPBasicAuth
# auth = HTTPBasicAuth('1553526263@qq.com', 'hou19910922')

post_url = 'https://accounts.douban.com/login'

s = requests.Session()
s.post(post_url,headers=headers,data=data)


def GetPostList(url):
	res = s.get(url)
	x = etree.HTML(res.text)
	title = x.xpath('//table[@class="olt"]//td[@class="td-subject"]/a/@title')
	# href = x.xpath('//table[@class="olt"]//td[@class="title"]/a/@href')
	href = x.xpath('//table[@class="olt"]//td[@class="td-subject"]/a/@href')
	group = x.xpath('//table[@class="olt"]//td[@class="td-group"]/a/text()')
	response = [i[:-2] for i in x.xpath('//table[@class="olt"]//td[@class="td-reply"]/text()')]
	last_time = x.xpath('//table[@class="olt"]//td[@class="td-time"]/@title')
	return title,href,author,response,last_time

