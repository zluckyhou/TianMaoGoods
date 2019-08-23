# coding: utf8
import re
import json
import datetime,time
from HTMLParser import HTMLParser
from crawl.parse.site import Site
from crawl.parse.item import ParseItem
from crawl.parse.utils import parse_doc, get_num


site = Site('tmall')


@site.route('mdskip.taobao.com', '/core/initItemDetail.htm')
def parse_mdskip_json(url_string, page_raw, kwargs):
    page_raw = page_raw.strip()
    if page_raw.startswith('setMdskip'):
        page_raw = page_raw.replace('setMdskip', '').strip()
        page_raw = re.findall(r'\(([\d\D]+)\)', page_raw)[0]

    dct = json.loads(page_raw)

    pi = ParseItem()
    if 'sellCountDO' in dct['defaultModel'] and 'sellCount' in dct['defaultModel']['sellCountDO']:
        pi.monthly_sales_qty = str(dct['defaultModel']['sellCountDO']['sellCount'])
    pi.prices = []
    for sku_id, price_info in dct['defaultModel']['itemPriceResultDO']['priceInfo'].iteritems():
        price = ParseItem()
        price.sku_id = str(sku_id)
        price.list_price = str(price_info['price'])
        discount_price_list = [str(each.get('price', '') or '') for each in (price_info.get('promotionList', {}) or {})]
        price.discount_price = discount_price_list[0] if discount_price_list else ''
        pi.discount_price = price.discount_price
        pi.prices.append(price)

    return pi


@site.route('detail.tmall.com', '/item.htm')
def parse_good_detail_page(url_string, page_raw, kwargs):

    doc = parse_doc(page_raw)
    pi = ParseItem()

    item_name_xpath = "//div[@class='tb-detail-hd']/h1/text()"
    item_sub_title_xpath = "//div[@class='tb-detail-hd']/p/text()"

    if doc.xpath(item_name_xpath):
        pi.item_name = doc.xpath(item_name_xpath)[0].strip().replace('\t', '').replace('\r', '').replace('\n', '')
    if doc.xpath(item_sub_title_xpath):
        pi.item_sub_title = doc.xpath(item_sub_title_xpath)[0].strip().replace('\t', '').replace('\r', '').replace('\n', '')

    dct = json.loads(re.findall(r'TShop\.Setup\(([\d\D]+)\}\)\(\);', page_raw)[0].strip()[:-2])
    pi.sku_list = json.dumps(dct.get('valItemInfo', '') or '')
    pi.instock = str(dct['itemDO']['quantity'])
    pi.list_price = str(dct['itemDO']['reservePrice'])
    pi.category_id = str(dct['itemDO']['categoryId'])
    if 'newProGroup' in dct['itemDO']:
        attribute_list = []
        for attr in dct['itemDO']['newProGroup']:
            for value in attr.get('attrs') or []:
                if value['name'].strip() == u'品牌':
                    pi.brand_name = value['value'].strip()
                attribute_list.append(value['name'].strip() + ':' + value['value'].strip())
        attributes = ' && '.join(attribute_list)
    else:
        attribute_xpath = "//ul[@id='J_AttrUL']/li/text()"
        for each in doc.xpath("//ul[@id='J_AttrUL']/li"):
            text = ''.join(each.xpath("./text()"))
            if u'品牌' == text.split(':')[0].strip():
                pi.brand_name = text.split(':')[1].strip()
        attributes = ' && '.join([e.strip() for e in doc.xpath(attribute_xpath) if e.strip()])
    pi.item_attr_desc = attributes
    item_main_image_url_xpath = "//div[@class='tb-booth']//img/@src"
    if doc.xpath(item_main_image_url_xpath):
        item_main_image_url = doc.xpath(item_main_image_url_xpath)[0]
        if 'https' not in item_main_image_url:
            item_main_image_url = 'https:' + item_main_image_url
        pi.item_main_image_url = item_main_image_url

    if re.findall(r'"globalSellItem":true', page_raw):
        pi.is_worldwide = True

    return pi


