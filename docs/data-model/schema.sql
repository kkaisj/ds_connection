-- 数据连接器（DC）MVP MySQL 8.x DDL 草案

CREATE TABLE IF NOT EXISTS platform (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  code VARCHAR(64) NOT NULL UNIQUE,
  name VARCHAR(128) NOT NULL,
  parent_id BIGINT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_platform_parent_id (parent_id)
);

CREATE TABLE IF NOT EXISTS connector_app (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  platform_id BIGINT NOT NULL,
  name VARCHAR(128) NOT NULL,
  version VARCHAR(64) NOT NULL,
  status ENUM('active','inactive') NOT NULL DEFAULT 'active',
  param_schema JSON NULL,
  description VARCHAR(500) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_connector_app_platform FOREIGN KEY (platform_id) REFERENCES platform(id),
  KEY idx_connector_app_platform_id (platform_id),
  KEY idx_connector_app_status (status)
);

CREATE TABLE IF NOT EXISTS adapter_release (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  adapter_key VARCHAR(128) NOT NULL,
  version VARCHAR(64) NOT NULL,
  status ENUM('draft','testing','released','deprecated') NOT NULL DEFAULT 'draft',
  qa_passed TINYINT(1) NOT NULL DEFAULT 0,
  checksum VARCHAR(128) NULL,
  release_notes VARCHAR(1000) NULL,
  released_by VARCHAR(64) NULL,
  released_at DATETIME NULL,
  is_deleted TINYINT(1) NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_adapter_release_key_version (adapter_key, version),
  KEY idx_adapter_release_status (status),
  KEY idx_adapter_release_adapter_key (adapter_key)
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
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_shop_account_platform FOREIGN KEY (platform_id) REFERENCES platform(id),
  KEY idx_shop_account_platform_id (platform_id),
  KEY idx_shop_account_status (status)
);

CREATE TABLE IF NOT EXISTS storage_config (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  type ENUM('mysql','feishu_bitable','dingtalk_sheet') NOT NULL,
  name VARCHAR(128) NOT NULL,
  config_enc VARBINARY(4096) NOT NULL,
  status ENUM('active','inactive') NOT NULL DEFAULT 'active',
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
