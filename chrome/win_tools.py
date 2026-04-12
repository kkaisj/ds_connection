# 使用提醒:
# 1. xbot包提供软件自动化、数据表格、Excel、日志、AI等功能
# 2. package包提供访问当前应用数据的功能，如获取元素、访问全局变量、获取资源文件等功能
# 3. 当此模块作为流程独立运行时执行main函数
# 4. 可视化流程中可以通过"调用模块"的指令使用此模块

import xbot
from xbot import print, sleep
from .import package
from .package import variables as glv

import os
import json
import time

import psutil
import win32con
import win32gui
import win32api
import win32process
import win32com.client

import xbot_visual

from .process15 import main as close_other_page
from .G import global_dict

pssuspend_path = xbot_visual.resourcesfile.get_resourcesfile_path(file_name="pssuspend64.exe", _block=("main", 9, "获取资源文件路径"))


def get_all_windows():
    """
    获取所有窗口句柄
    :return:
    """
    hwnd_list = []
    win32gui.EnumWindows(lambda hwnd, param: param.append(hwnd), hwnd_list)
    return hwnd_list


def get_cls_name(hwnd):
    return win32gui.GetClassName(hwnd)


def get_title(hwnd):
    return win32gui.GetWindowText(hwnd)


def show_window(handle: int):
    """
    显示窗口 托盘都找不到
    :param handle: 窗口句柄
    :return:
    """
    # win32gui.ShowWindow(handle, win32con.SW_SHOW)
    # win32gui.ShowWindow(handle, win32con.SW_SHOWNOACTIVATE)
    win32gui.ShowWindow(handle, win32con.SW_MAXIMIZE)


def hide_window(handle: int = None):
    """
    隐藏窗口 托盘都找不到
    :param handle: 窗口句柄
    :return:
    """
    # print(f"隐藏窗口: {handle}")
    win32gui.ShowWindow(handle, win32con.SW_HIDE)


def is_live_window(handle: int):
    """
    句柄是否有效
    :param handle:
    :return:
    """
    try:
        get_cls_name(handle)
        title = get_title(handle)
        print(f"[句柄查找]窗口存在: {handle} - {title}")
        return True
    except Exception:
        print(f"[句柄查找]窗口不存在: {handle}")
        return False


def foreground_window():
    """
    当前激活窗口的句柄
    :return:
    """
    return win32gui.GetForegroundWindow()


def active_foreground_window(handle: int):
    """
    激活为前台窗口
    :param handle:
    :return:
    """
    show_window(handle)

    for i in range(3):
        try:
            win32gui.BringWindowToTop(handle)
            win32gui.SetActiveWindow(handle)

            shell = win32com.client.Dispatch("WScript.Shell")
            shell.SendKeys('%')  # 模拟Alt键
            win32gui.SetForegroundWindow(handle)
            return
        except Exception as e:
            print(f"激活窗口失败: 句柄-{handle} 【{e}】")

    xbot_visual.win32.click_mouse(is_move_mouse_before_click=True, point_x="100", point_y="5", relative_to="screen", move_speed="middle", button="left", click_type="click", hardware_driver_click=False, keys="null", delay_after="1", _block=("winTool", 4, "clickTopLift"))
        

def get_process_id_by_window_handle(handle):
    """
    根据窗口句柄获取进程ID
    :param handle:
    :return:
    """
    app = win32gui.GetWindowText(handle)
    thread_id, process_id = win32process.GetWindowThreadProcessId(handle)
    process = psutil.Process(process_id)
    return process_id, process.name()


def freeze(pid):
    """
    冻结进程
    :param pid:
    :return:
    """
    pass
    # os.system(f"{pssuspend_path} -accepteula {pid}")

    # print(f"Freeze Pid: {pid}")


def unfreeze(pid):
    """
    冻结进程
    :param pid:
    :return:
    """
    os.system(f"{pssuspend_path} -r -accepteula {pid}")


def freeze_window(window_handle: int):
    """
    冻结进程及其子进程
    :param window_handle: 窗口句柄
    :return:
    """
    # 2025-05-20： 停用页面保活
    return 

    # 检查已冻结窗口数量，如果超过指定数量，杀死一个旧的冻结窗口

    close_other_page({})

    # 校验窗口并获取进程ID
    pid, pname = get_process_id_by_window_handle(window_handle)

    print(f"Freeze window : {pname}")

    if pname != "chrome.exe":
        raise Exception(f"冻结窗口目标非chrome: {pname} ")

    # 关闭特定窗口
    if global_dict.get('close_this_window'):
        print("此窗口被指定关闭！")
        close_window(window_handle)
    else:
        # 隐藏窗口
        hide_window(window_handle)

    # 冻结主进程
    # freeze(pid)

    # 取消冻结子进程
    # 获取当前进程的所有子进程
    # children = psutil.Process(pid).children()

    # # 冻结子进程
    # for child in children:
    #     freeze(child.pid)


