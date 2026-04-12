# 使用提醒:
# 1. xbot包提供软件自动化、数据表格、Excel、日志、AI等功能
# 2. package包提供访问当前应用数据的功能，如获取元素、访问全局变量、获取资源文件等功能
# 3. 当此模块作为流程独立运行时执行main函数
# 4. 可视化流程中可以通过"调用模块"的指令使用此模块
from __future__ import annotations

import xbot
from xbot import print, sleep
from .import package
from .package import variables as glv

import contextlib
import os.path
import platform
import contextlib
import re

from openpyxl.utils.exceptions import IllegalCharacterError
import pandas as pd
from pandas.core.dtypes.common import is_string_dtype

from xbot_extensions.activity_ljq_global.G import global_dict
from .Tools import match_dtypes, match_reader


os_name = platform.platform().split("-")[0]
print(f"当前系统环境 >>> {os_name}")
EXC_ORDER = "set PYTHONUTF8=1" if os_name == "Windows" else "export PYTHONUTF8=1"
os.system(EXC_ORDER)

import logging


def clean_illegal_chars(value):
    """彻底移除 openpyxl 不允许的控制字符"""
    if not isinstance(value, str):
        return value
    
    # 备选正则写法（效果相同，更直观）
    cleaned = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', value)   #加了一个x7F
    return cleaned


def _save_excel_in_chunks(df: pd.DataFrame, save_path: str, chunk_size: int = 10000):
    """
    分批写入Excel文件以避免内存溢出
    :param df: 要保存的DataFrame
    :param save_path: 保存路径
    :param chunk_size: 每批写入的行数
    """
    from openpyxl import Workbook
    from openpyxl.utils.dataframe import dataframe_to_rows
    
    print(f"开始分批写入Excel，总行数：{len(df)}，每批：{chunk_size}行")
    
    wb = Workbook(write_only=True)
    ws = wb.create_sheet()
    
    # 写入表头
    ws.append(list(df.columns))
    
    # 分批写入数据
    total_rows = len(df)
    for start_idx in range(0, total_rows, chunk_size):
        end_idx = min(start_idx + chunk_size, total_rows)
        chunk_df = df.iloc[start_idx:end_idx]
        
        # 将DataFrame转换为行并写入
        for row in dataframe_to_rows(chunk_df, index=False, header=False):
            normalized_row = [
                cell.strftime("%Y-%m-%d %H:%M:%S") if isinstance(cell, pd.Timestamp) else cell
                for cell in row
            ]

            try:
                ws.append(normalized_row)
            except IllegalCharacterError as e:
                print(f"Error row: {row}")
                # 可选：清理该行并重试
                cleaned_row = [clean_illegal_chars(cell) for cell in normalized_row]
                print(f"clean row: {cleaned_row}")
                ws.append(cleaned_row)

        print(f"已写入 {end_idx}/{total_rows} 行 ({end_idx*100//total_rows}%)")
    
    wb.save(save_path)
    print(f"Excel文件保存成功：{save_path}")


