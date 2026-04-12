# 使用提醒:
# 1. xbot包提供软件自动化、数据表格、Excel、日志、AI等功能
# 2. package包提供访问当前应用数据的功能，如获取元素、访问全局变量、获取资源文件等功能
# 3. 当此模块作为流程独立运行时执行main函数
# 4. 可视化流程中可以通过"调用模块"的指令使用此模块

import xbot
from xbot import print, sleep
from .import package
from .package import variables as glv
from pandas.core.dtypes.common import is_float_dtype, is_integer_dtype
import os
import pandas as pd
import contextlib


def is_xls_file(file_path):
    return os.path.splitext(file_path)[-1] == ".xls"

def is_csv_file(file_path):
    return os.path.splitext(file_path)[-1] == ".csv"


def match_reader(file_path):
    # 根据文件类型匹配对应的pandas读取方法

    file_type = os.path.splitext(file_path)[-1].lower()
    if file_type not in [".xlsx", ".xls", ".csv"]:
        raise TypeError(f"文件类型错误，只支持excel和csv，当前文件类型：{file_type}")

    return {
        ".xlsx": pd.read_excel,
        ".xls": pd.read_excel,
        ".csv": read_csv,
    }.get(file_type)



def series_max_length(series):
    # 获取int和float类型字段的最大长度

    max_len = 0
    for item in series:
        if len(str(item)) > max_len:
            max_len = len(str(item))
    return max_len


def match_dtypes(file_path, **kwargs):
    #匹配当前文件的列类型，处理超过10位的整数和小数

    reader = match_reader(file_path)
    # 某些情况nrows与skipfooter冲突
    if "skipfooter" not in kwargs:
        kwargs['nrows'] = 100
    df = reader(file_path, **kwargs)

    dtypes_map = {}

    for column in df.columns:
        series = df[column]
        if is_float_dtype(series) or is_integer_dtype(series):
            if series_max_length(series) > 8:
                dtypes_map[column] = object
            elif is_float_dtype(series): # 2025-11-07 float转str
                dtypes_map[column] = str

    return dtypes_map


def read_csv(file_path, **kwargs):
    import csv
    
    # csv文件存在encoding异常，需要兼容
    try_encoding = ["utf-8", "utf-8-sig", "gbk", "gb2312", "gb18030", "latin1"]
    for encoding in try_encoding:
        with contextlib.suppress(UnicodeDecodeError):
            return pd.read_csv(file_path, encoding=encoding, **kwargs)
    raise Exception("读取csv文件异常，尝试所有编码仍未正确解析文件. ")


def read_excel(file_path, **kwargs):
    return pd.read_excel(file_path, dtype=match_dtypes(file_path, **kwargs), **kwargs)
    