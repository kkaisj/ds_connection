-- DC 数据连接器 - 初始化脚本
-- 用法: mysql -u root -p < init.sql

SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- ========================================
-- 1. 建库
-- ========================================
CREATE DATABASE IF NOT EXISTS dc_connection
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE dc_connection;

-- ========================================
-- 2. 建表（来自 schema.sql）
-- ========================================

CREATE TABLE IF NOT EXISTS platform (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  code VARCHAR(64) NOT NULL UNIQUE,
  name VARCHAR(128) NOT NULL,
  parent_id BIGINT NULL,
  is_deleted TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除标记',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_platform_parent_id (parent_id)
);

CREATE TABLE IF NOT EXISTS connector_app (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  platform_id BIGINT NOT NULL,
  name VARCHAR(128) NOT NULL,
  adapter_key VARCHAR(128) NULL COMMENT 'DrissionPage 适配器标识',
  version VARCHAR(64) NOT NULL,
  status ENUM('active','inactive') NOT NULL DEFAULT 'active',
  param_schema JSON NULL,
  description VARCHAR(500) NULL,
  is_deleted TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除标记',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_connector_app_platform FOREIGN KEY (platform_id) REFERENCES platform(id),
  KEY idx_connector_app_platform_id (platform_id),
  KEY idx_connector_app_status (status)
);

CREATE TABLE IF NOT EXISTS shop_account (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  platform_id BIGINT NOT NULL,
  shop_name VARCHAR(128) NOT NULL,
  username_enc VARBINARY(512) NOT NULL,
  password_enc VARBINARY(512) NOT NULL,
  extra_enc VARBINARY(2048) NULL,
  status ENUM('active','inactive','disabled') NOT NULL DEFAULT 'active',
  health_score INT NOT NULL DEFAULT 100,
  captcha_method ENUM('none','sms_forward','email_forward','email_auth_code','manual') NOT NULL DEFAULT 'none' COMMENT '验证码转发方式',
  captcha_config JSON NULL COMMENT '验证码转发配置参数',
  captcha_enabled TINYINT(1) NOT NULL DEFAULT 0 COMMENT '验证码转发开关',
  is_deleted TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除标记',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_shop_account_platform FOREIGN KEY (platform_id) REFERENCES platform(id),
  KEY idx_shop_account_platform_id (platform_id),
  KEY idx_shop_account_status (status)
);

CREATE TABLE IF NOT EXISTS storage_config (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  type VARCHAR(64) NOT NULL COMMENT '存储类型: mysql/feishu_bitable/dingtalk_sheet/email',
  name VARCHAR(128) NOT NULL,
  config_enc VARBINARY(4096) NOT NULL,
  status ENUM('active','inactive') NOT NULL DEFAULT 'active',
  is_deleted TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除标记',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_storage_config_type (type),
  KEY idx_storage_config_status (status)
);

CREATE TABLE IF NOT EXISTS notification_config (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  channel ENUM('feishu','dingtalk','wechat_work') NOT NULL,
  webhook_url_enc VARBINARY(1024) NOT NULL,
  notify_on_fail TINYINT(1) NOT NULL DEFAULT 1,
  notify_on_retry_fail TINYINT(1) NOT NULL DEFAULT 1,
  notify_on_account_invalid TINYINT(1) NOT NULL DEFAULT 1,
  dedupe_window_sec INT NOT NULL DEFAULT 300,
  rate_limit_per_min INT NOT NULL DEFAULT 20,
  status ENUM('active','inactive') NOT NULL DEFAULT 'active',
  is_deleted TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除标记',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_notification_config_channel (channel),
  KEY idx_notification_config_status (status)
);

CREATE TABLE IF NOT EXISTS task_instance (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  app_id BIGINT NOT NULL,
  account_id BIGINT NOT NULL,
  storage_config_id BIGINT NOT NULL,
  notification_config_id BIGINT NOT NULL,
  name VARCHAR(128) NOT NULL,
  cron_expr VARCHAR(64) NOT NULL,
  timezone VARCHAR(64) NOT NULL DEFAULT 'Asia/Shanghai',
  status ENUM('enabled','paused') NOT NULL DEFAULT 'enabled',
  params JSON NULL,
  last_run_at DATETIME NULL,
  next_run_at DATETIME NULL,
  is_deleted TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除标记',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_task_instance_app FOREIGN KEY (app_id) REFERENCES connector_app(id),
  CONSTRAINT fk_task_instance_account FOREIGN KEY (account_id) REFERENCES shop_account(id),
  CONSTRAINT fk_task_instance_storage FOREIGN KEY (storage_config_id) REFERENCES storage_config(id),
  CONSTRAINT fk_task_instance_notification FOREIGN KEY (notification_config_id) REFERENCES notification_config(id),
  KEY idx_task_instance_app_id (app_id),
  KEY idx_task_instance_account_id (account_id),
  KEY idx_task_instance_status (status),
  KEY idx_task_instance_next_run_at (next_run_at)
);

