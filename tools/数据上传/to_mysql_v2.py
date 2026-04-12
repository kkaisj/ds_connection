# 使用提醒:
# 1. xbot包提供软件自动化、数据表格、Excel、日志、AI等功能
# 2. package包提供访问当前应用数据的功能，如获取元素、访问全局变量、获取资源文件等功能
# 3. 当此模块作为流程独立运行时执行main函数
# 4. 可视化流程中可以通过"调用模块"的指令使用此模块

import xbot
import xbot_visual
from xbot import print, sleep
from .import package
from .package import variables as glv

"""
入库流程

是否老客: 是->引入v1入库脚本, 直接执行v1版本

新客流程

1. 数据库初始化
    数据库是否存在, 不存在尝试创建 # api
    配置表格是否存在, 不存在创建 # api

2. 数据集对象初始化  # dataset
    文件校验：
        是否为空[空文件退出上传流程]
        指定主键字段文件内是否缺失
    文件清洗：
        # 初始化过程进行
        读取全部以str格式
        nan以空字符串填充

以中文字段, 全str格式入库一次

3. 根据 tableName 查询 MAP_TRANSLATOR_TABLE, 不存在值则上传流程结束
4. 查询 MAP_TRANSLATOR_TABLE 字段 target_db 是否存在异常值，存在不同db那么直接异常，取第一个为映射数据库
   切换 tool.engin 到映射数据库``

5. 映射数据库初始化， 只做数据库初始化，map_dataset在原始库内存在
6. 根据 MAP_TRANSLATOR_TABLE 查询出 target_field target_field_type, 对文件进行 【二次清洗】
     df.rename 字段映射改名
     pd.to_numeric(errors="") 定义转数值仅支持 double 转日期支持 date, datetime [非varchar，不是这三种直接异常]
     转日期不需要进行转换，直接更新字段格式，可以以字符串格式上传

     检查 target_table 是否已存在，不存在按照映射关系创建
     target_table 已存在 获取表字段格式和映射配置字段格式进行对比，存在增加的则修改更新target_table表格式

7. 根据 MAP_TRANSLATOR_TABLE 查询出 target_table 获取映射目标数据表，存在不同值异常，和db一样

8. 根据 target_table, target_field, target_field_type, df 生成映射表上传模型, create_table_if_not_exists
9. 更新映射表数据

10. 字段检查

11. 主键检查

12. 转译信息检查
"""
import contextlib
import random
import re
import traceback
from typing import List, Optional
from urllib.parse import quote_plus
from datetime import datetime
from enum import Enum

import pandas as pd
import sqlalchemy.engine
from sqlalchemy import Index, MetaData, create_engine, text
from sqlalchemy import Table as SQLAlchemyTable
from sqlalchemy.exc import ResourceClosedError, DataError
from pandas.core.dtypes.common import is_float_dtype, is_integer_dtype
from pydantic import BaseModel
import requests

from xbot_extensions.activity_ljq_global.feishu_base_config import feishu
from xbot_extensions.activity_ljq_global.G import global_dict
from xbot_extensions.activity_ljq_global.finally_raise import registe_finally_raise
from .backend_service import save_table_struct, upload_sink_info
from .utils import precheck_message_notice


global_dict['add_new_columns'] = []

MAP_TABLE = "map_dataset"

MAP_TABLE_STRUCT = [
    {"name": "data_set", "type": "VARCHAR(255)", "comment": "数据集名称"},
    {"name": "data_set_en", "type": "VARCHAR(255)", "comment": "入库表名"},
    {"name": "app_name", "type": "VARCHAR(255)", "comment": "取数连接器名称"},
    {"name": "columns", "type": "TEXT", "comment": "数据集名称"},
]

MAP_TRANSLATOR_TABLE = "map_translator"

MAP_TRANSLATOR_TABLE_STRUCT = [
    {"name": "data_set", "type": "VARCHAR(255)", "comment": "数据集名称"},
    {"name": "source_table", "type": "VARCHAR(255)", "comment": "源数据表名称"},
    {"name": "source_field_name", "type": "VARCHAR(100)", "comment": "源字段名称"},
    {"name": "source_field_type", "type": "VARCHAR(20)", "comment": "源字段类型"},
    {"name": "target_db", "type": "VARCHAR(30)", "comment": "映射目标数据库名称"},
    {"name": "target_table", "type": "VARCHAR(255)", "comment": "映射目标数据表名称"},
    {"name": "target_field_name", "type": "VARCHAR(100)", "comment": "映射目标字段名称"},
    {"name": "target_field_type", "type": "ENUM('date', 'datetime', 'double')", "comment": "映射目标字段类型"},
]


def duplicate_elements(lst):
    seen = set()
    duplicates = set()

    for item in lst:
        if item in seen:
            duplicates.add(item)
        else:
            seen.add(item)
    return list(duplicates)


class Field(BaseModel):
    name: str
    type: str
    comment: Optional[str] = ""
    is_primary: bool = False

    def __eq__(self, other):
        if isinstance(other, Field):
            return other.name == self.name and other.type.lower() == self.type.lower()
        elif isinstance(other, str):
            return other == self.name
        else:
            return False


class KeyType(Enum):
    PRIMARY = "PRIMARY KEY"
    UNIQUE = "UNIQUE INDEX"
    INDEX = "INDEX"


class Table(BaseModel):
    name: str
    primary_keys: Optional[List[str]] = []
    fields: List[Field]
    comment: Optional[str] = ""
    key_type: KeyType = KeyType.UNIQUE

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        for f in self.fields:
            if f.name in self.primary_keys:
                f.is_primary = True

    @property
    def rename_dict(self):
        # 重命名字段
        rename_dict = {
            f.comment: f.name for f in self.fields if f.comment and f.comment != f.name
        }

        # 重复值检查
        d = duplicate_elements(rename_dict.values())
        if d:
            duplicated_fields = {k: v for k, v in rename_dict.items() if v in d}
            raise ValueError(
                f"转译配置异常: 同数据表内转译出现重复字段 - {duplicated_fields}"
            )

        return rename_dict


class Dataset:
    def __init__(self, data_set: str, file_path: str, primary_keys: list):
        """
        数据集对象
        :param data_set: 数据集名称
        :param file_path: 数据文件路径
        :param primary_keys: 主键列表
        """
        self.data_set = data_set
        self.file_path = file_path
        self.primary_keys = primary_keys
        self.table_name = self._table_name()

        self.df: pd.DataFrame = pd.read_excel(self.file_path, dtype=str)

        if not self.df.empty:
            self.file_front_check()

    def file_front_check(self):
        """
        前置检查和必要的简单清洗
        :return:
        """

        # 检查去重主键字段是否存在
        differences_columns = set(self.primary_keys).difference(set(self.df.columns))
        if differences_columns:
            print(f"文件字段: {list(self.df.columns)}")
            print(f"去重主键: {list(self.primary_keys)}")

            raise ValueError(f"数据集【{self.data_set}】去重主键字段不存在主键【{differences_columns}】，请检查后修改！ - ")

        df = self.df
        # 对 RPA店铺名_页面 和 RPA店铺名_自填 进行处理, 二者只能留一个
        if df.columns.__contains__('RPA店铺名_页面') and df.columns.__contains__('RPA店铺名_自填'):
            df.drop('RPA店铺名_页面', axis=1, inplace=True)
            if self.primary_keys.__contains__('RPA店铺名_页面'):
                self.primary_keys.remove('RPA店铺名_页面')

        # 将字段内的%替换为 _percent_, sqlalchemy的bug, %为占位符, 会报错异常.
        # todo：后续将所有新任务停用此特性
        if str(global_dict.get("task_configs", {}).get("company_id")) != "894050763223113728":  # 除了 康臣 以外的客户字段仍然替换
            df.columns = [
                c.replace("%", "_percent_").strip() for c in df.columns
            ]

        # 数据清洗: 清洗nan
        df.fillna("", inplace=True)

    def data_clean(self, table: Table):
        """
        数据清洗
        :return:
        """
        map_func = {
            "date": self.convert_date,
            "datetime": self.convert_datetime,
            "double": self.convert_to_numeric
        }

        for field in table.fields:
            # 清洗字段格式，转换异常值为默认值
            t = field.type.lower()
            if t.startswith("varchar"):
                continue
            self.df[field.name] = self.df[field.name].map(lambda x: map_func[t](x))
            print(f"字段转译数据清洗: {field.comment}->{t}")

    def _table_name(self):
        """
        转译后的英文表格名称
        :return:
        """
        import pinyin

        def p(single_word, delimiter):
            if single_word == delimiter:
                return delimiter
            s = pinyin.get(single_word, delimiter="", format="strip")
            return s[0]

        res = "".join(p(c, "_") for c in self.data_set)
        return f"rpa_{res.lower()}"

    @property
    def empty(self):
        return self.df.empty

    @staticmethod
    def convert_date(date_str):
        """
        日期字符串转换为指定格式
        :param date_str:
        :return:
        """
        date_time_obj = pd.to_datetime(date_str, errors="coerce")

        if pd.isna(date_time_obj):
            return "1900-01-01"

        return date_time_obj.strftime("%Y-%m-%d")

    @staticmethod
    def convert_datetime(date_str):
        """
        日期字符串转换为指定格式
        :param date_str:
        :return:
        """
        date_time_obj = pd.to_datetime(date_str, errors="coerce")

        if pd.isna(date_time_obj):
            return "1900-01-01"

        return date_time_obj.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def convert_to_numeric(value_str):
        """
        转换为数值
        :param value_str:
        :return:
        """
        value_str = str(value_str).replace(",", "")
        number = pd.to_numeric(value_str, errors="coerce")

        if pd.isna(number):
            return 0

        return number

    def fields_struct(self, is_tran) -> List[Field]:
        """
        上传数据表的所有字段结构
        :param is_tran:
        :return:
        """
        return [
            Field(
                name=field_name,
                type=self.field_type(
                    field_name,
                    is_tran
                ),
                comment=field_name
            )
            for field_name in self.df.columns
        ]

    def field_type(self, field_name: str, is_tran: bool):
        """
        匹配单列数据类型
        :param field_name:
        :param is_tran: 是否转译， 转译状态通用匹配类型转换, 不转译只给 varchar
        :return:
        """
        series = self.df[field_name]

        values = series.tolist()
        max_length = len(str(max(values, key=lambda x: len(str(x)))))
        varchar_type = "varchar(10)" if max_length < 10 else f"varchar({max_length + 30})"

        # if not is_tran:
        #     return varchar_type

        # if is_float_dtype(series) or series.empty or is_integer_dtype(series):
        #     return "double"

        # min_length = len(str(min(values, key=lambda x: len(str(x)))))

        # # date日期列格式判断; 只有完全符合条件的日期列被赋予
        # random_value = random.choice(values)
        # if max_length == min_length == 10:
        #     date_pattern = r'\d{4}[-/]\d{2}[-/]\d{2}'
        #     if re.fullmatch(date_pattern, random_value):
        #         return "date"
        # elif max_length == min_length == 19:
        #     datetime_pattern = r'\d{4}[-/]\d{2}[-/]\d{2} \d{2}:\d{2}:\d{2}'
        #     if re.fullmatch(datetime_pattern, str(random_value)):
        #         return "datetime"

        return varchar_type