# @site.route('', '')
def parse_good_list_page(url_string, page_raw, kwargs):

    good_xpath = "//div[@class='J_TItems']/div[@class='item4line1']/dl[contains(@class, 'item')]"
    shop_url_xpath = "//a[@class='slogo-shopname']/@href"
    page_xpath = "//p[@class='ui-page-s']/b[contains(@class, 'ui-page-s')]/text()"

    doc = parse_doc(page_raw)
    pi = ParseItem()

    pi.seller_id = re.findall(r'sellerId: *"(\d+)",', page_raw)
    pi.page = doc.xpath(page_xpath)[0].strip().split('/')[1]

    if doc.xpath(shop_url_xpath):
        shop_url = doc.xpath(shop_url_xpath)[0].strip()
        pi.shop_url = 'https:' + shop_url if 'https:' not in shop_url else shop_url

    pi.goods = []
    for each in doc.xpath(good_xpath):
        good_id_xpath = "./@data-id"
        discount_price_xpath = "./dd[@class='detail']/div[@class='attribute']//span[@class='c-price']/text()"
        sales_qty_xpath = "./dd[@class='detail']/div[@class='attribute']//div[@class='sale-area']//text()"
        total_comment_count_xpath = u"./dd[@class='rates']//span[contains(text(), '评')]/text()"
        item_name_xpath = "./dd[@class='detail']/a[contains(@class, 'item-name')]/text()"

        good = ParseItem()
        good.good_id = each.xpath(good_id_xpath)[0].strip()
        good.discount_price = ''.join(each.xpath(discount_price_xpath)).strip()
        if each.xpath(sales_qty_xpath):
            sales_text = ''.join(each.xpath(sales_qty_xpath)).strip()
            if u'月' in sales_text:
                good.monthly_sales_qty = str(get_num(sales_text, int))
            elif u'总' in sales_text:
                good.total_sales_qty = str(get_num(sales_text, int))
        if each.xpath(total_comment_count_xpath):
            comment_text = ''.join(each.xpath(total_comment_count_xpath)).strip()
            good.total_comment_count = str(get_num(comment_text, int))
        if each.xpath(item_name_xpath):
            good.item_name = each.xpath(item_name_xpath)[0].strip()
        pi.goods.append(good)
    return pi


@site.route('detail.m.tmall.hk', '/item.htm')
@site.route('detail.m.tmall.com', '/item.htm')
def parse_m_good_detail_page(url_string, page_raw, kwargs):
    pi = ParseItem()

    data_detail = re.findall(r'_DATA_Detail *= *(.+);', page_raw)[0]
    dct = json.loads(data_detail)

    pi.item_name = dct['itemDO']['title'].replace(u'&quot;', u'"')
    if 'newAttraction' in dct['itemDO'] and dct['itemDO']['newAttraction'].strip():
        pi.item_sub_title = dct['itemDO']['newAttraction'].strip()

    pi.sku_list = json.dumps(dct.get('valItemInfo', '') or '')
    pi.instock = str(dct['itemDO']['quantity'])
    pi.list_price = str(dct['itemDO']['reservePrice'])
    pi.category_id = str(dct['itemDO']['categoryId'])
    if 'mainPic' in dct['itemDO'] and dct['itemDO']['mainPic'].strip():
        item_main_image_url = dct['itemDO']['mainPic'].strip()
        if 'https' not in item_main_image_url:
            item_main_image_url = 'https:' + item_main_image_url
        pi.item_main_image_url = item_main_image_url
    if 'brand' in dct['itemDO'] and dct['itemDO']['brand'].strip():
        pi.brand_name = HTMLParser().unescape(dct['itemDO']['brand'].strip())

    data_mdskip = re.findall(r'_DATA_Mdskip *= *(.+?)</script>', page_raw.replace(u'\n', '').replace(u'\r', ''))[0]
    dct = json.loads(data_mdskip)
    if 'sellCountDO' in dct['defaultModel'] and 'sellCount' in dct['defaultModel']['sellCountDO']:
        pi.monthly_sales_qty = str(dct['defaultModel']['sellCountDO']['sellCount'])
    if 'rateDO' in dct['defaultModel'] and 'rateCounts' in dct['defaultModel']['rateDO']:
        pi.total_comment_count = str(dct['defaultModel']['rateDO']['rateCounts'])
    pi.prices = []
    for sku_id, price_info in dct['defaultModel']['itemPriceResultDO']['priceInfo'].iteritems():
        price = ParseItem()
        price.sku_id = str(sku_id)
        price.list_price = str(price_info['price'])
        discount_price_list = [str(each.get('price', '') or '') for each in (price_info.get('promotionList', {}) or {})]
        price.discount_price = discount_price_list[0] if discount_price_list else ''
        pi.discount_price = price.discount_price
        pi.prices.append(price)
    pi.price_list = json.dumps({'prices': pi.prices})

    if re.findall(r'"globalSellItem":true', page_raw):
        pi.is_worldwide = True

    return pi


