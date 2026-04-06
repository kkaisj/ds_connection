-- DC 数据连接器 - 存储类型字段扩展
-- 将 ENUM 改为 VARCHAR 以支持更多存储类型（如 email）
-- 用法: mysql -u root -p dc_connection < alter_storage_type.sql

SET NAMES utf8mb4;
USE dc_connection;

ALTER TABLE storage_config
  MODIFY COLUMN type VARCHAR(64) NOT NULL COMMENT '存储类型: mysql/feishu_bitable/dingtalk_sheet/email';