class MysqlAPI:
    def __init__(self, host, port, user, password, db_name):
        self.engin: sqlalchemy.engine.Engine

        self.engin = create_engine(
            f"mysql+pymysql://{user}:{quote_plus(password)}@{host}:{port}?charset=utf8mb4",
        )

        self.create_database_if_not_exists(db_name)

        self.engin = create_engine(
            f"mysql+pymysql://{user}:{quote_plus(password)}@{host}:{port}/{db_name}?charset=utf8mb4"
        )

        self.init_config_table()

    def delete_data_by_conditions(
        self,
        table_name: str,
        delete_conditions: dict,
    ):
        """
        上传数据前删除数据
        :param table_name:
        :param delete_conditions: 例如: {"日期": "2024-01-01", "店铺名": "测试店铺"}
                                  生成: `日期` = '2024-01-01' AND `店铺名` = '测试店铺'

        :return:
        """
        if delete_conditions is None:
            delete_conditions = {}

        print(f" 开始删除数据: {table_name}; 条件: {delete_conditions}")

        # 创建数据库引擎
        engine = self.engin

        try:
            # 根据条件删除
            if not delete_conditions:
                message = "WARNING: 删除条件为空，跳过删除操作"
                print(message)
                return

            where_condition = build_where_condition(delete_conditions)

            if not where_condition:
                message = "WARNING: 构建的删除条件为空，跳过删除操作"
                print(message)
                return

            sql = f"DELETE FROM `{table_name}` WHERE {where_condition}"

            with engine.begin() as conn:
                result = conn.execute(sql.replace("%", "%%"))
                affected_rows = result.rowcount

            message = f"已删除表 {table_name} 中满足条件的数据，共 {affected_rows} 行"
            print(message)

        except Exception as e:
            error_msg = f"ERROR: 删除数据时发生错误: {str(e)}"
            print(error_msg)

    def update_chunk_df(
        self, chunk_df, dataset, is_tran, delete_before_upload, is_retry=False
    ):
        """
        更新切片数据
        :param chunk_df: pd.DataFrame 清洗转译后的切片数据
        :param dataset: 数据集对象
        :param is_tran: 是否转译
        :param delete_before_upload:
        :param is_retry: 是否重试
        :return: 受影响的行数 (MySQL ON DUPLICATE KEY UPDATE: 新增=1, 更新=2, 无变化=0)
        """
        columns = chunk_df.columns
        table_name = dataset.table_name
        engin = self.engin

        placeholders = ",".join(["%s"] * len(columns))

        # 构建批量插入数据的SQL语句
        insert_query = (
            f"INSERT INTO `{table_name}` ({','.join(f'`{c}`' for c in columns)}) VALUES ({placeholders}) "
            + (
                f"ON DUPLICATE KEY UPDATE {','.join([f'`{col}`=VALUES(`{col}`)' for col in columns])}"
                if not delete_before_upload
                else ""
            )
        )

        # 列名中的 % 需转义为 %% 避免 PyMySQL 将其误作格式占位符，
        # 再将被误转义的 %%s 还原为 %s（值占位符）
        insert_query = insert_query.replace("%", "%%").replace("%%s", "%s")

        # 构建插入的数据列表
        data_tuples = [tuple(row) for row in chunk_df.values]

        affected_rows = 0
        try:
            with engin.begin() as conn:
                result = conn.execute(insert_query, data_tuples)
                affected_rows = result.rowcount

            if is_retry:
                print("尝试修改表结构后更新成功！")

            return affected_rows

        except DataError as e:
            # 更新失败后，切片frame保存到异常文件夹。

            # 尝试解决异常
            err = traceback.format_exc()

            # 可能是数据超出字段长度限制导致DataError，重写数据表配置
            too_long_columns = set()

            # 提取因字段异常导致的正则表达式
            pattern_list = [
                "Data too long for column '(.*?)' at",  # 字段长度超出限制
                "Data truncated for column '(.*?)'",  # 数据被截断
                "Incorrect integer value: '.*?' for column '(.*?)'",  # 类型更改【之前是数字，现在里面混入了字符】
                "Incorrect datetime value: '.*' for column '(.*?)'",  # 日期类型更改【之前是日期，现在里面混入了字符】
            ]

            # 提取出异常的字段
            for pattern in pattern_list:
                long_columns = {s for s in re.findall(pattern, err) if s != ""}
                too_long_columns.update(long_columns)

            # 不存在将异常抛出去
            if not too_long_columns:
                raise e

            # 存在因字段长度超出限制或字段类型发生改变所导致的异常
            for column in too_long_columns:
                print(f"长度超出范围或类型异常字段: {column}")
                column_type = dataset.field_type(column, is_tran=is_tran)

                alter_sql = f"""
                            ALTER TABLE `{table_name}` MODIFY `{column}` {column_type} 
                            COMMENT '{self.comment_from_field_name(dataset.data_set, is_tran, column)}';
                            """
                print(f"修改表结构: {alter_sql}")

                with engin.begin() as conn:
                    conn.execute(alter_sql.replace("%", "%%"))

                    # 更新配置表信息
                    if not is_tran:
                        update_sql = f"""
                        UPDATE `{MAP_TRANSLATOR_TABLE}` SET source_field_type='{column_type}' 
                        WHERE source_table='{table_name}' AND source_field_name='{column}'
                        """
                        conn.execute(update_sql.replace("%", "%%"))

            return self.update_chunk_df(
                chunk_df, dataset, is_tran, delete_before_upload, True
            )

    def update_value(self, dataset: Dataset, is_tran, delete_before_upload):
        """
        更新数据
        :param dataset:
        :param is_tran:
        :param delete_before_upload:
        :return: 总受影响行数
        """

        df = dataset.df
        table_name = dataset.table_name

        if df.empty:
            print(f"更新数据集为空, 自动跳过: {table_name}")
            return 0

        total_affected_rows = 0
        for chunk_df in self.chunk_df_generator(df, chunk_size=1000):
            affected = self.update_chunk_df(
                chunk_df, dataset, is_tran, delete_before_upload
            )
            total_affected_rows += affected or 0

        return total_affected_rows

    @staticmethod
    def chunk_df_generator(df: pd.DataFrame, chunk_size: int):
        """
        更新数据
        :param df:
        :param chunk_size:
        :return:
        """

        # 获取DataFrame的总行数
        total_rows = len(df)

        # 计算切片数量
        num_chunks = (total_rows - 1) // chunk_size + 1

        # 循环切片并执行UPDATE语句
        for i in range(num_chunks):
            start_idx = i * chunk_size
            end_idx = min((i + 1) * chunk_size, total_rows)
            chunk_df = df.iloc[start_idx:end_idx]

            yield chunk_df

            print(f"数据集更新覆盖进度： {round((i + 1) / num_chunks, 4) * 100}%")
        print("数据集更新完成! ")

    def translator(
        self, data_set: str, is_tran: bool, source_field, target_field
    ) -> dict:
        """
        查询表格的转译配置信息
        :param data_set: 数据集名称
        :param is_tran: 是否转译
        :param target_field: 获取转译字典的字段 [target_field_type, target_field_name]
        :param source_field: 转译前的key字段 [source_field_name, source_table]
        :return:
        """
        if not is_tran:
            return {}

        sql = f"""
        SELECT {source_field}, {target_field}
        FROM `{MAP_TRANSLATOR_TABLE}`
        WHERE data_set = '{data_set}'
          AND {target_field} IS NOT NULL
          AND {target_field} != ''
        """
        t_df: pd.DataFrame = pd.read_sql(sql=sql, con=self.engin)

        t_df.dropna(axis=0, inplace=True)

        if t_df.empty:
            return {}

        return (
            t_df[[source_field, target_field]]
            .set_index(source_field)
            .T.to_dict("records")[0]
        )

    def comment_from_field_name(self, data_set, is_tran, field_name: str):
        """
        通过字段名查找comment
        :param data_set:
        :param field_name:
        :param is_tran:
        :return:
        """
        name_translator = self.translator(
            data_set=data_set,
            is_tran=is_tran,
            source_field="source_field_name",
            target_field="target_field_name",
        )

        comment_map = {v: k for k, v in name_translator.items()}

        return comment_map.get(field_name, field_name)

    def create_database_if_not_exists(self, db_name: str):
        """
        创建数据库
        :param db_name:
        :return:
        """
        if not self.exists_db(db_name):
            try:
                self.execute(
                    f"CREATE DATABASE IF NOT EXISTS {db_name} CHARSET utf8mb4; "
                )
                print(f"数据库已创建：{db_name} - CHARSET utf8mb4")
            except Exception as e:
                if e.__str__().__contains__("pymysql.err.OperationalError: (1044"):
                    raise Exception(
                        f"用户【{self.engin.url.username}】没有权限创建数据库，请参考"
                        f"【https://yingdao.yuque.com/xvfe50/zbx2f3/pong5ei0lgpr8qvq?singleDoc# 《MySQL权限不足》】"
                    )
                else:
                    raise e

    def execute(self, sql):
        """
        执行sql并返回所有结果
        :param sql:
        :return:
        """
        # 清理SQL语句中的空字符，避免阿里云RDS语法错误
        # 参考错误: (1726, '[30000, ...] syntax error. SQL => ... \x00')
        sql = sql.replace(chr(0), "").strip()
        sql = sql.replace("%", "%%")

        with self.engin.connect() as conn:
            # print(f"Execute: {sql}")
            try:
                return conn.execute(sql).fetchall()
            except ResourceClosedError as e:
                if e.__str__().__contains__("does not return rows"):
                    return ()

    @staticmethod
    def default_value(type_: str):
        type_ = type_.lower()
        if "varchar" in type_ or "text" in type_:
            return ""
        if "date" == type_:
            return "1900-01-01"
        elif "datetime" == type_:
            return "1900-01-01 00:00:00"
        return 0

    def create_table(self, table: Table):
        if len(table.primary_keys) == 0:
            s = "".join(
                f"`{field.name}` {field.type} COMMENT '{field.comment}', "
                for field in table.fields
            ).rstrip(", ")

            sql = f"""
                CREATE TABLE IF NOT EXISTS `{table.name}`(
                {s}
                ) COMMENT '{table.comment}' CHARSET=utf8mb4
            """
        else:
            s = "".join(
                f"`{filed.name}` {filed.type} COMMENT '{filed.comment}', "
                for filed in table.fields
            )

            sql = f"""
                CREATE TABLE IF NOT EXISTS `{table.name}` (
                    {s}
                    {table.key_type.value} `{get_unique_index_name(table.name)}` ({",".join(f"`{key}`" for key in table.primary_keys)})
                ) COMMENT '{table.comment}' CHARSET=utf8mb4
            """

        self.execute(sql)

    def insert_row(self, table, items: dict):
        """
        简单插入一行数据
        :param table:
        :param items:{col: val}
        :return:
        """

        # 构建插入sql语句
        cols, values = items.keys(), items.values()
        column = ",".join(cols)
        value = "".join(f"'{i}'," for i in values).rstrip(",")
        sql = f"INSERT INTO `{table}` ({column}) VALUES ({value});"
        # print(sql)
        return self.execute(sql)

    @property
    def tables(self):
        return [i[0] for i in self.execute("SHOW TABLES;")]

    @property
    def dbs(self):
        return [i[0] for i in self.execute("SHOW DATABASES;")]

    def exists_db(self, db_name):
        return db_name in self.dbs

    def exists_table(self, table_name):
        return table_name in self.tables

    def get_table_columns(self, table_name):
        return [c[0] for c in self.execute(f"SHOW COLUMNS FROM `{table_name}`")]

    def init_config_table(self):
        # map_dataset表初始化检查
        if not self.exists_table(MAP_TABLE):
            self.create_table(
                Table(
                    name=MAP_TABLE,
                    primary_keys=["data_set", "data_set_en"],
                    fields=[Field(**f) for f in MAP_TABLE_STRUCT],
                    comment="连接器入库映射表",
                    key_type=KeyType.PRIMARY
                )
            )

        # 转译数据库不创建配置表

        # map_translator表初始化检查
        if not self.exists_table(MAP_TRANSLATOR_TABLE):
            self.create_table(
                Table(
                    name=MAP_TRANSLATOR_TABLE,
                    primary_keys=["data_set", "source_table", "source_field_name"],
                    fields=[Field(**f) for f in MAP_TRANSLATOR_TABLE_STRUCT],
                    comment="连接器入库转译字段映射表",
                    key_type=KeyType.PRIMARY
                )
            )

    def table_comments(self, table_name):
        """
        查找table内已有的所有comment
        """
        # 填充comment为空的字段

        sql = f"""
                SELECT
                       CASE
                           WHEN COLUMN_COMMENT = '' THEN COLUMN_NAME
                           ELSE COLUMN_COMMENT
                       END AS COMMENT_OR_COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = '{self.engin.url.database}'
                AND TABLE_NAME = '{table_name}';
        """

        return list(filter(lambda x: x != "", [line[0] for line in self.execute(sql)]))

    def translator_source_field_name(self, data_set, field_name, is_tran):
        """
        通过转译表查找原字段名 comment
        :param data_set:
        :param field_name:
        :param is_tran:
        :return:
        """
        translator = self.translator(
            data_set=data_set,
            is_tran=is_tran,
            source_field="source_field_name",
            target_field="target_field_name",
        )
        return {
            target_field: source_field
            for source_field, target_field in translator.items()
        }.get(field_name, field_name)

    def find_column_by_comment(self, comment: str, table_name: str):
        """
        根据comment或column查找字段名 旧版程序创建的报表没有comment
        :param comment: 注释
        :param table_name: 表名
        :return: 字段名
        """
        engin = self.engin

        sql = f"""
            SELECT
                COLUMN_NAME
            FROM
                INFORMATION_SCHEMA.COLUMNS
            WHERE
                (table_schema = '{engin.url.database}' AND COLUMN_COMMENT = '{comment}' AND TABLE_NAME = '{table_name}')
            OR (table_schema = '{engin.url.database}' AND COLUMN_NAME = '{comment}' AND TABLE_NAME = '{table_name}');
        """

        with engin.begin() as coon:
            column = coon.execute(sql.replace("%", "%%")).fetchone()

        return column[0] if column else None

    def column_rename(
        self,
        table_name: str,
        old_column: str,
        new_column: str,
        column_type: str,
        comment: str,
        **kwargs,
    ):
        """
        字段重命名
        :param table_name:
        :param old_column:
        :param new_column:
        :param column_type:
        :param comment:
        :return:
        """

        engin = self.engin

        important_type = kwargs.get("important_type")
        if important_type:
            column_type = important_type
            print(f"强制使用字段类型: {column_type}")

        print(f"字段重命名: {old_column} -> {new_column}")
        sql = f"""
        ALTER TABLE `{table_name}` CHANGE `{old_column}` `{new_column}` {column_type} COMMENT '{comment}';
        """
        try:
            with engin.begin() as coon:
                coon.execute(sql.replace("%", "%%"))
        except DataError:
            size = kwargs.get("size") or 100
            if kwargs.get("recursion") and size >= 1000:
                raise Exception("字段异常：无法重置字段类型！")
            elif kwargs.get("recursion"):
                size += 100

            t = f"varchar({size})"
            print("修改字段名因字段类型导致DataError, 强制指定类型后重试.")
            self.column_rename(
                table_name,
                old_column,
                new_column,
                column_type,
                comment,
                important_type=t,
                recursion=True,
                size=size
            )

    def table_created_fields(self, table_name: str) -> List[Field]:
        """
        根据comment或column查找字段名 旧版程序创建的报表没有comment
        :param table_name: 表名
        :return: 字段名
        """
        engin = self.engin

        sql = f"""
            SELECT
                COLUMN_NAME, COLUMN_TYPE
            FROM
                INFORMATION_SCHEMA.COLUMNS
            WHERE
                (table_schema = '{engin.url.database}' AND TABLE_NAME = '{table_name}')
        """

        with engin.begin() as coon:
            columns_data = coon.execute(sql.replace("%", "%%")).fetchall()
            return [Field(name=row[0], type=row[1]) for row in columns_data]

    def table_primary_keys_old(self, table_name):
        """
        当前表格主键
        :param table_name:
        :return:
        """

        engin = self.engin
        select_sql = f"""
            SELECT
                COLUMN_NAME
            FROM
                INFORMATION_SCHEMA.COLUMNS
            WHERE
                (table_schema = '{engin.url.database}' AND COLUMN_KEY = 'PRI' AND TABLE_NAME = '{table_name}')
        """

        return [row[0] for row in self.execute(select_sql)]

    def table_primary_keys(self, table_name):
        """
        当前表格真正的主键（排除唯一索引）
        通过 TABLE_CONSTRAINTS 精确查询 PRIMARY KEY
        :param table_name:
        :return:
        """
        engin = self.engin

        # 使用 TABLE_CONSTRAINTS + KEY_COLUMN_USAGE 精确查询 PRIMARY KEY
        # 避免 UNIQUE INDEX 被误识别为 PRI
        select_sql = f"""
            SELECT kcu.COLUMN_NAME
            FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
            JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
                ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
                AND tc.TABLE_SCHEMA = kcu.TABLE_SCHEMA
                AND tc.TABLE_NAME = kcu.TABLE_NAME
            WHERE tc.TABLE_SCHEMA = '{engin.url.database}'
              AND tc.TABLE_NAME = '{table_name}'
              AND tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
            ORDER BY kcu.ORDINAL_POSITION
        """

        return [row[0] for row in self.execute(select_sql)]

    def create_index_orm(
        self, table_name: str, index_name: str, columns: list, unique: bool = False
    ):
        """
        使用ORM方式创建索引
        :param table_name: 表名
        :param index_name: 索引名
        :param columns: 列名列表
        :param unique: 是否为唯一索引
        :return:
        """
        try:
            # 创建 MetaData 对象
            metadata = MetaData()

            # 反射表结构（从数据库中加载表定义）
            table = SQLAlchemyTable(table_name, metadata, autoload_with=self.engin)

            # 获取表中的列对象
            column_objects = [table.c[col_name] for col_name in columns]

            # 创建 Index 对象
            index = Index(index_name, *column_objects, unique=unique)

            # 执行创建索引的 DDL
            with self.engin.begin() as conn:
                index.create(conn)

            return True
        except Exception as e:
            print(f"ORM创建索引失败: {e}")
            raise

    def drop_index_orm(self, table_name: str, index_name: str):
        """
        使用ORM方式删除索引
        :param table_name: 表名
        :param index_name: 索引名
        :return:
        """
        try:
            # 方法1: 尝试使用 SQL 语句删除（最可靠）
            sql = f"DROP INDEX `{index_name}` ON `{table_name}`"
            self.execute(sql)

            return True
        except Exception as e:
            print(f"删除索引失败: {e}")
            raise

    def close(self):
        self.engin.dispose()