@site.route('rate.tmall.com', '/list_detail_rate.htm')
def parse_tmall_comment(url_string, page_raw, kwargs):

    pi = ParseItem()
    try:
        dct = json.loads(page_raw)
        pi.feng = '0'
    except:
        pi.feng = '1'
        dct = json.loads('{' + page_raw + '}')

        pi.total_comment_count = str(dct['rateDetail']['rateCount']['total'])
        items = dct['rateDetail']['rateList']
        pi.page = dct['rateDetail']['paginator']['lastPage']

        pi.replies = []

        for item in items:
            reply = ParseItem()

            reply_id = 0
            reply.reply_id = str(reply_id)
            user_name = item['displayUserNick']
            reply.user_name = user_name
            reply.user_type = '0'
            reply.content_type = '0'
            reply.content = item['rateContent']
            pics = item['pics']
            comment_image_urls = ''
            for pic in pics:
                comment_image_urls += str(pic) + ':'
            reply.comment_image_urls = comment_image_urls
            created_at = str(item['rateDate'])
            reply.created_at = datetime.datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
            reply.sku_info = item['auctionSku']
            user_level = str(item['tamllSweetLevel'])
            reply.user_level = str(user_level)
            reply.comment_id = str(item['id'])

            pi.replies.append(reply)

            if item['reply'].encode('utf8') != '':
                reply = ParseItem()

                reply.content_type = '0'
                reply.created_at = datetime.datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
                reply.comment_id = str(item['id'])
                reply.sku_info = item['auctionSku']
                reply_id += 1
                reply.reply_id = str(reply_id)
                reply.user_type = '1'
                reply.content = item['reply']
                reply.user_name = ''
                reply.user_level = ''
                reply.replied_user_name = user_name
                reply.comment_image_urls = ''

                pi.replies.append(reply)

            if 'content' in item['appendComment']:
                reply = ParseItem()

                reply.content_type = '0'
                reply_id += 1
                reply.comment_id = str(item['id'])
                reply.sku_info = item['auctionSku']
                reply.reply_id = str(reply_id)
                reply.user_type = '0'
                reply.user_name = user_name
                reply.user_level = str(user_level)
                reply.content = item['appendComment']['content']
                pics = item['pics']
                comment_image_urls = ''
                for pic in pics:
                    comment_image_urls += str(pic) + ':'
                reply.comment_image_urls = comment_image_urls
                created_at = item['appendComment']['commentTime']
                reply.created_at = datetime.datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
                reply.replied_user_name = ''

                pi.replies.append(reply)

                if item['reply'].encode('utf8') != '':
                    reply = ParseItem()

                    reply.content_type = '0'
                    reply_id += 1
                    reply.created_at = datetime.datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
                    reply.comment_id = str(item['id'])
                    reply.sku_info = item['auctionSku']
                    reply.reply_id = str(reply_id)
                    reply.user_type = '1'
                    reply.content = item['reply']
                    reply.user_name = ''
                    reply.user_level = ''
                    reply.replied_user_name = user_name
                    reply.comment_image_urls = ''

                    pi.replies.append(reply)

    return pi
