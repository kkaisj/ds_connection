-- DC 数据连接器 - 添加验证码转发字段
-- 用法: mysql -u root -p dc_connection < add_captcha.sql

SET NAMES utf8mb4;
USE dc_connection;

ALTER TABLE shop_account
  ADD COLUMN captcha_method ENUM('none','sms_forward','email_forward','email_auth_code','manual')
    NOT NULL DEFAULT 'none' COMMENT '验证码转发方式' AFTER health_score,
  ADD COLUMN captcha_config JSON NULL COMMENT '验证码转发配置参数' AFTER captcha_method,
  ADD COLUMN captcha_enabled TINYINT(1) NOT NULL DEFAULT 0 COMMENT '验证码转发开关' AFTER captcha_config;
