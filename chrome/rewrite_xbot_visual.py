# 使用提醒:
# 1. xbot包提供软件自动化、数据表格、Excel、日志、AI等功能
# 2. package包提供访问当前应用数据的功能，如获取元素、访问全局变量、获取资源文件等功能
# 3. 当此模块作为流程独立运行时执行main函数
# 4. 可视化流程中可以通过"调用模块"的指令使用此模块

import xbot
from xbot import print, sleep
from .import package
from .package import variables as glv

import xbot_visual

from functools import wraps


def regiest_default_browser(browser: str):
    print(f"已重写【打开网页】: 仅支持{browser}; 禁用运行时不抢占键鼠")

    def browser_wrap(func):

        @wraps(func)
        def warp(*args, **kwargs):

            kwargs["web_type"] = browser
            kwargs["silent_running"] = False

            return func(*args, **kwargs)

        return warp

    return browser_wrap



def rewrite_browser_close(func):

    @wraps(func)
    def warp(*args, **kwargs):
        kwargs["task_kill"] = False

        if kwargs.get("operation") == "close_all":
            print("连接器组织内部应用不允许调用关闭所有浏览器进程.")
            return
        
        # 检查当前激活的web_page数量，少于1个不允许关闭
        web_page_list = xbot_visual.web.get_all(web_type="chrome", mode="all", value="", use_wildcard=False, _block=("CloseWebPage", 1, "获取网页对象列表"))
        if len(web_page_list) <= 1:
            print("已是最后一个web_page， 跳过关闭动作。")
            return

        return func(*args, **kwargs)

    return warp


def rewrite_xbot_visual_web_close():
    print("已重写【关闭网页】: 不允许关闭所有浏览器")
    temp_func = xbot_visual.web.browser.close
    xbot_visual.web.browser.close = rewrite_browser_close(temp_func)


def rewrite_browser_get(func):

    @wraps(func)
    def warp(*args, **kwargs):
        kwargs["silent_running"] = False
        return func(*args, **kwargs)

    return warp


def rewrite_xbot_visual_web_get():
    print("已重写【获取已打开的网页对象】: 禁用运行时不抢占键鼠")
    temp_func = xbot_visual.web.get
    xbot_visual.web.get = rewrite_browser_get(temp_func)



def main(args):
    # rewrite_xbot_visual_web_close()
    rewrite_xbot_visual_web_get()

    # 重新默认浏览器
    create_temp_func = xbot_visual.web.create
    xbot_visual.web.create = regiest_default_browser("chrome")(create_temp_func)