def clear_config_table(db: MysqlAPI):
    """
    清理配置表表内不存在的记录
    :param db:
    :return:
    """
    # 查找所有已记录的data_set
    query = f"SELECT DISTINCT data_set_en FROM {MAP_TABLE};"
    dataset_tables = [row[0] for row in db.execute(query)]

    # 遍历结果查询table是否存在，如果不存在就删除记录
    tables = db.tables
    for table_name in dataset_tables:
        if table_name not in tables:
            delete_query = (
                f"DELETE FROM map_dataset WHERE data_set_en = '{table_name}';"
            )
            db.execute(delete_query)
            print(f"清理不存在的表记录: {table_name}")

    # 转移表不进行清理，配置期间可能把客户配置好的转译配置误删


def is_old_customer(company_id):
    """
    此客户是否为旧客户
    :param company_id:
    :return:
    """
    customers = [
        {
            "COMPANY_ID": "625957414144561152",
            "COMPANY_NAME": "海宁卡拉扬皮草商贸有限公司",
        },
        {"COMPANY_ID": "630729021344169984", "COMPANY_NAME": "浙江海明实业有限公司"},
        {"COMPANY_ID": "659622534032560128", "COMPANY_NAME": "阳坊胜利"},
        {"COMPANY_ID": "674090128293142528", "COMPANY_NAME": "徐州市万卷图书有限公司"},
        {
            "COMPANY_ID": "664715018988322816",
            "COMPANY_NAME": "深圳市窑鸡王餐饮服务有限公司",
        },
        {
            "COMPANY_ID": "697322647368241152",
            "COMPANY_NAME": "佳禾食品工业股份有限公司",
        },
    ]

    return str(company_id) in [item["COMPANY_ID"] for item in customers]


