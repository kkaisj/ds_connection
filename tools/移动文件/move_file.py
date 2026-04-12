# 使用提醒:
# 1. xbot包提供软件自动化、数据表格、Excel、日志、AI等功能
# 2. package包提供访问当前应用数据的功能，如获取元素、访问全局变量、获取资源文件等功能
# 3. 当此模块作为流程独立运行时执行main函数
# 4. 可视化流程中可以通过"调用模块"的指令使用此模块

import xbot
from xbot import print, sleep
from .import package
from .package import variables as glv
import time, os,  shutil


def clean_string(s):
    l = [":", "*", "?", "'", '"', "<", ">", "|"]
    for i in l:
        s = s.replace(i, "_")
    return s
    

def main(args):
    根目录 = args.get("根目录")
    主平台 = clean_string(args.get("主平台"))
    多级层级 = clean_string(args.get("多级层级"))
    店铺名 = clean_string(args.get("店铺名"))
    # 数据集 = clean_string(args.get("数据集"))

    处理后或原文件 = args.get("处理后或原文件")
    是否重试 = args.get("是否重试")
    file_path = args.get("file_path")

    today = time.strftime("%Y-%m-%d")
    t_year = time.strftime("%Y")
    if 是否重试:
        today = f"重试记录\\{today}"

    # other_list = args.get("其他层级")
    # other_floor = "\\".join(other_list) if other_list  else ""
    

    dir_path = f"{根目录}\\{处理后或原文件}\\{主平台}\\{多级层级}\\{店铺名}\\{t_year}年\\{today}"

    print(f"创建目录:{dir_path}")
    
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

    new_file_path = dir_path + "\\" + os.path.basename(file_path)

    # 可能存在PermissionError不确定原因
    # shutil.move(file_path, new_file_path)

    shutil.copy2(file_path, new_file_path)
    
    try:
        os.remove(file_path)
    except:
        print("删除文件失败！")
        
    args["新路径"] = new_file_path
