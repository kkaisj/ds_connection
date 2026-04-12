# 使用提醒:
# 1. xbot包提供软件自动化、数据表格、Excel、日志、AI等功能
# 2. package包提供访问当前应用数据的功能，如获取元素、访问全局变量、获取资源文件等功能
# 3. 当此模块作为流程独立运行时执行main函数
# 4. 可视化流程中可以通过"调用模块"的指令使用此模块

import xbot
from xbot import print, sleep
from .import package
from .package import variables as glv

import os, json


def set_profile_exit_type(run_user_data_dir="", zoom="75"):
    """
    用途:修改chrome的Preferences文件，清除chrome被终止进程后的恢复页面弹窗
    该函数必须在谷歌进程确认关闭的清空下调用！！！
    chrome安装路径必须是默认安装且未修改配置文件路径！！！
    """
    # 获取指定缩放比的zoom_level
    zoom_level_x = {
        "50": -3.8017840169239308,
        "75": -1.5778829311823859,
        "100": 0.0
    }.get(zoom, 0.0)


    print("开始修改chrome的Preferences文件")

    if not run_user_data_dir:
        file_path = os.path.join(os.environ['LOCALAPPDATA'], r'Google\Chrome\User Data\Default\Preferences')
    else:
        file_path = os.path.join(run_user_data_dir, 'Preferences')

    try:
         with open(file_path, 'r+', encoding='utf-8') as f:
            # 读取文件内容
            chrome_pre_json = json.load(f)
            
            # 修改默认下载文件位置到当前用户目录
            default_save_dir = os.path.join(os.path.expanduser("~"), "Downloads")
            print(f"设置默认下载路径: {default_save_dir}")

            chrome_pre_json["download"] = {
                "prompt_for_download": False,
                "default_directory": default_save_dir
            }

            chrome_pre_json["savefile"] = {
                "default_directory": default_save_dir
            }

            # 关闭下载完成后显示文件
            chrome_pre_json["download_bubble"] = {
                "partial_view_enabled": False,
                "partial_view_impressions": 6
            }

            chrome_pre_json['partition'] = {
                "default_zoom_level": {
                    "x": zoom_level_x
                },
                "per_host_zoom_levels": {
                    "x": {}
                }
            }

            # 修改chrome退出类型
            if "profile" not in chrome_pre_json:
                chrome_pre_json['profile'] = {}

            chrome_pre_json["profile"]["exit_type"] = "Normal"

            # 允许弹窗和重定向
            chrome_pre_json["profile"]["default_content_setting_values"] = {
                "popups": 1
            }

            # 禁用密码管理器
            chrome_pre_json["password_manager"] = {
                "autofillable_credentials_account_store_login_database": False,
                "autofillable_credentials_profile_store_login_database": False,
                "password_promo_cards_list": [
                    {
                        "id": "password_checkup_promo",
                        "last_time_shown": "0",
                        "number_of_times_shown": 0,
                        "was_dismissed": False
                    },
                    {
                        "id": "passwords_on_web_promo",
                        "last_time_shown": "0",
                        "number_of_times_shown": 0,
                        "was_dismissed": False
                    },
                    {
                        "id": "password_shortcut_promo",
                        "last_time_shown": "13386843019157930",
                        "number_of_times_shown": 1,
                        "was_dismissed": False
                    },
                    {
                        "id": "access_on_any_device_promo",
                        "last_time_shown": "0",
                        "number_of_times_shown": 0,
                        "was_dismissed": False
                    },
                    {
                        "id": "move_passwords_promo",
                        "last_time_shown": "0",
                        "number_of_times_shown": 0,
                        "was_dismissed": False
                    }
                ]
            }
            
            chrome_pre_json["credentials_enable_autosignin"] = False
            chrome_pre_json["credentials_enable_service"] = False

            # 将文件指针移回文件的开头
            f.seek(0)
            
            # 写入修改后的数据
            json.dump(chrome_pre_json, f)
            
            # 清除文件的其余部分（如果有的话）
            f.truncate()
    except Exception as e:
        # Preferences文件可能为只读状态,取消只读即可
        print("存在异常，chrome配置文件重置失败:",e)
        return

    print("chrome配置文件重置完成.")




def main(a):
    set_profile_exit_type(r"C:\Users\HeXia\CHROME\USER_DATA\阿里妈妈_4")