def build_table(
    dataset: Dataset, db_api: MysqlAPI, is_tran: bool, delete_before_upload: bool
) -> Table:
    """
    构建入库table对象
    :param dataset:
    :param db_api:
    :param is_tran:
    :param delete_before_upload:
    :return:
    """

    table_name = dataset.table_name

    # 获取数据表的原始字段结构
    fields = dataset.fields_struct(is_tran)

    # get translator # api
    name_translator = db_api.translator(
        data_set=dataset.data_set,
        is_tran=is_tran,
        target_field="target_field_name",
        source_field="source_field_name",
    )

    type_translator = db_api.translator(
        data_set=dataset.data_set,
        is_tran=is_tran,
        target_field="target_field_type",
        source_field="source_field_name",
    )

    # 根据转译配置重置字段结构
    for f in fields:
        f.name = name_translator.get(f.comment) or f.comment
        f.type = type_translator.get(f.comment) or f.type

    table_name_translator = db_api.translator(
        data_set=dataset.data_set,
        is_tran=is_tran,
        target_field="target_table",
        source_field="source_table",
    )

    # 转译后的表名
    target_table = table_name_translator.get(table_name) or table_name
    # 重新设置dataset对象
    dataset.table_name = target_table

    # 转译后的主键
    pks = [name_translator.get(pk) or pk for pk in dataset.primary_keys]
    # 清理主键中的空字符
    pks = [pk.replace(chr(0), "").strip() for pk in pks]
    # 重设
    dataset.primary_keys = pks

    key_type = (
        KeyType.PRIMARY
        if str(db_api.engin.url.host).__contains__("ads.aliyuncs.com")
        else (KeyType.INDEX if delete_before_upload else KeyType.UNIQUE)
    )

    return Table(
        name=target_table,
        primary_keys=pks,
        fields=fields,
        comment=dataset.data_set,
        key_type=key_type,
    )


def config_table_update(
    dataset: Dataset, db_api: MysqlAPI, table: Table, is_tran: bool
):
    """
    更新配置表信息
    :param dataset:
    :param db_api:
    :param table:
    :param is_tran:
    :return:
    """
    with contextlib.suppress(sqlalchemy.exc.IntegrityError):
        db_api.insert_row(
            MAP_TABLE,
            {
                "data_set": dataset.data_set,
                "data_set_en": dataset.table_name,
                "columns": ",".join(dataset.df.columns),
                "app_name": global_dict.get("task_configs", {}).get(
                    "current_app_name", ""
                ),
            },
        )
        print(f"`{MAP_TABLE}` 增加新纪录: {dataset.data_set}")

    # 转译库内不对字段信息记录
    if is_tran:
        return

    for f in table.fields:
        # 忽略因重复创建数据表，主键重复导致的异常
        with contextlib.suppress(sqlalchemy.exc.IntegrityError):
            db_api.insert_row(
                MAP_TRANSLATOR_TABLE,
                {
                    "data_set": dataset.data_set,
                    "source_table": dataset.table_name,
                    "source_field_name": f.name,
                    "source_field_type": f.type,
                },
            )

    print(f"`{MAP_TRANSLATOR_TABLE}` 增加新纪录: {dataset.data_set}")


def new_fields_check(db_api: MysqlAPI, dataset: Dataset, is_translation: bool):
    """
    字段新增/改翻译校验
    :param db_api:
    :param dataset:
    :param is_translation:
    :return:
    """
    table_name = dataset.table_name
    db_table_fields = db_api.get_table_columns(table_name)
    difference_fields = set(dataset.df.columns).difference(db_table_fields)
    if not difference_fields:
        return

    print(f"存在新增字段/转译字段: {difference_fields}")
    table_comments = db_api.table_comments(table_name)
    for d_field in difference_fields:
        field_source_name = db_api.translator_source_field_name(
            data_set=dataset.data_set, field_name=d_field, is_tran=is_translation
        )

        column_type = dataset.field_type(d_field, is_translation)

        if field_source_name in table_comments:
            # 查找数据库的当前字段名
            current_field_name = db_api.find_column_by_comment(
                comment=field_source_name, table_name=table_name
            )
            # 字段改名
            db_api.column_rename(
                table_name=table_name,
                old_column=current_field_name,
                new_column=d_field,
                column_type=column_type,
                comment=field_source_name,
            )

        else:
            # 新增字段
            d_field: str
            # 转译表逻辑: 新增字段非英文进行翻译
            d_field_english = None
            # if is_translation and not d_field.isascii():
            #     d_field_english = ai_translate(d_field)
            #     print(f"转译表新增中文字段 自动转译: {d_field}->{d_field_english}")
            #     d_field = d_field_english
            #     # 待上传的数据文件字段同步转译后的字段
            #     dataset.df.rename(
            #         columns={field_source_name: d_field_english}, inplace=True
            #     )

            sql = f"ALTER TABLE `{table_name}` ADD `{d_field}` {column_type}  COMMENT '{field_source_name}';"

            db_api.execute(sql)
            print(f"报表[{table_name}]新增字段: {d_field} - {column_type}")
            if "RPA" not in d_field:
                # 新增字段不包含RPA标记，进行记录，最后抛出异常，群通知
                global_dict["add_new_columns"].append(d_field)

            # 新增字段同步到配置表
            db_table_columns = db_api.get_table_columns(table_name)
            all_columns = list(set(dataset.df.columns).union(set(db_table_columns)))
            db_api.execute(
                f"UPDATE {MAP_TABLE} SET columns='{','.join(all_columns)}' WHERE data_set_en='{table_name}'"
            )

            # 底表更新出现新增字段：在translator表内插入字段
            if not is_translation:
                # 忽略配置表内主键冲突的异常
                with contextlib.suppress(sqlalchemy.exc.IntegrityError):
                    db_api.insert_row(
                        MAP_TRANSLATOR_TABLE,
                        {
                            "data_set": dataset.data_set,
                            "source_table": table_name,
                            "source_field_name": d_field,
                            "source_field_type": column_type,
                        },
                    )
            elif is_translation and d_field_english is not None:
                # 更新 translator
                update_sql = f"""
                update `{MAP_TRANSLATOR_TABLE}` 
                set target_field_name = '{d_field_english}'
                where data_set = '{dataset.data_set}' and 
                    source_field_name = '{field_source_name}';
                """
                db_api.execute(update_sql)

            print("配置表已同步更新.")


def fields_type_check(db_api, table, table_name, is_tran):
    """
    字段格式更新校验
    :param db_api:
    :param table:
    :param table_name:
    :param is_tran:
    :return:
    """
    if not is_tran:
        return

    created_fields = db_api.table_created_fields(table_name)
    for field in table.fields:
        if field in created_fields:
            continue

        if field.type.lower().startswith("varchar"):
            continue

        # 更新字段的格式
        alter_sql = f"""
                    ALTER TABLE `{table_name}` MODIFY `{field.name}` {field.type} 
                    COMMENT '{field.comment}';
                    """
        db_api.execute(alter_sql)
        print(f"更新字段转译格式: {field}")


