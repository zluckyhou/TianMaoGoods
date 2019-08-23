# coding: utf8
import re
import json
import datetime
from crawl.parse.site import Site
from crawl.parse.item import ParseItem
from crawl.parse.utils import parse_doc, get_num


site = Site('taobao')


def get_created_at(time_text):
    now = datetime.datetime.now()
    if u'刚刚' in time_text:
        return now
    elif u'秒钟前' in time_text or u'秒前' in time_text:
        return now - datetime.timedelta(seconds=get_num(time_text, int))
    elif u'分钟前' in time_text or u'分前' in time_text:
        return now - datetime.timedelta(minutes=get_num(time_text, int))
    elif u'小时前' in time_text or u'时前' in time_text:
        return now - datetime.timedelta(hours=get_num(time_text, int))
    elif u'天前' in time_text:
        return now - datetime.timedelta(days=get_num(time_text, int))
    elif time_text.strip() == '':
        return now
    elif re.findall(r'(\d+)-(\d+)-(\d+) (\d+):(\d+)', time_text):
        year, month, day, hour, minute = map(int, re.findall(r'(\d+)-(\d+)-(\d+) (\d+):(\d+)', time_text)[0])
        return datetime.datetime(year, month, day, hour, minute)
    elif re.findall(r'(\d+)-(\d+)-(\d+) (\d+):(\d+):(\d+)', time_text):
        year, month, day, hour, minute, miao = map(int,
                                                   re.findall(r'(\d+)-(\d+)-(\d+) (\d+):(\d+):(\d+)', time_text)[0])
        return datetime.datetime(year, month, day, hour, minute, miao)
    elif re.findall(r'(\d+)-(\d+)-(\d+)', time_text):
        year, month, day = map(int, re.findall(r'(\d+)-(\d+)-(\d+)', time_text)[0])
        return datetime.datetime(year, month, day)
    elif re.findall(r'(\d+)-(\d+) (\d+):(\d+)', time_text):
        month, day, hour, minute = map(int, re.findall(r'(\d+)-(\d+) (\d+):(\d+)', time_text)[0])
        try:
            temp = datetime.datetime(now.year, month, day, hour, minute)
        except:
            temp = datetime.datetime(now.year - 1, month, day, hour, minute)
        if temp > now:
            return datetime.datetime(now.year - 1, month, day, hour, minute)
        else:
            return datetime.datetime(now.year, month, day, hour, minute)
    else:
        raise ValueError('time_text wrong')


@site.route('detailskip.taobao.com', '/service/getData/1/p1/item/detail/sib.htm')
def parse_detailskip_json(url_string, page_raw, kwargs):

    dct = json.loads(re.findall(r'onSibRequestSuccess\((.+)\);', page_raw)[0])

    pi = ParseItem()
    if 'soldQuantity' in dct['data']:
        pi.monthly_sales_qty = str(dct['data']['soldQuantity']['soldTotalCount'])
    pi.list_price = str(dct['data']['price'])
    pi.instock = str(dct['data']['dynStock']['sellableQuantity'])
    pi.prices = []
    if 'sku' in dct['data']['dynStock']:
        stocks = dct['data']['dynStock']['sku']
        prices = dct['data']['promotion']['promoData']
        for stock in stocks:
            price = ParseItem()
            price.sku_id = str(stock)
            price.stock = stocks[stock]['stock']
            price.list_price = pi.list_price
            if stock in prices:
                price.discount_price = prices[stock][0].get('price', '') or ''
                pi.discount_price = price.discount_price
            else:
                price.discount_price = ''
            pi.prices.append(price)
    else:
        price = ParseItem()
        price.sku_id = ''
        price.discount_price = pi.list_price
        price.list_price = pi.list_price
        price.stock = dct['data']['dynStock'].get('stock') or ''
        pi.prices.append(price)

    return pi