def unfreeze_window(window_handle: int):
    """
    解冻进程及其子进程
    :param window_handle: 窗口句柄
    :return:
    """
    pid, pname = get_process_id_by_window_handle(window_handle)

    print(f"UnFreeze window: {pname}")

    # 解冻主进程
    unfreeze(pid)

    # 获取当前进程的所有子进程
    # children = psutil.Process(pid).children()

    # 解冻子进程
    # for child in children:
    #     unfreeze(child.pid)

    # 激活窗口
    active_foreground_window(window_handle)


def get_screen_resolution():
    # 获取屏幕的宽度
    screen_width = win32api.GetSystemMetrics(0)
    # 获取屏幕的高度
    screen_height = win32api.GetSystemMetrics(1)
    print(f"当前屏幕分辨率为: {screen_width} x {screen_height}")
    return screen_width, screen_height


def close_window(handle):
    # 关闭窗口
    if not is_live_window(handle):
        print("窗口不存在, 无法关闭.")
        return

    # unfreeze_window(handle)
    print(f"关闭窗口: {handle}")
    win32api.PostMessage(handle, win32con.WM_CLOSE, 0, 0)


# 常量声名
ACTIVATED_WINDOW_MAX_COUNT = 10

def record_activated_windows(handle, platform, account):
    record_file = os.path.join(os.path.expanduser("~"),"CHROME", "USER_DATA", "activated_windows.json")

    add_window = {
        "platform": platform,
        "account": account,
        "window_handle": handle,
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "keep_alive": "【保活】" in global_dict.get("task_configs", {}).get("remark", "")
    }

    # 首次记录
    if not os.path.exists(record_file):
        with open(record_file, "w", encoding="utf-8") as f:
            json.dump(
                [
                   add_window 
                ],
                f,
                ensure_ascii=False
            )       
            print(f"窗口记录完成: {add_window}")
            return

    # 追加记录
    with open(record_file, "r+", encoding="utf-8") as f:
        
        activated_windows = json.load(f)

        # 检查是否为已记录的窗口
        for i, item in enumerate(activated_windows):
            # 1. 此账号已被记录且句柄相同，更新时间后退出
            if item['platform'] == platform and item['account'] == account:
                # 2. 此账号被记录但句柄不同，尝试关闭旧窗口后记录新窗口
                if item['window_handle'] != handle:
                    print(f"已存在记录但不一致，尝试关闭记录旧窗口: {item}")
                    close_window(item['window_handle'])
                    item['window_handle'] = handle

                item['time'] = time.strftime("%Y-%m-%d %H:%M:%S")
                f.seek(0)
                json.dump(activated_windows, f, ensure_ascii=False)
                f.truncate()
                print(f"窗口记录完成: {item}")
                return

        
        # 4. 检查是否达到记录上限，达到上限后不再保活新窗口
        if len(activated_windows) >= ACTIVATED_WINDOW_MAX_COUNT and not add_window.get("keep_alive"):
            print(f"达到上限,放弃保活此窗口: {add_window}")
            global_dict['close_this_window'] = True
            return
        else:
            # 3. 没有被记录，添加新记录 | 配置保活的窗口
            activated_windows.append(
                add_window
            )

        # =====================================================
        # if len(activated_windows) > ACTIVATED_WINDOW_MAX_COUNT:
            # activated_windows.sort(key=lambda x: x['time'])

            # earliest_window = next((item for item in activated_windows if not item.get("keep_alive")), None)

            # if earliest_window is not None:
            #     print(f"本机冻结窗口达到上限[{ACTIVATED_WINDOW_MAX_COUNT}]: 关闭 {earliest_window}")
            #     close_window(earliest_window['window_handle'])
            #     activated_windows.remove(earliest_window)
        # =====================================================

        f.seek(0)
        json.dump(activated_windows, f, ensure_ascii=False)
        f.truncate()

        print(f"窗口记录完成: {add_window}")


def hide_window_by_title(t):
    all_window = get_all_windows()
    for hw in all_window:
        title = get_title(hw)
        if t in title:
            hide_window(hw)
            print(f"hide: {title}-{hw}")


def show_window_by_title(t):
    all_window = get_all_windows()
    for hw in all_window:
        title = get_title(hw)
        if t in title:
            show_window(hw)
            print(f"show: {title}-{hw}")