CREATE TABLE IF NOT EXISTS task_run (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  task_id BIGINT NOT NULL,
  trigger_type ENUM('scheduler','manual','retry') NOT NULL,
  status ENUM('pending','running','success','failed','cancelled') NOT NULL DEFAULT 'pending',
  retry_count INT NOT NULL DEFAULT 0,
  idempotency_key VARCHAR(128) NULL,
  started_at DATETIME NULL,
  ended_at DATETIME NULL,
  duration_ms BIGINT NULL,
  error_code VARCHAR(64) NULL,
  error_message VARCHAR(1000) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_task_run_task FOREIGN KEY (task_id) REFERENCES task_instance(id),
  UNIQUE KEY uk_task_run_idempotency_key (idempotency_key),
  KEY idx_task_run_task_id (task_id),
  KEY idx_task_run_status (status),
  KEY idx_task_run_started_at (started_at)
);

CREATE TABLE IF NOT EXISTS task_run_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  run_id BIGINT NOT NULL,
  step VARCHAR(64) NOT NULL,
  level ENUM('INFO','WARN','ERROR') NOT NULL,
  message VARCHAR(2000) NOT NULL,
  ext JSON NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_task_run_log_run FOREIGN KEY (run_id) REFERENCES task_run(id),
  KEY idx_task_run_log_run_id (run_id),
  KEY idx_task_run_log_level (level)
);

CREATE TABLE IF NOT EXISTS audit_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  actor_id VARCHAR(64) NOT NULL,
  action VARCHAR(128) NOT NULL,
  target_type VARCHAR(64) NOT NULL,
  target_id VARCHAR(64) NOT NULL,
  payload JSON NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_audit_log_actor_id (actor_id),
  KEY idx_audit_log_target (target_type, target_id),
  KEY idx_audit_log_created_at (created_at)
);

-- ========================================
-- 3. 种子数据
-- ========================================

-- 平台
INSERT INTO platform (id, code, name) VALUES
  (1, 'taobao',  '淘宝天猫'),
  (2, 'jd',      '京东'),
  (3, 'pdd',     '拼多多'),
  (4, 'douyin',  '抖音');

-- 连接应用
INSERT INTO connector_app (id, platform_id, name, adapter_key, version, description) VALUES
  (1, 1, '订单数据采集', 'taobao.order_sync',       '1.0.0', '采集淘宝天猫订单数据'),
  (2, 1, '物流轨迹更新', 'taobao.logistics_track',  '1.0.0', '更新淘宝天猫物流信息'),
  (3, 2, '商品库存同步', 'jd.product_stock_sync',    '1.0.0', '同步京东商品库存'),
  (4, 2, '退款数据同步', 'jd.refund_sync',           '1.0.0', '同步京东退款记录'),
  (5, 3, '评价数据抓取', 'pdd.review_scrape',        '1.0.0', '抓取拼多多评价数据'),
  (6, 4, '流量数据采集', 'douyin.traffic_analytics', '1.0.0', '采集抖音流量数据');

-- 店铺账号（enc 字段用占位值）
INSERT INTO shop_account (id, platform_id, shop_name, username_enc, password_enc, status, health_score) VALUES
  (1, 1, '旗舰店 A', X'656E635F7573657231', X'656E635F7061737331', 'active',   100),
  (2, 1, '旗舰店 B', X'656E635F7573657232', X'656E635F7061737332', 'active',   95),
  (3, 2, '自营店铺',  X'656E635F7573657233', X'656E635F7061737333', 'active',   88),
  (4, 3, '百货专营',  X'656E635F7573657234', X'656E635F7061737334', 'inactive', 30),
  (5, 4, '品牌旗舰',  X'656E635F7573657235', X'656E635F7061737335', 'active',   92);

-- 存储配置
INSERT INTO storage_config (id, type, name, config_enc) VALUES
  (1, 'mysql', '业务主库', X'656E635F636F6E666967');

