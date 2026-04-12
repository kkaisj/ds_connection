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


def writer_to_databook(data):
    """
    数据保存到数据表格
    """

    columns, values = [], []

    for line in data:
        if not columns:
            columns = list(line.keys())

        l = []
        for k, v in line.items():
            l.insert(columns.index(k), v)

        values.append(l)

    xbot_visual.programing.databook.write_data_to_workbook(write_range="row", write_way="append", write_column_way="override", row_num="1", column_name="", begin_row_num="1", begin_column_name="A", content=lambda: columns, _block=("main", 1, "写入内容至数据表格"))
    xbot_visual.programing.databook.write_data_to_workbook(write_range="area", write_way="append", write_column_way="override", row_num="2", column_name="A", begin_row_num="1", begin_column_name="", content=lambda: values, _block=("main", 11, "写入内容至数据表格"))
    

def main(args):
    is_clear = args.get("自动清空")
    if is_clear:
        xbot_visual.programing.databook.remove_all_rows()

    data = args.get("data")
    writer_to_databook(data)

    folder_path = args.get("保存文件夹路径")
    file_name = args.get("文件名")
    
    file_name = file_name.replace("'","").replace("/","").replace("\\","")

    args["文件路径"] = xbot_visual.programing.databook.export_data(folder_source="custom", custom_folder_path=folder_path, file_name=file_name, export_header=True, _block=("main", 1, "数据表格导出"))
