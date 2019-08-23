# coding: utf8
import os
import sys
DIR = os.path.normpath(os.path.join(os.path.abspath(__file__), '../../../'))
sys.path.insert(0, DIR)
import re
import time
import datetime
from common.schedule import sched
from crawl.task import Task
from mongoengine import Q
from crawl.templates.base import Template
from crawl.parse.utils import parse_ali_list_page
from common.models.system import SystemCookie
from common.models.data import get_tmall_good_cls
from common.models.data.taobao import TmallDressShop


tmall_cookie = SystemCookie.get_cookie(suitable_site='tmall')


URL_BASE = 'https://shop{}.taobao.com/"//playboymitu.tmall.com/search.htm?search=y&orderType=defaultSort&scene=taobao_shop&pageNo={}&tsearch=y#anchor"'


class TmallGoodSearchCrawl(Template):

    @classmethod
    @sched(__file__)
    def load(cls, instance):
        instance.second_rate_limit = 50
        instance.save()

        valid_started_at = datetime.datetime.now()

        for shop in TmallDressShop.objects(TmallDressShop.valid_q).only('id', 'shop_name').no_cache():
            cls.check_task_queue(instance.id, 1000)
            task = Task()
            task.instance_id = instance.id
            task.url = URL_BASE.format(shop.id, 1)
            task.temp_data['shop_id'] = shop.id
            task.temp_data['shop_name'] = shop.shop_name
            task.temp_data['url_base'] = URL_BASE
            task.headers = {
                'referer': 'https://detail.tmall.com/item.htm',
                'cookie': tmall_cookie,
            }
            task.function = cls.parse_good_list_page
            # task.use_proxy = True
            task.remaining_retries = 4
            task.is_redirect = False
            task.get_certifi_verify = False
            task.timeout = 15
            task.add()

        for shop in TmallDressShop.objects(TmallDressShop.valid_q & Q(updated_at__lt=valid_started_at)).only('id', 'shop_name').no_cache():
            cls.check_task_queue(instance.id, 1000)
            task = Task()
            task.instance_id = instance.id
            task.url = URL_BASE.format(shop.id, 1)
            task.temp_data['shop_id'] = shop.id
            task.temp_data['shop_name'] = shop.shop_name
            task.temp_data['url_base'] = URL_BASE
            task.headers = {
                'referer': 'https://detail.tmall.com/item.htm',
                'cookie': tmall_cookie,
            }
            task.function = cls.parse_good_list_page
            # task.use_proxy = True
            task.is_redirect = False
            task.get_certifi_verify = False
            task.timeout = 15
            task.add()

    @classmethod
    def parse_good_list_page(cls, task, page_raw):

        shop_id = task.temp_data['shop_id']
        shop_name = task.temp_data['shop_name']
        url_base = task.temp_data['url_base']

        pi = parse_ali_list_page(page_raw)
        if pi.is_invalid:
            TmallDressShop.objects(id=shop_id).update(set__is_invalid=True, set__updated_at=datetime.datetime.now())
            return

        kwds = {}
        if pi.shop_url:
            kwds['set__shop_url'] = pi.shop_url
        kwds['set__seller_id'] = pi.seller_id
        kwds['set__shop_type'] = pi.shop_type
        kwds['set__updated_at'] = datetime.datetime.now()
        TmallDressShop.objects(id=shop_id).update(**kwds)

        for good in pi.goods:
            good_id = good.good_id
            good_cls = get_tmall_good_cls(good_id)
            kwds = {}
            kwds['set__is_invalid'] = False
            kwds['set__updated_at'] = datetime.datetime.now()
            kwds['set__shop_id'] = shop_id
            kwds['set__shop_name'] = shop_name
            kwds['set__seller_id'] = pi.seller_id
            kwds['set__shop_type'] = pi.shop_type
            kwds['upsert'] = True
            if not good_cls.get(good_id):
                kwds['set__created_at'] = datetime.datetime.now()
            if good.discount_price:
                kwds['set__discount_price'] = good.discount_price
            kwds['set__total_sales_qty'] = good.total_sales_qty
            if good.total_sales_qty:
                if int(good.total_sales_qty) < 1 and 'set__created_at' not in kwds:  # 剔除总销量为0的数据
                    continue
            kwds['set__monthly_sales_qty'] = good.monthly_sales_qty  # 只有天猫有, 为0 不抓详情页
            if good.monthly_sales_qty:
                if int(good.monthly_sales_qty) < 1 and 'set__created_at' not in kwds:  # 剔除月销量为0的数据
                    continue
            if good.total_comment_count:
                kwds['set__total_comment_count'] = good.total_comment_count
            if good.item_name:
                kwds['set__item_name'] = good.item_name
            good_cls.objects(id=good_id).update(**kwds)

        if pi.page and task.url == url_base.format(shop_id, 1) and int(pi.page) > 1:
            for i in range(2, int(pi.page)+1):
                new_task = task.new()
                new_task.url = url_base.format(shop_id, i)
                new_task.add()


if __name__ == '__main__':
    TmallGoodSearchCrawl.run()