-- 通知配置
INSERT INTO notification_config (id, channel, webhook_url_enc) VALUES
  (1, 'feishu', X'656E635F776562686F6F6B');

-- 任务实例（6 个任务，全部 enabled）
INSERT INTO task_instance (id, app_id, account_id, storage_config_id, notification_config_id, name, cron_expr) VALUES
  (1, 1, 1, 1, 1, '订单数据采集', '0 8 * * *'),
  (2, 2, 2, 1, 1, '物流轨迹更新', '0 8 * * *'),
  (3, 3, 3, 1, 1, '商品库存同步', '0 8 * * *'),
  (4, 4, 3, 1, 1, '退款数据同步', '0 8 * * *'),
  (5, 5, 4, 1, 1, '评价数据抓取', '0 8 * * *'),
  (6, 6, 5, 1, 1, '流量数据采集', '0 8 * * *');

-- ========================================
-- 执行记录（最近 7 天，每任务每天 1 条）
-- 日期使用相对计算：CURDATE() - INTERVAL N DAY
-- ========================================

-- 辅助变量：生成 7 天 × 6 任务 = 42 条记录
-- 第 7 天前 → 今天

INSERT INTO task_run (task_id, trigger_type, status, started_at, ended_at, duration_ms, error_code, error_message) VALUES
-- Day -6 (6天前)
(1, 'scheduler', 'success', DATE_SUB(CURDATE(), INTERVAL 6 DAY) + INTERVAL 8 HOUR + INTERVAL 2 MINUTE,  DATE_SUB(CURDATE(), INTERVAL 6 DAY) + INTERVAL 8 HOUR + INTERVAL 2 MINUTE + INTERVAL 12 SECOND, 12400, NULL, NULL),
(2, 'scheduler', 'success', DATE_SUB(CURDATE(), INTERVAL 6 DAY) + INTERVAL 8 HOUR + INTERVAL 5 MINUTE,  DATE_SUB(CURDATE(), INTERVAL 6 DAY) + INTERVAL 8 HOUR + INTERVAL 5 MINUTE + INTERVAL 8 SECOND,   8200, NULL, NULL),
(3, 'scheduler', 'success', DATE_SUB(CURDATE(), INTERVAL 6 DAY) + INTERVAL 8 HOUR + INTERVAL 10 MINUTE, DATE_SUB(CURDATE(), INTERVAL 6 DAY) + INTERVAL 8 HOUR + INTERVAL 10 MINUTE + INTERVAL 15 SECOND, 15300, NULL, NULL),
(4, 'scheduler', 'success', DATE_SUB(CURDATE(), INTERVAL 6 DAY) + INTERVAL 8 HOUR + INTERVAL 12 MINUTE, DATE_SUB(CURDATE(), INTERVAL 6 DAY) + INTERVAL 8 HOUR + INTERVAL 12 MINUTE + INTERVAL 5 SECOND,  5200, NULL, NULL),
(5, 'scheduler', 'failed',  DATE_SUB(CURDATE(), INTERVAL 6 DAY) + INTERVAL 8 HOUR + INTERVAL 15 MINUTE, DATE_SUB(CURDATE(), INTERVAL 6 DAY) + INTERVAL 8 HOUR + INTERVAL 15 MINUTE + INTERVAL 3 SECOND,  3100, 'CAPTCHA_EXPIRED', '验证码已过期'),
(6, 'scheduler', 'success', DATE_SUB(CURDATE(), INTERVAL 6 DAY) + INTERVAL 8 HOUR + INTERVAL 18 MINUTE, DATE_SUB(CURDATE(), INTERVAL 6 DAY) + INTERVAL 8 HOUR + INTERVAL 18 MINUTE + INTERVAL 9 SECOND,  9100, NULL, NULL),