def primary_keys_check(db_api, dataset, table_name):
    """
    主键校验
    :param db_api:
    :param dataset:
    :param table_name:
    :return:
    """
    current_primary_keys = (
        db_api.table_primary_keys_old(table_name)
        if db_api.engin.url.host.__contains__("ads.aliyuncs.com")
        else db_api.table_primary_keys(table_name)
    )

    print(f"current_primary_keys： {current_primary_keys}")

    differences_keys = (
        set(dataset.primary_keys)
        .difference(current_primary_keys)
        .union(set(current_primary_keys).difference(dataset.primary_keys))
    )
    if not differences_keys:
        return

    print(f"索引异常， 当前使用索引于实际索引不符。 --- {differences_keys}")

    # 删除所有索引
    try:
        db_api.execute(f"ALTER TABLE `{table_name}` DROP PRIMARY KEY")
    except Exception as e:
        if e.__str__().__contains__("DROP PRIMARY KEY not supported"):
            print("警告：当前数据库不支持删除主键重建，退出校验流程!")
            return 

        # 如果是因为索引不存在报错就跳过
        if not e.__str__().__contains__("exists"):
            raise e

    # 创建新索引
    db_api.execute(
        f"ALTER TABLE `{table_name}` ADD PRIMARY KEY ({','.join(f'`{key}`' for key in dataset.primary_keys)})"
    )
    print("索引重置完成.")


def tran_db_name(db_api, table_name):
    """
    获取转译数据库
    :param db_api:
    :param table_name:
    :return:
    """
    sql = f"""
        SELECT target_db from `{MAP_TRANSLATOR_TABLE}` 
        WHERE source_table='{table_name}'
          AND target_field_name IS NOT NULL
          AND target_table IS NOT NULL
        ORDER BY target_db DESC
    """
    data = db_api.execute(sql)

    if not data:
        print(
            f"未指定转译配置信息, 如需使用自动转译 请在 [`{MAP_TRANSLATOR_TABLE}`]指定转译信息！"
        )
        return

    target_db_set = set(s[0] for s in data if s[0])

    if len(target_db_set) != 1:
        raise ValueError(
            f"转译配置文件不正确: 一个SourceTable指定了多个数据库 - {target_db_set}"
        )

    tran_db = target_db_set.pop()

    print(f"转译数据库: {tran_db}")
    return tran_db


# ============================================


def build_where_condition(conditions) -> str:
    """
    构建删除条件SQL语句
    支持多个条件，多个条件之间使用 AND 连接
    例如: {"日期": "2024-01-01", "店铺名": "测试店铺"}
    生成: `日期` = '2024-01-01' AND `店铺名` = '测试店铺'
    :type conditions: dict | list
    """
    if not conditions:
        return ""

    def build_one_condition(condition: dict):
        where_conditions: list = []

        for field_name, condition_value in condition.items():
            # 转义字段名，防止SQL注入
            safe_field = f"`{field_name}`"

            if isinstance(condition_value, dict):
                # 复杂条件：支持操作符
                operator = condition_value.get("operator", "=").upper()
                value = condition_value.get("value")

                if operator == "BETWEEN":
                    # BETWEEN条件
                    if isinstance(value, (list, tuple)) and len(value) == 2:
                        where_conditions.append(
                            f"{safe_field} BETWEEN '{value[0]}' AND '{value[1]}'"
                        )
                    else:
                        raise ValueError(f"BETWEEN条件需要两个值，字段: {field_name}")
                elif operator == "IN":
                    # IN条件
                    if isinstance(value, (list, tuple)):
                        values_str = "', '".join(str(v) for v in value)
                        where_conditions.append(f"{safe_field} IN ('{values_str}')")
                    else:
                        raise ValueError(f"IN条件需要列表或元组，字段: {field_name}")
                elif operator == "LIKE":
                    # LIKE条件
                    where_conditions.append(f"{safe_field} LIKE '{value}'")
                elif operator in (">", "<", ">=", "<=", "!=", "<>"):
                    # 比较条件
                    where_conditions.append(f"{safe_field} {operator} '{value}'")
                else:
                    # 默认等于
                    where_conditions.append(f"{safe_field} = '{value}'")

            elif isinstance(condition_value, (list, tuple)):
                # 列表/元组：使用IN条件
                values_str = "', '".join(str(v) for v in condition_value)
                where_conditions.append(f"{safe_field} IN ('{values_str}')")

            else:
                # 简单值：等于条件
                where_conditions.append(f"{safe_field} = '{condition_value}'")

        return " AND ".join(where_conditions)

    if isinstance(conditions, dict):
        return build_one_condition(conditions)
    elif isinstance(conditions, list):
        batch_conditions = []

        for c in conditions:
            batch_conditions.append(f"( {build_one_condition(c)} )")

        return " OR ".join(batch_conditions)


def get_unique_index_name(table_name):
    """生成唯一索引名称"""
    # 去掉数据库前缀
    if "`.`" in table_name:
        table_name = table_name.split("`.`")[-1]
    # idx名称最长64位
    if len(table_name) > 52:
        table_name = table_name[:52]
    return f"uk_{table_name}_business"


def get_table_unique_index_columns(db_api, table_name):
    """
    获取表的唯一索引字段列表
    :param db_api:
    :param table_name:
    :return: 唯一索引字段列表，如果不存在返回空列表
    """
    index_name = get_unique_index_name(table_name)
    sql = f"""
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.STATISTICS
        WHERE TABLE_SCHEMA = '{db_api.engin.url.database}'
          AND TABLE_NAME = '{table_name}'
          AND INDEX_NAME = '{index_name}'
        ORDER BY SEQ_IN_INDEX
    """
    result = db_api.execute(sql)
    return [row[0] for row in result] if result else []


def is_index_unique(db_api, table_name) -> bool:
    """
    检查业务索引是否为唯一索引
    :param db_api:
    :param table_name:
    :return: True 表示唯一索引，False 表示普通索引，None 表示索引不存在
    """
    index_name = get_unique_index_name(table_name)
    sql = f"""
        SELECT NON_UNIQUE
        FROM INFORMATION_SCHEMA.STATISTICS
        WHERE TABLE_SCHEMA = '{db_api.engin.url.database}'
          AND TABLE_NAME = '{table_name}'
          AND INDEX_NAME = '{index_name}'
        LIMIT 1
    """
    result = db_api.execute(sql)
    if not result:
        return None  # 索引不存在
    # NON_UNIQUE = 0 表示唯一索引，NON_UNIQUE = 1 表示普通索引
    return result[0][0] == 0


def migrate_primary_to_unique_index(db_api, dataset, table_name):
    """
    当前流程仅使用UNIQUE INDEX 或 INDEX 时执行
    旧流程迁移：将主键迁移到唯一索引
    如果主键存在且与配置主键一致，删除主键并创建唯一索引
    :param db_api:
    :param dataset:
    :param table_name:
    :return: 
    """
    current_primary_keys = db_api.table_primary_keys(table_name)

    if not current_primary_keys:
        print("表无 PRIMARY KEY 约束，检查是否已使用唯一索引")
        return

    # 检查主键是否与配置一致（旧流程创建的表）
    if set(current_primary_keys) == set(dataset.primary_keys):
        print("旧流程创建的主键与配置一致，跳过处理。")
    else:
        # 主键发生变动，必须进行修改，否则可能引起后续的数据入库不正确

        print(
            f"警告：主键与配置不一致，移除主键操作。当前主键: {current_primary_keys}, 配置主键: {dataset.primary_keys}"
        )

        try:
            # 删除主键
            db_api.execute(f"ALTER TABLE `{table_name}` DROP PRIMARY KEY")
            print(f"已删除主键: {current_primary_keys}")
        except Exception as e:
            print(f"主键移除异常：{e}")
            raise Exception(f"异常: 当前主键与配置不一致且无法移除，需要人工接入重新配置数据表！ {e}")


