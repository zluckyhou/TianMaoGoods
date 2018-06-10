# coding:utf-8


# ### 使用selenium抓取淘宝商品，并保存到mongodb

# In[79]:


from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.keys import Keys


# In[274]:


from lxml import etree
import re
from tqdm import tqdm
import time
import os
import base64
import json
from PIL import Image
from user_agent import generate_user_agent


# In[174]:


def parse_product():
    print('正在获取商品列表')
    try:
        html = browser.page_source
        s = etree.HTML(html)
        product_url = s.xpath('//div[@class="productImg-wrap"]/a/@href')
        product_img = s.xpath('//div[@class="productImg-wrap"]/a/img/@src')
        product_price = s.xpath('//p[@class="productPrice"]//em/@title')
        product_title = s.xpath('//p[@class="productTitle"]/a/@title')
        product_shop_name = s.xpath('//div[@class="productShop"]/a[@class="productShop-name"]/text()')
        product_shop_url = s.xpath('//div[@class="productShop"]/a[@class="productShop-name"]/@href')
        product_month_gc = s.xpath('//p[@class="productStatus"]//span[contains(text(),"月成交")]/em/text()')
        product_comments = s.xpath('//p[@class="productStatus"]//span[contains(text(),"评价")]/a/text()')
        product_comments_url = s.xpath('//p[@class="productStatus"]//span[contains(text(),"评价")]/a/@href')

        res = []
        for i in range(len(product_url)):
            d = {
                'product_url':product_url[i],
                'product_img':product_img[i],
                'product_price':float(product_price[i]),
                'product_title':product_title[i],
                'product_shop_name':product_shop_name[i],
                'product_shop_url':product_shop_url[i],
                'product_month_gc':re.findall('\d+',product_month_gc[i])[0],
                'product_comments':int(product_comments[i]),
                'product_comments_url':product_comments_url[i]    
            }
            res.append(d)
        save_to_mongo(res)
    except Exception as e:
        print(e)


# In[169]:


mongo_url = 'mongodb://admin:9870384@localhost'
mongo_db = 'crawler'
mongo_collection = 'ca'
client = pymongo.MongoClient(mongo_url)
db=client[mongo_db]


# In[170]:


def save_to_mongo(res):
    '''
    保存至mongodb
    :param result:结果
    '''
    try:
        if db[mongo_collection].insert_many(res):
            print('成功存储到mongodb')
    except Exception as e:
        print('存储到mongodb失败',e)


# In[299]:


def get_page(page):
    '''
    抓取商品列表页
    :param page:页码
    '''
    print('正在抓取第{}页'.format(page))
    global jumpto_element
    try:
        jumpto_element.clear()
        jumpto_element.send_keys(page)
        jumpto_element.send_keys(Keys.RETURN)
        ### 判断是否需要处理验证码
        handle_checkcode(browser)
        jumpto_element = wait.until(EC.presence_of_element_located((By.NAME,'jumpto')))
        parse_product()
    except Exception as e:
        print(e)


# #### 验证码识别

# In[277]:


### 调用阿里云验证码识别接口

def get_verify_code_by_ali(pic_path,tp='cen'):
    host = 'http://jisuyzmsb.market.alicloudapi.com'
    path = '/captcha/recognize'
    appcode = 'c5e14e8feb17494aa6cedb63f8dcb82f'
    querys = 'type={}'.format(tp)
    url = host + path + '?' + querys

    with open(pic_path,'rb') as f:
        data = f.read()
    bodys = {}
    bodys['pic'] = base64.b64encode(data)

    headers = {
        'Authorization': 'APPCODE ' + appcode,
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
    }

    r = requests.post(url,data=bodys,headers=headers)
    if r.status_code !=200:
        return False

    res = json.loads(r.text)
    if res.get('msg') != 'ok':
        return False
    return res['result']['code']


### 获取验证码
def recognize_verify_code(browser):
    page_path='./page.png'
    browser.save_screenshot(page_path)
    
    image = Image.open(page_path)
    verify_code_path = './verify_code.png'
    verify_image_element = browser.find_element_by_xpath('//img[@id="checkcodeImg"]')
    # 获取图片坐标
    x1 = verify_image_element.location['x']
    y1 = verify_image_element.location['y']
    delta_x = verify_image_element.size['width']
    delta_y = verify_image_element.size['height']
    x2 = x1+delta_x
    y2 = y1+delta_y
    box = (x1,y1,x2,y2)
    image = image.crop(box)
    image.save(verify_code_path)
    verify_code = get_verify_code_by_ali(verify_code_path)
    return verify_code

### 输入验证码

def input_verify(browser):
    verify_input_element = browser.find_element_by_id('checkcodeInput')
    verify_code = recognize_verify_code(browser)
    print('验证码：',verify_code)
    verify_input_element.clear()
    verify_input_element.send_keys(verify_code)
    verify_input_element.send_keys(Keys.RETURN)
    time.sleep(1)
    if '验证错误' in browser.page_source:
        print('验证错误,请重新输入...')
        return True
    else:
        print('验证成功!')
        return False
    
    


# #### 判断是否需要输入验证码，并处理

# In[301]:


def handle_checkcode(browser):
    try:
        nickname = wait.until(EC.presence_of_element_located((By.XPATH,'//a[@class="j_Username j_UserNick sn-user-nick"]')))
        if nickname.get_attribute('title')=='tb5792639_2012':
            print('跳转成功')
    except Exception as e:
        # 识别验证码
        if '验证码' in browser.page_source:
            print('需要验证码识别...')
            i = 1
            flag = True
            while i<=5 & flag:
                print('第{}次识别...'.format(i))
                flag = input_verify(browser)
        else:
            print(e)


# In[222]:


co = webdriver.ChromeOptions()
# co.add_argument('--headerless')
# co.add_argument('--disable-images')
co.add_argument('--user-agent={}'.format(generate_user_agent(navigator=['chrome'])))


# In[287]:


browser=webdriver.Chrome(chrome_options=co,service_log_path=os.path.devnull)
browser.get('https://www.tmall.com/')

wait = WebDriverWait(browser,10)


# In[288]:


#点击登录按钮
login_button = wait.until(EC.presence_of_element_located((By.XPATH,'//a[@class="sn-login"]')))
login_button.click()



# In[289]:


# 手动登录
try:
    nickname = wait.until(EC.presence_of_element_located((By.XPATH,'//a[@class="j_Username j_UserNick sn-user-nick"]')))
    if nickname.get_attribute('title')=='tb5792639_2012':
        print('登录成功')
    else:
        print('登录失败')
except Exception as e:
    print(e)


# In[290]:


# 搜索目标产品

input_element = wait.until(EC.presence_of_element_located((By.ID,'mq')))

input_element.clear()
input_element.send_keys('H&M')
input_element.send_keys(Keys.RETURN)

# 判断是否需要验证
handle_checkcode(browser) 


# In[297]:



# 跳转到搜索结果页，获取产品总页数
jumpto_element = wait.until(EC.presence_of_element_located((By.NAME,'jumpto')))

s =etree.HTML(browser.page_source)

page_info = ','.join(s.xpath('//form[@name="filterPageForm"]//text()'))

total_page = int(re.findall('共(.*?)页',page_info)[0])


# In[298]:


total_page


# In[204]:


for page in tqdm(range(1,total_page+1)):
    get_page(page)
    time.sleep(1)
browser.quit()