-- Day -5
(1, 'scheduler', 'success', DATE_SUB(CURDATE(), INTERVAL 5 DAY) + INTERVAL 8 HOUR + INTERVAL 1 MINUTE,  DATE_SUB(CURDATE(), INTERVAL 5 DAY) + INTERVAL 8 HOUR + INTERVAL 1 MINUTE + INTERVAL 11 SECOND, 11200, NULL, NULL),
(2, 'scheduler', 'success', DATE_SUB(CURDATE(), INTERVAL 5 DAY) + INTERVAL 8 HOUR + INTERVAL 4 MINUTE,  DATE_SUB(CURDATE(), INTERVAL 5 DAY) + INTERVAL 8 HOUR + INTERVAL 4 MINUTE + INTERVAL 7 SECOND,   7800, NULL, NULL),
(3, 'scheduler', 'success', DATE_SUB(CURDATE(), INTERVAL 5 DAY) + INTERVAL 8 HOUR + INTERVAL 8 MINUTE,  DATE_SUB(CURDATE(), INTERVAL 5 DAY) + INTERVAL 8 HOUR + INTERVAL 8 MINUTE + INTERVAL 14 SECOND, 14100, NULL, NULL),
(4, 'scheduler', 'success', DATE_SUB(CURDATE(), INTERVAL 5 DAY) + INTERVAL 8 HOUR + INTERVAL 11 MINUTE, DATE_SUB(CURDATE(), INTERVAL 5 DAY) + INTERVAL 8 HOUR + INTERVAL 11 MINUTE + INTERVAL 6 SECOND,  6300, NULL, NULL),
(5, 'scheduler', 'success', DATE_SUB(CURDATE(), INTERVAL 5 DAY) + INTERVAL 8 HOUR + INTERVAL 14 MINUTE, DATE_SUB(CURDATE(), INTERVAL 5 DAY) + INTERVAL 8 HOUR + INTERVAL 14 MINUTE + INTERVAL 10 SECOND, 10400, NULL, NULL),
(6, 'scheduler', 'success', DATE_SUB(CURDATE(), INTERVAL 5 DAY) + INTERVAL 8 HOUR + INTERVAL 17 MINUTE, DATE_SUB(CURDATE(), INTERVAL 5 DAY) + INTERVAL 8 HOUR + INTERVAL 17 MINUTE + INTERVAL 8 SECOND,  8700, NULL, NULL),

-- Day -4
(1, 'scheduler', 'success', DATE_SUB(CURDATE(), INTERVAL 4 DAY) + INTERVAL 8 HOUR + INTERVAL 3 MINUTE,  DATE_SUB(CURDATE(), INTERVAL 4 DAY) + INTERVAL 8 HOUR + INTERVAL 3 MINUTE + INTERVAL 13 SECOND, 13200, NULL, NULL),
(2, 'scheduler', 'success', DATE_SUB(CURDATE(), INTERVAL 4 DAY) + INTERVAL 8 HOUR + INTERVAL 6 MINUTE,  DATE_SUB(CURDATE(), INTERVAL 4 DAY) + INTERVAL 8 HOUR + INTERVAL 6 MINUTE + INTERVAL 9 SECOND,   9400, NULL, NULL),
(3, 'scheduler', 'failed',  DATE_SUB(CURDATE(), INTERVAL 4 DAY) + INTERVAL 8 HOUR + INTERVAL 9 MINUTE,  DATE_SUB(CURDATE(), INTERVAL 4 DAY) + INTERVAL 8 HOUR + INTERVAL 9 MINUTE + INTERVAL 2 SECOND,  2300, 'PAGE_CHANGED', '页面结构变化'),
(4, 'scheduler', 'success', DATE_SUB(CURDATE(), INTERVAL 4 DAY) + INTERVAL 8 HOUR + INTERVAL 13 MINUTE, DATE_SUB(CURDATE(), INTERVAL 4 DAY) + INTERVAL 8 HOUR + INTERVAL 13 MINUTE + INTERVAL 5 SECOND,  5600, NULL, NULL),
(5, 'scheduler', 'failed',  DATE_SUB(CURDATE(), INTERVAL 4 DAY) + INTERVAL 8 HOUR + INTERVAL 16 MINUTE, DATE_SUB(CURDATE(), INTERVAL 4 DAY) + INTERVAL 8 HOUR + INTERVAL 16 MINUTE + INTERVAL 4 SECOND,  4100, 'CAPTCHA_EXPIRED', '验证码已过期'),
(6, 'scheduler', 'success', DATE_SUB(CURDATE(), INTERVAL 4 DAY) + INTERVAL 8 HOUR + INTERVAL 19 MINUTE, DATE_SUB(CURDATE(), INTERVAL 4 DAY) + INTERVAL 8 HOUR + INTERVAL 19 MINUTE + INTERVAL 7 SECOND,  7200, NULL, NULL),

