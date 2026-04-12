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

import os
import json
import time

import psutil

from .init_chrome import set_profile_exit_type
from .G import global_dict
from .win_tools import is_live_window, active_foreground_window, unfreeze_window, foreground_window, record_activated_windows, hide_window_by_title
from .process14 import main as restart_extension_flow


# 常量声名
user_dir_path = os.path.expanduser("~")


def exists_window_handle(user_data_dir):
    # 获取此环境浏览器的window_handle
    window_handle_path = os.path.join(user_data_dir, "window_handle.json")
    if not os.path.exists(window_handle_path):
        return False
    
    with open(window_handle_path, "r", encoding='utf-8') as f:
        c = json.load(f)
        window_handle = c.get("window_handle")
    
    if is_live_window(window_handle):
        unfreeze_window(window_handle)
        return window_handle

    return False


def save_window_handle(user_data_dir, window_handle):
    # 获取此环境浏览器的window_handle
    window_handle_path = os.path.join(user_data_dir, "window_handle.json")

    with open(window_handle_path, "w", encoding='utf-8') as f:
        json.dump(
            {
                "window_handle": window_handle,
                "time": time.strftime("%Y-%m-%d %H:%M:%S")
            }, f
        )


def load_extensions():
    base_dir_name = "connector_extensions_v9"
    extension_base_dir = os.path.join(os.path.expanduser("~"), "CHROME", "Extensions", base_dir_name)
    if not os.path.exists(extension_base_dir):
        extension_zip = xbot_visual.resourcesfile.get_resourcesfile_path(file_name="connector_extensions.7z", _block=("创建环境隔离浏览器", 4, "获取资源文件路径"))
        _ = xbot_visual.xzip.unzip(zip_file_path=extension_zip, password=xbot_visual.decrypt(""), unzip_dir_path=lambda: extension_base_dir, create_dedicated_folder=False, _block=("创建环境隔离浏览器", 5, "解压文件/文件夹"))
    
    return ",".join(
        os.path.join(extension_base_dir, f)
        for f in os.listdir(extension_base_dir)
    )


def double_check_window_handle(handle):
    active_window = foreground_window()
    if active_window != handle:
        raise Exception(f"窗口校验失败，当前激活窗口: {active_window}  目标窗口: {handle}")


def replace_char(s):
    replace_char = [r":", "\\", "/", ":", "*", "?", '"', "<", ">", "|", " "]
    s = s.strip()
    if any(char in s for char in replace_char):
        for char in replace_char:
            s = s.replace(char, "_")
    return s


def active_extension():
    # 激活当前网页的影刀插件
    # 激活/获取web_page
    web_page = None
    err = None
    for i in range(5):
        try:
            web_page = xbot_visual.web.get(web_type="chrome", mode="activated", value="", use_wildcard=False, silent_running=False, wait_load_completed=False, load_timeout="20", stop_load_if_load_timeout="handleExcept", open_page=False, url=None, _block=("EnvChrome", 2, "获取已打开的网页对象"))
            break
        except Exception as e:
            print(f"激活插件异常[自动重试:{i}]: {e}")
            err = e
            restart_extension_flow({"first_run": False})
    else:
        if err is not None:
            from .process16 import main as close_actived_window
            close_actived_window({})
            raise err
        if web_page is None:
            raise Exception("激活窗口插件超出最大失败次数。")

    return web_page


