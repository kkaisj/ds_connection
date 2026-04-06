-- DC 数据连接器 - 添加 adapter_key 字段
-- 用法: mysql -u root -p dc_connection < add_adapter_key.sql

USE dc_connection;

ALTER TABLE connector_app
  ADD COLUMN adapter_key VARCHAR(128) NULL COMMENT 'DrissionPage 适配器标识' AFTER name;

-- 更新已有数据的 adapter_key
UPDATE connector_app SET adapter_key = 'taobao.order_sync' WHERE id = 1;
UPDATE connector_app SET adapter_key = 'taobao.logistics_track' WHERE id = 2;
UPDATE connector_app SET adapter_key = 'jd.product_stock_sync' WHERE id = 3;
UPDATE connector_app SET adapter_key = 'jd.refund_sync' WHERE id = 4;
UPDATE connector_app SET adapter_key = 'pdd.review_scrape' WHERE id = 5;
UPDATE connector_app SET adapter_key = 'douyin.traffic_analytics' WHERE id = 6;