def unique_index_check(db_api, dataset, table_name, delete_before_upload):
    """
    改进的主键检查 - 使用唯一索引策略
    1. 如果主键存在且与配置一致，删除主键，创建唯一索引
    2. 检查唯一索引与配置是否一致，不一致则更新唯一索引
    3. 当 delete_before_upload 为 True 时，需确保索引为普通索引
    :param db_api:
    :param dataset:
    :param table_name:
    :param delete_before_upload:
    """
    # 步骤1: 尝试从旧流程迁移（主键 -> 唯一索引）
    migrate_primary_to_unique_index(db_api, dataset, table_name)

    # 步骤2: 检查唯一索引与配置是否一致
    current_unique_columns = get_table_unique_index_columns(db_api, table_name)
    index_name = get_unique_index_name(table_name)

    # 判断是否需要更新索引
    columns_match = set(current_unique_columns) == set(dataset.primary_keys)
    current_is_unique = is_index_unique(db_api, table_name)

    # 期望的索引类型：delete_before_upload 为 True 时期望普通索引，否则期望唯一索引
    expected_is_unique = not delete_before_upload

    if columns_match and current_is_unique == expected_is_unique:
        index_type_desc = "普通索引" if delete_before_upload else "唯一索引"
        print(f"索引与配置一致（{index_type_desc}），无需更新")
        return

    # 需要更新索引的情况
    if columns_match and current_is_unique != expected_is_unique:
        # 字段匹配但索引类型不匹配，需要重建索引
        current_type = "唯一索引" if current_is_unique else "普通索引"
        target_type = "普通索引" if delete_before_upload else "唯一索引"
        print(f"索引类型需要更新。当前: {current_type}, 目标: {target_type}")
    else:
        # 字段不匹配
        print(
            f"索引需要更新。当前字段: {current_unique_columns}, 目标字段: {dataset.primary_keys}"
        )

    # 删除旧索引（如果存在）
    if current_unique_columns:
        try:
            db_api.drop_index_orm(table_name, index_name)
            print(f"已删除旧索引: {index_name}")
        except Exception as e:
            print(f"删除旧索引失败（可能不存在）: {e}")

    # 创建新索引
    # delete_before_upload 为 True 时创建普通 INDEX，否则创建 UNIQUE INDEX
    # 清理主键列表中的空字符
    clean_columns = [key.replace(chr(0), "").strip() for key in dataset.primary_keys]

    # 最多重试一次（删除重复数据后重试）
    max_retries = 2
    for attempt in range(max_retries):
        try:
            if delete_before_upload:
                print(
                    f"使用ORM创建普通索引: {index_name}, 列: {clean_columns} (尝试 {attempt + 1}/{max_retries})"
                )
                db_api.create_index_orm(
                    table_name, index_name, clean_columns, unique=False
                )
            else:
                print(
                    f"使用ORM创建唯一索引: {index_name}, 列: {clean_columns} (尝试 {attempt + 1}/{max_retries})"
                )
                db_api.create_index_orm(
                    table_name, index_name, clean_columns, unique=True
                )
            print(f"索引创建成功: {index_name}")
            break  # 成功则跳出循环

        except Exception as e:
            print(f"索引创建失败 (尝试 {attempt + 1}/{max_retries})：{e}")

            # 只在创建唯一索引且遇到重复数据时才处理
            if "Duplicate entry" in str(e) and not delete_before_upload:
                if attempt < max_retries - 1:  # 还有重试机会
                    print("检测到重复数据，开始清理...")

                    # 先查找并显示重复数据信息
                    duplicate_info, sql = _find_duplicate_data(
                        db_api, table_name, dataset.primary_keys
                    )
                    print(f"重复数据示例: {duplicate_info}")

                    try:
                        # 删除重复数据，保留最后一条
                        deleted_count = _remove_duplicate_keep_last(
                            db_api, table_name, dataset.primary_keys
                        )
                        if deleted_count is not None:
                            print(
                                f"已删除 {deleted_count} 条重复数据，准备重试创建索引..."
                            )
                        else:
                            print("已完成重复数据清理，准备重试创建索引...")

                        # 继续下一次循环，重试创建索引
                        continue

                    except Exception as clean_error:
                        print(f"清理重复数据失败: {clean_error}")
                        print(traceback.format_exc())

                        # 清理失败，记录详细错误信息
                        message = f"""
                            无法创建唯一索引，存在重复数据且清理失败！
                            重复的业务键: {dataset.primary_keys}
                            重复数据示例: {duplicate_info}
                            重复数据查询sql: {sql}
                            清理错误: {clean_error}
                        """
                        registe_finally_raise(
                            module="数据上传-索引创建",
                            line=1540,
                            details=message,
                        )
                        break
                else:
                    # 已经重试过了，仍然失败
                    duplicate_info, sql = _find_duplicate_data(
                        db_api, table_name, dataset.primary_keys
                    )
                    message = f"""
                        创建唯一索引失败（已重试）！
                        重复的业务键: {dataset.primary_keys}
                        重复数据示例: {duplicate_info}
                        重复数据查询sql: {sql}
                    """
                    registe_finally_raise(
                        module="数据上传-索引创建",
                        line=1540,
                        details=message,
                    )
                    break
            else:
                # 使用主键替代unique_key
                if expected_is_unique:
                    print("无法正常创建唯一索引，更换使用主键进行条件约束。")
                    primary_keys_check(db_api, dataset, table_name)
                    break
                else:
                    print("跳过普通索引创建动作。")
                    return


def _find_duplicate_data(db_api, table_name, primary_keys):
    """
    查找重复数据示例
    :param db_api:
    :param table_name:
    :param primary_keys:
    :return: 重复数据的字符串描述
    """
    key_columns = ", ".join(f"`{key}`" for key in primary_keys)

    sql = f"""
        SELECT {key_columns}, COUNT(*) as cnt
        FROM `{table_name}`
        GROUP BY {key_columns}
        HAVING COUNT(*) > 1
        LIMIT 5
    """

    result = db_api.execute(sql)
    if not result:
        return "未找到重复数据", sql

    return [dict(zip(list(primary_keys) + ["重复次数"], row)) for row in result], sql


def _remove_duplicate_keep_last(db_api, table_name, primary_keys):
    """
    删除重复数据，保留每组重复数据中的最后一条
    策略：使用子查询找到需要保留的记录ID，然后删除其他记录

    :param db_api: 数据库API对象
    :param table_name: 表名
    :param primary_keys: 主键列表
    :return: 删除的记录数量
    """
    print(f"开始清理表 {table_name} 中的重复数据，主键字段: {primary_keys}")

    key_columns = ", ".join(f"`{key}`" for key in primary_keys)

    # 使用所有列的比较来模拟行号
    print("使用临时表方式删除重复数据")

    # 获取所有列名
    all_columns_sql = f"""
        SELECT COLUMN_NAME 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() 
        AND TABLE_NAME = '{table_name}'
        ORDER BY ORDINAL_POSITION
    """
    all_columns_result = db_api.execute(all_columns_sql)
    all_columns = [row[0] for row in all_columns_result]
    all_columns_str = ", ".join(f"`{col}`" for col in all_columns)

    # 查询原数据表删除前已存在的数据量
    existing_count_sql = f"""
        SELECT COUNT(*) FROM `{table_name}`
    """
    existing_count_result = db_api.execute(existing_count_sql)
    existing_count_before = existing_count_result[0][0] if existing_count_result else 0
    print(f"删除前已存在的数据量: {existing_count_before}")

    # 创建临时表保存需要保留的记录
    temp_table = f"temp_dedup_{table_name}"

    # 删除可能存在的临时表
    try:
        db_api.execute(f"DROP TABLE IF EXISTS `{temp_table}`")
    except Exception:
        pass

    # 创建临时表并插入去重后的数据（每组保留一条）
    create_temp_sql = f"""
        CREATE TEMPORARY TABLE `{temp_table}` AS
        SELECT * FROM (
            SELECT t.*, 
                    ROW_NUMBER() OVER (
                        PARTITION BY {key_columns} 
                        ORDER BY (SELECT 0)
                    ) as rn
            FROM `{table_name}` t
        ) ranked
        WHERE rn = 1
    """

    try:
        db_api.execute(create_temp_sql)

        # 清空原表
        db_api.execute(f"TRUNCATE TABLE `{table_name}`")

        # 从临时表恢复数据
        restore_sql = f"""
            INSERT INTO `{table_name}` ({all_columns_str})
            SELECT {all_columns_str} FROM `{temp_table}`
        """
        db_api.execute(restore_sql)

        # 查询删除后数据表的数据量
        existing_count_sql = f"""
            SELECT COUNT(*) FROM `{table_name}`
        """
        existing_count_result = db_api.execute(existing_count_sql)
        existing_count_after = (
            existing_count_result[0][0] if existing_count_result else 0
        )
        print(f"删除后已存在的数据量: {existing_count_after}")

        # 计算删除的行数
        deleted_count = existing_count_before - existing_count_after
        print(f"删除的行数: {deleted_count}")

        # 删除临时表
        db_api.execute(f"DROP TABLE IF EXISTS `{temp_table}`")

        print("使用临时表方式完成重复数据清理")
        return deleted_count

    except Exception as e:
        print(f"重复数据删除失败: {e}")
        raise


def _escape_sql_value(value) -> str:
    """
    转义 SQL 值，防止 SQL 注入
    :param value: 原始值
    :return: 转义后的字符串
    """
    # return str(value).replace(chr(39), chr(39) + chr(39))
    return value
    

def _build_tuple_in_clause(batch_df: pd.DataFrame, primary_keys: list) -> str:
    """
    构建元组 IN 查询条件，用于多主键场景
    示例: (key1, key2) IN (('v1', 'v2'), ('v3', 'v4'))

    :param batch_df: 批次数据
    :param primary_keys: 主键列表
    :return: WHERE 子句
    """
    key_columns = ", ".join(f"`{key}`" for key in primary_keys)

    # 构建值元组列表
    value_tuples = []
    for _, row in batch_df.iterrows():
        values = ", ".join(f"'{_escape_sql_value(row[key])}'" for key in primary_keys)
        value_tuples.append(f"({values})")

    values_clause = ", ".join(value_tuples)
    return f"({key_columns}) IN ({values_clause})"


def _build_or_conditions_clause(batch_df: pd.DataFrame, primary_keys: list) -> str:
    """
    构建 OR 条件查询子句（降级方案）
    示例: (key1='v1' AND key2='v2') OR (key1='v3' AND key2='v4')

    :param batch_df: 批次数据
    :param primary_keys: 主键列表
    :return: WHERE 子句
    """
    conditions = []
    for _, row in batch_df.iterrows():
        key_conditions = " AND ".join(
            f"`{key}` = '{_escape_sql_value(row[key])}'" for key in primary_keys
        )
        conditions.append(f"({key_conditions})")
    return " OR ".join(conditions)