# 创建环境隔离浏览器
def create_web_page(url, platform, account, zoom="75",**kwargs):
    # 启动前隐藏所有已开启的chrome窗口
    hide_window_by_title("Chrome")

    # 账户名处理，替换掉账户名里面的特殊字符
    account = replace_char(account)
    



    # 路径获取
    user_data_path = os.path.join(user_dir_path, "CHROME", "USER_DATA")
    if not os.path.exists(user_data_path):
        os.makedirs(user_data_path)

    company_name = replace_char(global_dict.get("task_configs", {}).get("company_name") or "UndefindCompany")

    company_data_dir = os.path.join(user_data_path, company_name) 

    profile_dir_name = f"{platform}_{account}"


    profile_dir = os.path.join(company_data_dir, profile_dir_name)

    # 传出chrome地址
    global_dict['env_chrome_path'] = profile_dir

    # 启动
    chrome_exe = os.path.join(os.path.expanduser("~"), "AppData\Local\Google\Chrome\Application\chrome.exe")
    if not os.path.exists(chrome_exe):
        chrome_exe = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

    # 启动参数配置
    # performance_optimization = '--process-per-site --disable-dev-shm-usage --js-flags="--max-old-space-size=2048" --disk-cache-size=104857600'
    # gc_params = "--enable-aggressive-domstorage-flushing --enable-memory-coordinator" 
    # render = "--enable-gpu-rasterization --enable-zero-copy --disable-gpu-vsync --disable-renderer-backgrounding --disable-background-timer-throttling"

    # 原始参数
    performance_optimization = "--in-process-plugins"
    gc_params = ""
    render = ""
    disable_features = "DownloadAutoOpen,ChromeUpdateService,PasswordManagerUI"
    start_params = f'--user-data-dir={company_data_dir} --profile-directory="{profile_dir_name}" {performance_optimization} {render} {gc_params} --allow-outdated-plugins --load-extension={load_extensions()} --disable-features={disable_features} --disable-popup-blocking --start-maximized  --no-first-run --disable-signin-screen --silent-debugger-extension-api'
    start_html_path = xbot_visual.resourcesfile.get_resourcesfile_path(file_name="start.html", _block=("main", 3, "获取资源文件路径"))

    if not os.path.exists(profile_dir):
        # 首次初始化，初始化目录后重启浏览器
        os.makedirs(profile_dir)
        # 启动新环境: 启动浏览器，生成配置文件，随后关闭浏览器，更新配置文件，再次重启
        xbot_visual.system.terminal_process(terminal_way="name", process_id=None, process_name="ShadowBot.ChromeBridge.exe", _block=("启用影刀插件", 1, "终止程序"))
        xbot_visual.system.run_or_open(application_path=lambda: f'"{chrome_exe}" {start_params} "{start_html_path}"', command_line_arguments="", working_folder=None, after_application_launch="wait_to_mainwindow", is_waitexit_not_more_than=False, timeout_for_exit="10", is_waithwnd_not_more_than=True, timeout_for_hwnd="5", start_as_admin=False, window_style="normal", _block=("EnvChrome", 5, "启动命令"))
        restart_extension_flow({"first_run": True})
        w = active_extension()

        xbot_visual.web.browser.close(operation="close_specified", browser=w, web_type="chrome", task_kill=False, _block=("创建环境隔离浏览器", 17, "关闭网页"))
        sleep(2)
        return create_web_page(url, platform, account)

    else:
        # 设置启动状态，删除chrome弹窗
        # 2025-06-12：支持设置chrome缩放
        set_profile_exit_type(profile_dir, zoom)

    # window_handle
    window_handle = exists_window_handle(profile_dir)

    if not window_handle:
        
        process = xbot_visual.system.run_or_open(application_path=lambda: f'"{chrome_exe}" {start_params} "{start_html_path}"', command_line_arguments="", working_folder=None, after_application_launch="wait_to_mainwindow", is_waitexit_not_more_than=False, timeout_for_exit="10", is_waithwnd_not_more_than=True, timeout_for_hwnd="5", start_as_admin=False, window_style="normal", _block=("EnvChrome", 5, "启动命令"))

        # 比例缩放不能开，影刀模拟人工点击会出异常
        # --force-device-scale-factor=1

        # 保存激活的窗口句柄
        window_handle = process.main_window_handle
        print(f"开启新窗口: {window_handle}")

        if window_handle == -1:
            # 主窗口存在且未记录，无法查找目标窗口，为防止 kill所有chrome.exe 
            # os.system('taskkill /im chrome.exe /F')
            # raise Exception("主窗口存在且未记录，无法查找目标窗口, 关闭已开启的所有chrome, 请重启此任务!")

            # 查找当前激活窗口不受控制，可能导致账号间串数
            window_handle = foreground_window()
            print(f"主进程未关闭，获取到当前激活的窗口句柄：{window_handle}")
            
        # 激活窗口
        active_foreground_window(window_handle)

    print(f"当前任务操作窗口句柄: {window_handle}")

    # 保留window_handle后续冻结使用
    global_dict['window_handle'] = window_handle

    # 2024-11-26: 新增功能
    # 关闭所有 ShadowBot.ChromeBridge.exe
    # xbot_visual.system.terminal_process(terminal_way="name", process_id=None, process_name="ShadowBot.ChromeBridge.exe", _block=("EnvChrome", 8, "Kill"))
    # 重启插件
    restart_extension_flow({"first_run": True})

    # 激活/获取web_page
    web_page = active_extension()
    
    try:
        web_page.navigate(url)
    except Exception as e:
        print(f"[忽略异常]跳转到url等待加载超时：{url}")
    
    # 校验当前激活窗口是否为目标窗口
    double_check_window_handle(window_handle)

    # 保存更新
    save_window_handle(profile_dir, window_handle)

    # 不进行保活的平台
    NOT_KEEP_LIVE_PLATFORM, _, _ = xbot_visual.asset.get_asset(asset_name="NOT_KEEP_LIVE_PLATFORM", asset_type="txt", encrypt_flag="0", _block=("FeishuBase", 1, "获取资产"))
    # 非抖店账号 保活限制校验
    if platform in str(NOT_KEEP_LIVE_PLATFORM):  # XXX为不包含平台名称， 抖店
        global_dict['close_this_window'] = True
    else:
        record_activated_windows(window_handle, platform, account)

    return web_page


def main(args):
    web_page = create_web_page(**args)
    args["web_page"] = web_page