@site.route('item.taobao.com', '/item.htm')
def parse_good_detail_page(url_string, page_raw, kwargs):

    doc = parse_doc(page_raw)
    pi = ParseItem()

    item_name_xpath = "//div[@id='J_Title']/h3/text()"
    item_sub_title_xpath = "//div[@id='J_Title']/p/text()"

    if doc.xpath(item_name_xpath):
        pi.item_name = ' '.join(doc.xpath(item_name_xpath)).strip().replace('\t', '').replace('\r', '').replace('\n', '')
    if doc.xpath(item_sub_title_xpath):
        pi.item_sub_title = ' '.join(doc.xpath(item_sub_title_xpath)).strip().replace('\t', '').replace('\r', '').replace('\n', '')

    pi.category_id = re.findall(r"(?<!r)cid *: *'(\d+)'", page_raw)[0]
    sku_dct = json.loads(re.findall(r'skuMap *:(.+)', page_raw)[0].strip())
    property_dct = json.loads(re.findall(r'propertyMemoMap *:(.+)', page_raw)[0])
    pi.sku_list = json.dumps({'skuMap': sku_dct, 'propertyMemoMap': property_dct})

    attribute_xpath = "//div[@id='attributes']/ul[@class='attributes-list']/li/text()"
    for each in doc.xpath(attribute_xpath):
        text = each.strip()
        if u'品牌' == text.split(':')[0].strip():
            pi.brand_name = text.split(':')[1].strip()
    attributes = ' && '.join([e.strip() for e in doc.xpath(attribute_xpath) if e.strip()])
    pi.item_attr_desc = attributes

    item_main_image_url_xpath = "//div[contains(@class, 'tb-booth')]//img/@src"
    if doc.xpath(item_main_image_url_xpath):
        item_main_image_url = doc.xpath(item_main_image_url_xpath)[0]
        if 'https' not in item_main_image_url:
            item_main_image_url = 'https:' + item_main_image_url
        pi.item_main_image_url = item_main_image_url

    if re.findall(r'globalBuyer +: +true', page_raw):
        pi.is_worldwide = True

    return pi


@site.route('shopsearch.taobao.com', '/search')
def parse_shop_list_page(url_string, page_raw, kwargs):
    # callback = kwargs['callback']

    page_raw = re.sub(u'jsonp\d+', '', page_raw).strip()[1:-2]
    # page_raw = page_raw.replace(callback, '').strip()[1:-2]
    dct = json.loads(page_raw)
    shop_list = dct['mods']['shoplist']['data']['shopItems']

    pi = ParseItem()
    pi.total_page = dct['mods']['pager']['data'].get('totalPage')
    if not pi.total_page:
        return
    pi.current_page = dct['mods']['pager']['data']['currentPage']
    pi.page_size = dct['mods']['pager']['data']['pageSize']
    pi.total_count = dct['mods']['pager']['data']['totalCount']
    pi.shops = []
    for each in shop_list:
        shop = ParseItem()
        shop.id = each['nid']
        shop.shop_name = ' '.join(each['title'].split())
        shop.detail_url = 'https:' + each['shopUrl'] if 'http' not in each['shopUrl'] else each['shopUrl']
        shop.seller_id = each['uid']
        shop.seller_nick_name = each['nick']
        shop.shop_location = each['provcity']
        dsr = each['dsrInfo']['dsrStr']
        dsr_dct = json.loads(dsr)
        shop.business_scope = dsr_dct['ind']
        shop.shop_level = str(int(int(dsr_dct['srn']) * get_num(dsr_dct['sgr'])/100))
        shop.shop_dsr = dsr_dct['sgr']
        shop.shop_dsr_detail = dsr
        shop.is_tmall = each['isTmall'] == 'true'
        pi.shops.append(shop)
    return pi


@site.route('s.taobao.com', '/search')
def parse_good_list_json(url_string, page_raw, kwargs):
    page_raw = re.sub(u'jsonp\d+', '', page_raw).strip()[1:-2]
    dct = json.loads(page_raw, strict=False)
    good_list = dct['mods']['itemlist']['data']['auctions']

    pi = ParseItem()
    pi.total_page = dct['mods']['pager']['data']['totalPage']
    pi.current_page = dct['mods']['pager']['data']['currentPage']
    pi.total_count = dct['mods']['pager']['data']['totalCount']

    pi.goods = []
    for each in good_list:
        good = ParseItem()
        good.category_id = each['category']
        good.item_id = each['nid']
        good.seller_id = each['user_id']
        good.item_name = each['raw_title']
        good.total_comment_count = each['comment_count']
        good.shop_type = 'tmall' if each['shopcard']['isTmall'] else 'taobao'
        good.discount_price = each['view_price']
        pi.goods.append(good)
    return pi