def _query_existing_count_with_retry(
    db_api, table_name: str, unique_df: pd.DataFrame, primary_keys: list
) -> int:
    """
    查询已存在记录数量，支持自动降级策略

    策略优先级：
    1. 元组 IN 查询（批次大小 500）- 最高效
    2. 元组 IN 查询（批次大小 100）- 中等批次
    3. OR 条件查询（批次大小 50）- 降级方案
    4. OR 条件查询（批次大小 10）- 最小批次

    :param db_api: 数据库 API
    :param table_name: 表名
    :param unique_df: 去重后的数据
    :param primary_keys: 主键列表
    :return: 已存在记录数量
    """
    strategies = [
        ("tuple_in", 500, _build_tuple_in_clause),
        ("tuple_in", 100, _build_tuple_in_clause),
        ("or_conditions", 50, _build_or_conditions_clause),
        ("or_conditions", 10, _build_or_conditions_clause),
    ]

    last_error = None

    for strategy_name, batch_size, build_clause_func in strategies:
        try:
            existing_count = 0

            for i in range(0, len(unique_df), batch_size):
                batch_df = unique_df.iloc[i : i + batch_size]
                where_clause = build_clause_func(batch_df, primary_keys)

                sql = f"""
                    SELECT COUNT(*) FROM `{table_name}`
                    WHERE {where_clause}
                """

                result = db_api.execute(sql)
                existing_count += result[0][0] if result else 0

            print(f"数据存在性检查完成 - 策略: {strategy_name}, 批次大小: {batch_size}")
            return existing_count

        except Exception as e:
            last_error = e
            error_msg = str(e).lower()

            # 判断是否为条件数量限制相关的错误
            if any(
                keyword in error_msg
                for keyword in [
                    "too many",
                    "limit",
                    "exceed",
                    "condition",
                    "expression",
                    "overflow",
                    "max_allowed",
                ]
            ):
                print(
                    f"查询策略 [{strategy_name}, batch={batch_size}] 失败，尝试降级: {e}"
                )
                continue
            else:
                # 非条件数量限制的错误，直接抛出
                print(f"查询已存在数据出现异常，停止已有数据校验: {e}")
                return 0

    # 所有策略都失败
    print(
        f"<查询已存在数据>所有查询策略均失败。最后错误: {last_error}"
    )
    return 0


def check_existing_records(
    db_api, table_name, df: pd.DataFrame, primary_keys: list, delete_before_upload: bool, is_tran: bool
):
    """
    根据唯一索引检查哪些数据已存在（需要更新），哪些是新增数据

    使用元组 IN 查询优化性能，支持自动降级策略应对云数据库限制

    :param db_api: 数据库API对象
    :param table_name: 表名
    :param df: 待写入的数据
    :param primary_keys: 业务主键列表
    :param delete_before_upload:
    :return: (insert_count, update_count, duplicate_in_source_count)
             insert_count: 新增数据行数
             update_count: 更新数据行数
             duplicate_in_source_count: 源数据中重复的行数
    """
    if df.empty:
        return 0, 0, 0

    if not primary_keys or delete_before_upload:
        print("警告：此任务唯一键为空或开启上传前删除，跳过数据源唯一性检查。")
        return len(df), 0, 0

    # 检查源数据中是否有重复的业务键
    source_duplicates = df.duplicated(subset=primary_keys, keep="first")
    duplicate_in_source_count = source_duplicates.sum()

    if duplicate_in_source_count > 0:
        # 获取重复的业务键示例
        duplicate_rows = df[source_duplicates].head(2)
        duplicate_keys = duplicate_rows[primary_keys].to_dict("records")
        shop = global_dict.get("task_configs", {}).get("shop")
        message = f"Table: {table_name}\n源数据：{len(df)} 行, 重复: {duplicate_in_source_count} 行；这些数据将被后出现的行覆盖。\n店铺: {shop}\n重复键示例: {duplicate_keys}"
        print(message)

        # 发送飞书提醒
        precheck_notice_count, _, _ = xbot_visual.asset.get_asset(asset_name="DataSavePrecheckNoticeCount", asset_type="txt", encrypt_flag="0", asset_info="{\"asset_id\":\"f453304e-1eeb-4e9c-8811-b571b45be5b0\",\"asset_template\":null}", _block=("main", 3, "获取资产"))
        if duplicate_in_source_count > int(precheck_notice_count) and not is_tran:
            precheck_message_notice(message, global_dict.get("extraJson"))

    # 去重后的有效数据行数
    unique_df = df.drop_duplicates(subset=primary_keys, keep="last")
    total_unique_rows = len(unique_df)

    # 使用带重试的查询策略
    existing_count = _query_existing_count_with_retry(
        db_api, table_name, unique_df, primary_keys
    )

    insert_count = total_unique_rows - existing_count
    update_count = existing_count

    print(
        f"数据写入预检查 - 总行数: {len(df)}, 去重后: {total_unique_rows}, "
        f"新增: {insert_count}, 更新: {update_count}, 源数据重复: {duplicate_in_source_count}"
    )

    return insert_count, update_count, duplicate_in_source_count


def verify_data_write(
    affected_rows: int,
    insert_count: int,
    update_count: int,
    duplicate_in_source: int,
    primary_keys: list,
):
    """
    验证数据写入结果

    MySQL INSERT ... ON DUPLICATE KEY UPDATE 的 rowcount 规则:
    - 新增一行: 返回 1
    - 更新一行(值有变化): 返回 2
    - 更新一行(值无变化): 返回 0

    验证逻辑:
    - 新增数据: affected_rows 必须包含 insert_count (每行贡献1)
    - 更新数据: affected_rows 可以有偏差 (每行贡献0~2)

    :param affected_rows: 实际受影响的行数
    :param insert_count: 预期新增的数据行数
    :param update_count: 预期更新的数据行数
    :param duplicate_in_source: 源数据中重复的行数
    :param primary_keys: 业务主键列表
    :return: None, 但会根据情况抛出 warning 或 error 日志
    """
    # 计算预期的 affected_rows 范围
    # 最小值: insert_count + 0 (所有更新都无变化)
    # 最大值: insert_count + 2 * update_count (所有更新都有变化)
    min_expected = insert_count
    max_expected = insert_count + 2 * update_count

    print(
        f"数据写入验证 - 实际影响行数: {affected_rows}, "
        f"预期新增: {insert_count}, 预期更新: {update_count}, "
        f"预期范围: [{min_expected}, {max_expected}]"
    )

    # 源数据重复检查
    if duplicate_in_source > 0:
        print(
            f"数据写入警告: 源数据存在 {duplicate_in_source} 行重复业务键 {primary_keys}，"
            f"重复数据已被覆盖处理"
        )

    # 新增数据验证: affected_rows 必须 >= insert_count
    # 因为每条新增记录贡献 1 到 affected_rows
    if affected_rows < insert_count:
        # 新增数据数量不匹配，这是严重错误
        error_msg = (
            f"数据写入错误: 新增数据验证失败！"
            f"预期新增 {insert_count} 行，但实际影响行数 {affected_rows} 不足。"
            f"可能原因: 1) 唯一索引配置错误 2) 数据库写入异常 3) 业务键 {primary_keys} 存在问题"
        )
        print(error_msg)
        raise ValueError(error_msg)

    # 更新数据验证: affected_rows 应在 [min_expected, max_expected] 范围内
    if affected_rows > max_expected:
        # 超出预期范围，可能存在问题
        print(
            f"数据写入警告: 影响行数 {affected_rows} 超出预期范围 [{min_expected}, {max_expected}]。"
            f"可能原因: 业务键 {primary_keys} 配置发生变化"
        )
    elif affected_rows < max_expected:
        # 在范围内但不是最大值，说明部分更新数据无变化
        unchanged_updates = max_expected - affected_rows
        if unchanged_updates > 0:
            print(f"数据写入统计: 约 {unchanged_updates} 行更新数据无变化（值相同）")

    # 计算实际的新增和更新统计
    # affected_rows = insert_count + update_with_change * 2 + update_without_change * 0
    # 简化计算
    actual_insert_contribution = insert_count
    update_contribution = affected_rows - actual_insert_contribution

    if update_count > 0 and update_contribution >= 0:
        print(f"数据写入完成: 新增 {insert_count} 行, 更新 {update_count} 行")
    else:
        print(f"数据写入完成: 新增 {insert_count} 行")


def parse_delete_conditions_dict(df: pd.DataFrame, primary_keys: list) -> list:
    """
    从数据中解析条件字典
    :param df:
    :param primary_keys:
    :return:
    """
    # 执行上传前删除必须存在dc_task_id 字段
    if len(primary_keys) < 3:
        raise Exception(
            "开启《上传前删除》需要最少指定 3个 去重主键字段进行where条件构建。"
        )

    if "dc_task_id" not in list(df.columns):
        raise Exception(
            "开启《上传前删除》上传文件必须存在字段《dc_task_id》!!! 请调用插入字段指令插入。"
        )
    unique_key = primary_keys + ["dc_task_id"]
    delete_df = df[unique_key]
    delete_df.drop_duplicates(keep="first", inplace=True)
    delete_df.fillna("", inplace=True)
    conditions = delete_df.to_dict(orient="records")
    print(f"移除数据条件: {len(conditions)} 个")
    return conditions


def delete_before_upload_check(
    write_count: int, delete_conditions: list, table_name: str, db_api: MysqlAPI
):
    """
    删除前上传数据量校验
    :param write_count: 写入数据量
    :param delete_conditions:
    :param table_name:
    :param db_api:
    :return:
    """
    delete_count = 0
    check_batch_size = 20

    for i in range(0, len(delete_conditions), check_batch_size):
        batch_conditions = delete_conditions[i : i + check_batch_size]

        where_clause = build_where_condition(batch_conditions)

        sql = f"""
            SELECT COUNT(*) FROM `{table_name}` 
            WHERE {where_clause}
        """

        result = db_api.execute(sql)
        delete_count += result[0][0] if result else 0

    # 计算差异比例
    ratio = (delete_count - write_count) / write_count

    if ratio > 0.1:
        message = (
            f"删除前数据量校验失败！表: {table_name}, "
            f"删除数据量({delete_count}) - 写入数据量({write_count}) = {delete_count - write_count}，"
            f"差异比例 {ratio:.2%} 超过阈值 10%。"
            f"请检查数据或联系管理员。"
        )
        print(message)
        # 发送飞书提醒
        # precheck_message_notice(message, global_dict.get("extraJson"))
        # raise ValueError(message)
    else:
        print(
            f"删除前数据量校验通过 - 删除数据量: {delete_count}, "
            f"写入数据量: {write_count}, 差异比例: {ratio:.2%}"
        )


