-- 用途：新增适配器发版表，并初始化已发版版本（MVP 默认 1.0.0）。
-- 执行方式：mysql -u root -p dc_connection < add_adapter_release.sql

SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

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

-- 首批默认发版：已接入 registry 的示例适配器默认发布 1.0.0，便于历史流程平滑过渡。
INSERT INTO adapter_release (
  adapter_key, version, status, qa_passed, released_by, released_at, release_notes
) VALUES
  ('taobao.order_sync', '1.0.0', 'released', 1, 'system', NOW(), '初始化默认发版'),
  ('taobao.logistics_track', '1.0.0', 'released', 1, 'system', NOW(), '初始化默认发版'),
  ('jd.product_stock_sync', '1.0.0', 'released', 1, 'system', NOW(), '初始化默认发版'),
  ('jd.refund_sync', '1.0.0', 'released', 1, 'system', NOW(), '初始化默认发版'),
  ('pdd.review_scrape', '1.0.0', 'released', 1, 'system', NOW(), '初始化默认发版'),
  ('douyin.traffic_analytics', '1.0.0', 'released', 1, 'system', NOW(), '初始化默认发版')
ON DUPLICATE KEY UPDATE
  status = VALUES(status),
  qa_passed = VALUES(qa_passed),
  released_by = VALUES(released_by),
  released_at = VALUES(released_at),
  release_notes = VALUES(release_notes),
  is_deleted = 0;