-- Day -3
(1, 'scheduler', 'success', DATE_SUB(CURDATE(), INTERVAL 3 DAY) + INTERVAL 8 HOUR + INTERVAL 0 MINUTE,  DATE_SUB(CURDATE(), INTERVAL 3 DAY) + INTERVAL 8 HOUR + INTERVAL 0 MINUTE + INTERVAL 12 SECOND, 12100, NULL, NULL),
(2, 'scheduler', 'success', DATE_SUB(CURDATE(), INTERVAL 3 DAY) + INTERVAL 8 HOUR + INTERVAL 3 MINUTE,  DATE_SUB(CURDATE(), INTERVAL 3 DAY) + INTERVAL 8 HOUR + INTERVAL 3 MINUTE + INTERVAL 8 SECOND,   8500, NULL, NULL),
(3, 'scheduler', 'success', DATE_SUB(CURDATE(), INTERVAL 3 DAY) + INTERVAL 8 HOUR + INTERVAL 7 MINUTE,  DATE_SUB(CURDATE(), INTERVAL 3 DAY) + INTERVAL 8 HOUR + INTERVAL 7 MINUTE + INTERVAL 16 SECOND, 16200, NULL, NULL),
(4, 'scheduler', 'success', DATE_SUB(CURDATE(), INTERVAL 3 DAY) + INTERVAL 8 HOUR + INTERVAL 10 MINUTE, DATE_SUB(CURDATE(), INTERVAL 3 DAY) + INTERVAL 8 HOUR + INTERVAL 10 MINUTE + INTERVAL 4 SECOND,  4800, NULL, NULL),
(5, 'scheduler', 'success', DATE_SUB(CURDATE(), INTERVAL 3 DAY) + INTERVAL 8 HOUR + INTERVAL 13 MINUTE, DATE_SUB(CURDATE(), INTERVAL 3 DAY) + INTERVAL 8 HOUR + INTERVAL 13 MINUTE + INTERVAL 11 SECOND, 11300, NULL, NULL),
(6, 'scheduler', 'failed',  DATE_SUB(CURDATE(), INTERVAL 3 DAY) + INTERVAL 8 HOUR + INTERVAL 16 MINUTE, DATE_SUB(CURDATE(), INTERVAL 3 DAY) + INTERVAL 8 HOUR + INTERVAL 16 MINUTE + INTERVAL 3 SECOND,  3500, 'TIMEOUT', '采集超时'),

-- Day -2
(1, 'scheduler', 'success', DATE_SUB(CURDATE(), INTERVAL 2 DAY) + INTERVAL 8 HOUR + INTERVAL 1 MINUTE,  DATE_SUB(CURDATE(), INTERVAL 2 DAY) + INTERVAL 8 HOUR + INTERVAL 1 MINUTE + INTERVAL 10 SECOND, 10800, NULL, NULL),
(2, 'scheduler', 'success', DATE_SUB(CURDATE(), INTERVAL 2 DAY) + INTERVAL 8 HOUR + INTERVAL 4 MINUTE,  DATE_SUB(CURDATE(), INTERVAL 2 DAY) + INTERVAL 8 HOUR + INTERVAL 4 MINUTE + INTERVAL 9 SECOND,   9200, NULL, NULL),
(3, 'scheduler', 'success', DATE_SUB(CURDATE(), INTERVAL 2 DAY) + INTERVAL 8 HOUR + INTERVAL 8 MINUTE,  DATE_SUB(CURDATE(), INTERVAL 2 DAY) + INTERVAL 8 HOUR + INTERVAL 8 MINUTE + INTERVAL 13 SECOND, 13600, NULL, NULL),
(4, 'scheduler', 'success', DATE_SUB(CURDATE(), INTERVAL 2 DAY) + INTERVAL 8 HOUR + INTERVAL 11 MINUTE, DATE_SUB(CURDATE(), INTERVAL 2 DAY) + INTERVAL 8 HOUR + INTERVAL 11 MINUTE + INTERVAL 5 SECOND,  5100, NULL, NULL),
(5, 'scheduler', 'failed',  DATE_SUB(CURDATE(), INTERVAL 2 DAY) + INTERVAL 8 HOUR + INTERVAL 14 MINUTE, DATE_SUB(CURDATE(), INTERVAL 2 DAY) + INTERVAL 8 HOUR + INTERVAL 14 MINUTE + INTERVAL 3 SECOND,  3400, 'CAPTCHA_EXPIRED', '验证码已过期'),
(6, 'scheduler', 'success', DATE_SUB(CURDATE(), INTERVAL 2 DAY) + INTERVAL 8 HOUR + INTERVAL 17 MINUTE, DATE_SUB(CURDATE(), INTERVAL 2 DAY) + INTERVAL 8 HOUR + INTERVAL 17 MINUTE + INTERVAL 8 SECOND,  8900, NULL, NULL),