def to_mysql(
    host,
    port,
    username,
    password,
    db_name,
    dataset_dict,
    primary_keys_list,
    is_translation,
    delete_before_upload,
):
    """
    入库动作
    :param host:
    :param port:
    :param username:
    :param password:
    :param db_name:
    :param dataset_dict:
    :param primary_keys_list:
    :param is_translation: False情况下代表向基础数据表写入数据
    :param delete_before_upload: 上传前删除
    :return:
    """
    global MAP_TRANSLATOR_TABLE

    print(f"TO MYSQL V2: in {db_name}")

    # 首次写入基础表时把配置表的数据库信息带上，否则后续映射表查不到
    if not is_translation and not MAP_TRANSLATOR_TABLE.startswith(f"{db_name}`"):
        MAP_TRANSLATOR_TABLE = f"{db_name}`.`{MAP_TRANSLATOR_TABLE}"

    dataset_name = dataset_dict["data_set"]
    file_path = dataset_dict["file_path"]

    # 上传文件对象初始化
    dataset = Dataset(
        data_set=dataset_name, file_path=file_path, primary_keys=primary_keys_list
    )

    if dataset.empty:
        return None, None

    # 底表数据库初始化
    db_api = MysqlAPI(host, port, username, password, db_name)

    try:
        # 配置表清理, 不存在的表从 map_dataset 和 map_translator 删除
        clear_config_table(db_api)

        # 入库表对象构建, 数据库不存在此表以此结构创建
        # 表结构配置转译，对象属性在此处进行赋值
        table = build_table(dataset, db_api, is_translation, delete_before_upload)

        table_name = dataset.table_name

        # 如果存在转译, 同步到待上传的DF
        dataset.df.rename(columns=table.rename_dict, inplace=True)

        # 清理字段非 varchar 类型的字段数据
        dataset.data_clean(table)

        sink_params = file_path, table, dataset, table_name, dataset_name

        # 查询底表数据库是否存在数据表, 不存在创建
        if not db_api.exists_table(table_name):
            # 创建表
            db_api.create_table(table)
            # 更新配置表信息
            config_table_update(dataset, db_api, table, is_translation)

            # 初次入库：检查源数据重复
            _, _, duplicate_in_source = check_existing_records(
                db_api, table_name, dataset.df, dataset.primary_keys, delete_before_upload, is_translation
            )
            insert_count = (
                len(
                    dataset.df.drop_duplicates(subset=dataset.primary_keys, keep="last")
                )
                if dataset.primary_keys
                else len(dataset.df)
            )

            # 上传数据
            affected_rows = db_api.update_value(dataset, is_translation, delete_before_upload)

            # 初次入库验证
            verify_data_write(
                affected_rows=affected_rows,
                insert_count=insert_count,
                update_count=0,
                duplicate_in_source=duplicate_in_source,
                primary_keys=dataset.primary_keys,
            )

            if not is_translation:
                print(f"初次入库完成，请在`{MAP_TRANSLATOR_TABLE}`配置转译信息！")
            return None, sink_params

        # 新增字段校验, 是否存在新增字段, 新增字段是否为转译字段, 字段是否存在格式转换
        new_fields_check(db_api, dataset, is_translation)

        # 字段类型校验, 是否存在字段类型修改
        fields_type_check(db_api, table, table_name, is_translation)

        # 唯一索引校验（替代主键校验）
        if table.key_type == KeyType.PRIMARY:
            primary_keys_check(db_api, dataset, table_name)
        else:
            unique_index_check(db_api, dataset, table_name, delete_before_upload)

        # 在此之前完成所有的前置动作，对象构建，字段映射，DataFrame构建等
        # 上传前删除动作 - 查询当前上传条件
        if delete_before_upload:
            delete_conditions = parse_delete_conditions_dict(dataset.df, dataset.primary_keys)

            # 删除前数据量校验：查询本次删除的数据量和写入数据量进行对比
            # (删除量 - 写入量) / 写入量 > 0.1 抛出异常警告，停止删除动作
            delete_before_upload_check(
                write_count=len(dataset.df),
                delete_conditions=delete_conditions,
                table_name=table_name,
                db_api=db_api,
            )

            # 执行上传前删除数据动作
            delete_batch_size = 20
            for i in range(0, len(delete_conditions), delete_batch_size):
                batch_conditions = delete_conditions[i: i + delete_batch_size]
                db_api.delete_data_by_conditions(
                    table_name=table_name, delete_conditions=batch_conditions
                )

        # 写入前检查：区分新增和更新数据
        insert_count, update_count, duplicate_in_source = check_existing_records(
            db_api, table_name, dataset.df, dataset.primary_keys, delete_before_upload, is_translation
        )

        # 数据写入，获取受影响行数
        affected_rows = db_api.update_value(dataset, is_translation, delete_before_upload)

        # 数据写入验证
        verify_data_write(
            affected_rows=affected_rows,
            insert_count=insert_count,
            update_count=update_count,
            duplicate_in_source=duplicate_in_source,
            primary_keys=dataset.primary_keys,
        )

        # 查询转译的db名称
        if not is_translation:
            # 临时使用，让所有旧客户表内增加入库信息，后续需删除
            config_table_update(dataset, db_api, table, is_translation)

            return tran_db_name(db_api, table_name), sink_params

        return None, sink_params

    finally:
        db_api.close()



def run(host, port, username, password, db_name, dataset_dict, primary_keys_list, is_translation, delete_before_upload):
    # 确认客户是否为老客， 老客直接进入旧入库流程
    company_id = global_dict.get("task_configs", {}).get("company_id")
    if is_old_customer(company_id):
        print("转译字段更新老客，v1入库")

        from .init_mysql import main as init_mysql_v1
        from .to_mysql import main as to_mysql_v1
        db_tool_v1 = init_mysql_v1(
            {
                "user": username,
                "password": password,
                "host": host,
                "port": port,
                "dbName": db_name
            }
        )
        to_mysql_v1(
            {
                "上传文件对象": dataset_dict,
                "db": db_tool_v1,
                "去重主键列表": primary_keys_list,
                "是否转译": is_translation
            }
        )
        return

    sink_params = None
    if is_translation:
        # 转译先在底层数据库进行一次入库
        # 查询转译数据库名称
        tran_db, sink_params = to_mysql(
            host,
            port,
            username,
            password,
            db_name,
            dataset_dict,
            primary_keys_list,
            is_translation=False,
            delete_before_upload=delete_before_upload,
        )
        db_name = tran_db

    # 入库转译数据
    # 2025-10-22：保存落地信息，保存上传信息
    if db_name:
        _, sink_params = to_mysql(
            host,
            port,
            username,
            password,
            db_name,
            dataset_dict,
            primary_keys_list,
            is_translation,
            delete_before_upload=delete_before_upload,
        )

    # 2025-10-22: 上传结果保存
    # 1. 保存上传表信息
    if sink_params is not None:
        file_path, table, dataset, table_name, dataset_name = sink_params
        save_table_struct(
            table_name=table_name, 
            dataset_name=dataset_name,
            table_columns=[
                {"fieldName": f.name, "fieldType": f.type, "fieldDesc": f.comment}
                for f in table.fields
            ], 
            primary_keys=table.primary_keys
        )
        # 2. 保存上传落地信息
        save_sink_result(file_path, table, dataset, table_name)


def save_sink_result(file_path, table, dataset, table_name):
    check_result = global_dict.get("date_check", {}).get(file_path)
    if check_result is None:
        print(f"WARNING：未找到文件日期校验结果: {file_path}")
        return

    print(f"文件日期校验信息: {check_result}")

    date_field = table.rename_dict.get(check_result["field_name"]) or check_result["field_name"]
    date_format = check_result["date_format"]

    # 3. 将日期格式化为标准格式
    dataset.df["temp_column"] = pd.to_datetime(
        dataset.df[date_field], format=date_format, errors="coerce"
    ).map(lambda x: datetime.strftime(x, "%Y-%m-%d") if pd.notna(x) else None)

    dataset.df.dropna(subset=["temp_column"], inplace=True)

    # 4. 拆分文件并上传
    for date_str, sub_df in dataset.df.groupby("temp_column"):
        # 跳过格式化失败的文件日期
        if not date_str:
            continue

        upload_sink_info(
            sink_target=table_name,
            sink_count=len(sub_df), 
            date=date_str, 
            table_name=table_name
        )

    # 5. 上传无数据状态
    date_check_result = check_result['result']
    if not isinstance(date_check_result, dict):
        return 
    for date_str, status in date_check_result.items():
        if status in ("not_present", "no_data"):
            upload_sink_info(
            sink_target=table_name,
            sink_count=0, 
            date=date_str, 
            table_name=table_name
        )


def ai_translate(chinese):
    """
    字段转译
    :param chinese:
    :return:
    """

    API_URL = "https://power-api.yingdao.com/oapi/power/v1/rest/flow/442ee262-c112-4d1f-a573-fec98cf61dc7/execute"
    headers = {
        'Authorization': 'Bearer AP_mHFbpoobLt6hNnhc',
        'Content-Type': 'application/json'
    }

    def query(payload):
        response = requests.post(API_URL, headers=headers, json=payload)
        return response.json()

    output = query({"input": {"input_text_0": chinese}})
    return output['data']['result']['english']



def main(args):
    run(**args)

    # run(
    #     username="root",
    #     password="123123",
    #     host="localhost",
    #     port=3306,
    #     db_name="test_db",
    #     dataset_dict={
    #         "data_set": "测试数据集_测试字段更新",
    #         "file_path": r"D:\Project\connect-dev\数据存储\a.xlsx",
    #     },
    #     primary_keys_list=["主订单编号", "子订单编号", "dc_task_id"],
    #     is_translation=False,
    #     delete_before_upload=False
    # )