@site.route('count.taobao.com', '/counter3')
def parse_good_favorite_json(url_string, page_raw, kwargs):
    page_raw = re.findall(r'jsonp\d+\((.+)\);', page_raw)[0]
    page_raw = re.sub(r':\{.+?\}', ':""', page_raw)
    dct = json.loads(page_raw)

    pi = ParseItem()
    pi.dct = dct

    return pi


@site.route('rate.taobao.com', '/feedRateList.htm')
def parse_taobao_comment(url_string, page_raw, kwargs):

    page_raw = re.findall('\((.+)\)', page_raw)[0]
    pi = ParseItem()

    dct = json.loads(page_raw)
    pi.total_comment_count = str(dct['total'])
    if int(dct['total']) / 20 == 0:
        page = int(dct['total']) / 20
    else:
        page = int(dct['total']) / 20 + 1
    if page > 250:
        page = 250
    pi.page = page

    pi.replies = []

    items = dct['comments']
    for item in items:
        reply = ParseItem()

        reply_id = 0
        reply.reply_id = str(reply_id)
        user_name = item['user']['nick']
        reply.user_name = user_name
        reply.user_type = '0'
        reply.content_type = '0'
        reply.content = item['content']
        comment_level = str(item['rate'])
        reply.comment_level = comment_level
        tags = item['tag']
        reply.tags = tags
        pics = item['photos']
        comment_image_urls = ''
        for pic in pics:
            if 'url' in pic:
                comment_image_urls += str(pic['url']) + ':'
        reply.comment_image_urls = comment_image_urls
        created_at = item['date'].replace(u'年', '-').replace(u'月', '-').replace(u'日', '')
        reply.created_at = get_created_at(created_at)
        reply.sku_info = item['auction']['sku']
        user_level = str(item['user']['displayRatePic']).replace('.gif','')
        reply.user_level = str(user_level)

        reply.comment_id = str(item['rateId'])
        pi.replies.append(reply)

        if item['reply'] != None:
            reply = ParseItem()

            reply.comment_level = comment_level
            reply.content_type = '0'
            reply.created_at = get_created_at(created_at)
            reply.comment_id = str(item['rateId'])
            reply.sku_info = item['auction']['sku']
            reply.tags = tags
            reply_id += 1
            reply.reply_id = str(reply_id)
            reply.user_type = '1'
            reply.content = item['reply']['content']
            reply.user_name = ''
            reply.user_level = ''
            reply.replied_user_name = user_name
            reply.comment_image_urls = ''

            pi.replies.append(reply)

        for each in item['appendList']:
            if 'content' in each:
                reply = ParseItem()

                reply.comment_level = comment_level
                reply.content_type = '0'
                reply_id += 1
                reply.tags = tags
                reply.comment_id = str(item['rateId'])
                reply.sku_info = item['auction']['sku']
                reply.reply_id = str(reply_id)
                reply.user_type = '0'
                reply.user_name = user_name
                reply.user_level = str(user_level)
                reply.content = each['content']
                pics = each['photos']
                comment_image_urls = ''
                for pic in pics:
                    if 'url' in pic:
                        comment_image_urls += str(pic['url']) + ':'
                reply.comment_image_urls = comment_image_urls
                dayAfterConfirm = each['dayAfterConfirm']
                reply.created_at = get_created_at(created_at) + datetime.timedelta(dayAfterConfirm)
                reply.replied_user_name = ''

                pi.replies.append(reply)

                if each['reply'] != None:
                    reply = ParseItem()

                    reply.content_type = '0'
                    reply.tags = tags
                    reply.comment_level = comment_level
                    reply_id += 1
                    reply.created_at = get_created_at(created_at) + datetime.timedelta(dayAfterConfirm)
                    reply.comment_id = str(item['rateId'])
                    reply.sku_info = item['auction']['sku']
                    reply.reply_id = str(reply_id)
                    reply.user_type = '1'
                    reply.content = each['reply']['content']
                    reply.user_name = ''
                    reply.user_level = ''
                    reply.replied_user_name = user_name
                    reply.comment_image_urls = ''

                    pi.replies.append(reply)

    return pi