-- Day -1 (昨天)
(1, 'scheduler', 'success', DATE_SUB(CURDATE(), INTERVAL 1 DAY) + INTERVAL 8 HOUR + INTERVAL 2 MINUTE,  DATE_SUB(CURDATE(), INTERVAL 1 DAY) + INTERVAL 8 HOUR + INTERVAL 2 MINUTE + INTERVAL 11 SECOND, 11500, NULL, NULL),
(2, 'scheduler', 'success', DATE_SUB(CURDATE(), INTERVAL 1 DAY) + INTERVAL 8 HOUR + INTERVAL 5 MINUTE,  DATE_SUB(CURDATE(), INTERVAL 1 DAY) + INTERVAL 8 HOUR + INTERVAL 5 MINUTE + INTERVAL 7 SECOND,   7600, NULL, NULL),
(3, 'scheduler', 'success', DATE_SUB(CURDATE(), INTERVAL 1 DAY) + INTERVAL 8 HOUR + INTERVAL 9 MINUTE,  DATE_SUB(CURDATE(), INTERVAL 1 DAY) + INTERVAL 8 HOUR + INTERVAL 9 MINUTE + INTERVAL 14 SECOND, 14800, NULL, NULL),
(4, 'scheduler', 'success', DATE_SUB(CURDATE(), INTERVAL 1 DAY) + INTERVAL 8 HOUR + INTERVAL 12 MINUTE, DATE_SUB(CURDATE(), INTERVAL 1 DAY) + INTERVAL 8 HOUR + INTERVAL 12 MINUTE + INTERVAL 6 SECOND,  6100, NULL, NULL),
(5, 'scheduler', 'failed',  DATE_SUB(CURDATE(), INTERVAL 1 DAY) + INTERVAL 8 HOUR + INTERVAL 15 MINUTE, DATE_SUB(CURDATE(), INTERVAL 1 DAY) + INTERVAL 8 HOUR + INTERVAL 15 MINUTE + INTERVAL 2 SECOND,  2800, 'LOGIN_EXPIRED', '登录已失效'),
(6, 'scheduler', 'success', DATE_SUB(CURDATE(), INTERVAL 1 DAY) + INTERVAL 8 HOUR + INTERVAL 18 MINUTE, DATE_SUB(CURDATE(), INTERVAL 1 DAY) + INTERVAL 8 HOUR + INTERVAL 18 MINUTE + INTERVAL 9 SECOND,  9300, NULL, NULL),

-- Day 0 (今天)
(1, 'scheduler', 'success', CURDATE() + INTERVAL 8 HOUR + INTERVAL 0 MINUTE + INTERVAL 12 SECOND,  CURDATE() + INTERVAL 8 HOUR + INTERVAL 0 MINUTE + INTERVAL 24 SECOND,  12400, NULL, NULL),
(2, 'scheduler', 'running', CURDATE() + INTERVAL 8 HOUR + INTERVAL 5 MINUTE,                       NULL,                                                                      NULL,  NULL, NULL),
(3, 'scheduler', 'success', CURDATE() + INTERVAL 8 HOUR + INTERVAL 8 MINUTE + INTERVAL 30 SECOND,  CURDATE() + INTERVAL 8 HOUR + INTERVAL 8 MINUTE + INTERVAL 45 SECOND,  15200, NULL, NULL),
(4, 'scheduler', 'success', CURDATE() + INTERVAL 8 HOUR + INTERVAL 10 MINUTE + INTERVAL 7 SECOND,  CURDATE() + INTERVAL 8 HOUR + INTERVAL 10 MINUTE + INTERVAL 12 SECOND,  5200, NULL, NULL),
(5, 'scheduler', 'failed',  CURDATE() + INTERVAL 7 HOUR + INTERVAL 45 MINUTE + INTERVAL 33 SECOND, CURDATE() + INTERVAL 7 HOUR + INTERVAL 45 MINUTE + INTERVAL 36 SECOND,  3100, 'CAPTCHA_EXPIRED', '验证码已过期'),
(6, 'scheduler', 'success', CURDATE() + INTERVAL 7 HOUR + INTERVAL 30 MINUTE,                      CURDATE() + INTERVAL 7 HOUR + INTERVAL 30 MINUTE + INTERVAL 9 SECOND,   8700, NULL, NULL),

-- 今天额外：物流轨迹等待中
(2, 'scheduler', 'pending', CURDATE() + INTERVAL 8 HOUR + INTERVAL 10 MINUTE, NULL, NULL, NULL, NULL);
