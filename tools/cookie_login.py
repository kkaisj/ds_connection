# 使用提醒:
# 1. xbot包提供软件自动化、数据表格、Excel、日志、AI等功能
# 2. package包提供访问当前应用数据的功能，如获取元素、访问全局变量、获取资源文件等功能
# 3. 当此模块作为流程独立运行时执行main函数
# 4. 可视化流程中可以通过"调用模块"的指令使用此模块

import xbot
import xbot_visual
from xbot_visual.web import get_cookies, set_cookie, remove_cookie
from xbot import print, sleep
from .import package
from .package import variables as glv
import datetime

import json
import re
import os
from dateutil import parser
from pydantic import BaseModel
from .backend_session import session


print = [ lambda *_, **__: None, print ][__package__ == "xbot_robot" or hasattr(xbot, "__log")]

SERVICE_DOMAIN = "https://misc-connector.yingdao.com"


class LoginCache(BaseModel):
    cookies: str
    localstorage: str

    url: str
    platform: str
    account: str


class CookieSerivce:

    def upload(platform: str, account: str, info_data: dict):
        """
        上传账号cookie信息
        """
        info_data.update({
            "platform": platform,
            "account": account
        })

        resp = session.post(
            f"{SERVICE_DOMAIN}/api/cookie-login-cache/",
            json=info_data,
            timeout=60 * 5
        )
        if resp.status_code != 200:
            print("上传cookie信息异常: ", resp.text)

    def get(platform: str, account: str):
        """
        获取cookie数据
        """
        resp = session.get(
            f"{SERVICE_DOMAIN}/api/cookie-login-cache/",
            params={
                "platform": platform,
                "account": account
            },
            timeout=60 * 5
        )
        if resp.status_code != 200:
            print("获取cookie信息异常: ", resp.text)
            return

        json_data = resp.json()

        if json_data["code"] != 0:
            print("cookie服务异常: ", json_data)
            return

        if not json_data["data"]:
            print("没有此账号的缓存cookie：", account)
            return

        return LoginCache(**json_data["data"])
    

def save_login_info(web_page, platform, account, partition_key=None):

    # 数据获取
    url = web_page.get_url()
    cookies = get_cookies(url_type="auto", browser=web_page, web_type=None, url=None, name=None, domain=None, path=None, filter_secure=False, secure=False, filter_session=False, session=False)
    if partition_key:
        try:
            _cookies = get_cookies(url_type="auto", browser=web_page, web_type=None, url=None, name=None, domain=None, path=None, filter_secure=False, secure=False, filter_session=False, session=False, partition_key=partition_key)
            cookies.extend(_cookies)
        except TypeError as e:
            pass
 
    for cookie in cookies:
        cookie['expires'] = None
        if cookie['expirationDate']:
            date_string = cookie['expirationDate']
            dt = parser.parse(date_string)
            # dt = datetime.datetime.strptime(dt, "%Y/%m/%d %H:%M:%S")       
            cookie['expires'] = int(datetime.datetime.timestamp(dt))
        cookie['sessionCookie'] = not bool(cookie['expires'])
        cookie.pop('expirationDate')

    local_storage = web_page.execute_javascript('''
        function (ele, input) {
            let local_storage = {}
            for (let i = 0; i < localStorage.length; i++) {
                let key = localStorage.key(i);
                let value = localStorage.getItem(key);
                local_storage[key] = value
            }
            if (Object.keys(local_storage).length == 0) {
                return null
            }
            return local_storage
        }    
    ''')
    local_storage = local_storage if local_storage else {}

    # 上传对象构建
    info_data = {
        "url": url,
        "cookies": json.dumps(cookies, ensure_ascii=False),
        "localstorage": json.dumps(local_storage, ensure_ascii=False)
    }

    # 上传
    CookieSerivce.upload(
        platform=platform,
        account=account,
        info_data=info_data
    )



def login(web_page, platform, account, add_localstorage):

    cache_data: LoginCache = CookieSerivce.get(
        platform=platform,
        account=account
    )

    if not cache_data:
        print("没有查询到云端缓存，请继续登录流程。")
        return False

    # 数据获取
    url = cache_data.url
    cookies = json.loads(cache_data.cookies)
    local_storage = json.loads(cache_data.localstorage)

    if "拼多多" in platform:
        # 2025-05-19: 增加离线添加cookie功能，防止注册cookie过程中的平台校验
        network_status_button = web_page.find_by_xpath("//div[@id='network-status-button']")
        network_status_button.click(simulative=False)

    try:
        web_page.navigate(url) 
        sleep(2)   
    except:
        pass

    # 设置cookie
    for cookie in cookies:        
        if cookie['name'] == "":
            continue
        try:
            xbot_visual.web.set_cookie(
                url_type="auto", 
                browser=web_page, 
                web_type="chrome", 
                url=url, 
                name=cookie["name"], 
                value=cookie["value"], 
                sessionCookie=cookie["sessionCookie"], 
                expires=cookie["expires"], 
                domain=cookie["domain"], 
                path=cookie["path"], 
                httpOnly=cookie["httpOnly"], 
                secure=cookie["secure"], 

                _block=("main", 4, "设置Cookie")
            )
            set_cookie(url_type="auto", browser=web_page, web_type="chrome", url=url, **cookie)
        except Exception as e:
            print("设置cookie异常：", e)

    # 设置localstorage
    if add_localstorage:
        for k, v in local_storage.items():
            try:
                if isinstance(v, str):
                    v = f'`{v}`'

                web_page.execute_javascript('''
                function (ele, input) {
                    localStorage.removeItem(`%s`);
                    localStorage.setItem(`%s`, %s);
                }
                ''' % (k, k, v))                
            except Exception as e:
                print(f'添加本地存储异常：【{k}】', e)
        
    # 2025-05-19: 网络离线后需要等待10s恢复网络
    if "拼多多" in platform:
        sleep(10)

    try:
        web_page.navigate(url, load_timeout=20)
    except:
        pass

    return True



def main(args):
    import os
    platform = "阿里妈妈"
    account = "南极人裤袜旗舰店:丁香"

    # web_page = xbot.web.get_active("chrome")
    # save_login_info(web_page, platform, account)

    web_page = xbot.web.get_active("chrome")
    login(web_page, platform, account, 0)

