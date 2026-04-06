-- DC 数据连接器 - 软删除字段迁移
-- 给业务表添加 is_deleted 字段
-- 用法: mysql -u root -p dc_connection < add_soft_delete.sql

USE dc_connection;

-- 平台表
ALTER TABLE platform
  ADD COLUMN is_deleted TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除标记' AFTER parent_id;

-- 连接应用表
ALTER TABLE connector_app
  ADD COLUMN is_deleted TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除标记' AFTER description;

-- 店铺账号表
ALTER TABLE shop_account
  ADD COLUMN is_deleted TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除标记' AFTER health_score;

-- 存储配置表
ALTER TABLE storage_config
  ADD COLUMN is_deleted TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除标记' AFTER status;

-- 通知配置表
ALTER TABLE notification_config
  ADD COLUMN is_deleted TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除标记' AFTER status;

-- 任务实例表
ALTER TABLE task_instance
  ADD COLUMN is_deleted TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除标记' AFTER next_run_at;