def append_column(
        path: str, 
        column_list: list, 
        value_list: list, 
        is_add_timestamp: bool=True, 
        drop_old_file: bool=False, 
        calculated_fields:list | None=None,
        is_clean_chars: bool=True, 
        **kwargs
):
    """
    向excel/csv文件最后追加N列
    :param path: 文件路径【相对路径或绝对路径】
    :param column_list: 新增字段名列表
    :param value_list: 新增数据列表
    :param is_add_timestamp: 添加时间戳
    :param drop_old_file: 删除旧文件
    :param calculated_fields: 增加计算字段
    :param is_clean_chars:是否清洗额外字符
    :param kwargs: 
    :return: 
    """
    if len(column_list) != len(value_list):
        raise AttributeError(
            f"字段列表长度和数据列表长度不相同！column_len:{len(column_list)}, value_len:{len(value_list)}")

    file_type = os.path.splitext(path)[-1].lower()
    if file_type not in [".xlsx", ".xls", ".csv"]:
        raise AttributeError(f"文件类型错误，只支持excel和csv，当前文件类型：{file_type}")

    print(f"插入字段: {column_list} -> {value_list}")
    save_path = os.path.splitext(path)[0] + "_new.xlsx"

    try:
        dtypes = match_dtypes(path, **kwargs)

        reader = match_reader(path)

        df = reader(path, dtype=dtypes, **kwargs)

    except pd.errors.EmptyDataError:
        # 如果发生EmptyDataError异常，说明文件为空
        logging.info("待处理csv文件为空, 已退出流程")
        pd.DataFrame().to_excel(save_path, index=False, encoding="utf-8")
        return save_path

    if df.empty:
        print("插入字段：待处理文件为空；已退出流程;")
        df.to_excel(save_path, index=False, encoding="utf-8")
        return save_path

    # 2025-12-28：检查字段是否已存在，已存在不允许插入
    exists_columns = set(column_list).intersection(set(df.columns))
    if exists_columns:
        raise AttributeError(
            f"插入字段原文件中已存在，不能插入和源文件相同的字段: {exists_columns}"
        )

    # 删除Unnamed字段
    df = df[[column for column in df.columns if "Unnamed" not in column]]

    # 删除列名中的引号
    df.columns = [col.replace("'", "").strip() for col in df.columns]

    # 清除nan值
    df.fillna("", inplace=True)

    # 清理csv非法字符
    if path.endswith(".csv"):
        string_cols = df.select_dtypes(include=['object', 'string']).columns
        df[string_cols] = df[string_cols].apply(lambda col: col.map(clean_illegal_chars))

    if is_clean_chars:
        # 删除掉千分符
        for col in df.columns:
            if is_string_dtype(df[col]):
                with contextlib.suppress(Exception):
                    df[col] = df[col].map(lambda x: str(x).replace(",", "").replace("'","").strip())

    # 插入shopCode
    shop_code = global_dict.get("task_configs", {}).get("shop_code")
    if shop_code:
        df["RPA店铺ID"] = shop_code

    # 插入taskId
    task_id = global_dict.get("extraJson", {}).get("taskId")
    if task_id:
        df["dc_task_id"] = str(task_id)

    # 新增字段
    for idx, colum in enumerate(column_list):
        df[colum] = value_list[idx]

    # 新增计算字段
    if calculated_fields:
        for calculate in calculated_fields:
            
            # 找出需要进行计算的字段，然后转换为数值类型
            _fields = calculate.split("=")[-1].replace("+", " ").replace("-", " ").replace("*", " ").replace("/", " ")
            to_numeric_columns = [i.strip() for i in _fields.split() if not i.strip().isnumeric()]
            print(to_numeric_columns)

            for col in to_numeric_columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
             
            try:
                df.eval(calculate, inplace=True)
            except Exception as e:
                print(f"增加计算字段异常: {calculate}")
                raise e

    # 追加时间戳
    if is_add_timestamp:
        import time
        df["时间戳"] = time.strftime("%Y-%m-%d %H:%M:%S")
    
    # 插入当前取数应用名称
    company_id = global_dict.get("task_configs", {}).get("company_id")
    if str(company_id) != '721600107864231936':
        current_app_name = global_dict.get("task_configs", {}).get("current_app_name")
        if current_app_name:
            df["RPA应用名称"] = current_app_name

    # 小于100W条数据保存为xlsx，高于这个值保存为csv
    if df.shape[0] < 1000000:
        save_path = os.path.splitext(path)[0] + "_new.xlsx"
        _save_excel_in_chunks(df, save_path, chunk_size=10000)
    else:
        save_path = os.path.splitext(path)[0] + "_new.csv"
        df.to_csv(save_path, index=False, encoding="utf-8-sig")

    # 判断以下是否覆盖了原文件，没有就把原文件删掉
    if drop_old_file:
        if save_path != path:
            os.remove(path)

    return save_path



def main(args):
    file_path = args.get("文件路径")
    columns_list = args.get("字段名列表")
    value_list = args.get("值列表")
    is_add_timestamp = args.get("插入时间戳")
    kwargs = args.get("kwargs")
    drop_old_file = args.get("删除原文件")
    calculated_fields = args.get("新增计算字段")
    is_clean_chars = args.get("是否清洗额外字符", True)

    args["文件保存路径"] = append_column(file_path, columns_list, value_list, is_add_timestamp, drop_old_file,calculated_fields, is_clean_chars, **kwargs)

    