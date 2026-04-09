-- 用途：维护平台一二级层级（一级决定二级），并补充业务侧常用二级平台。
-- 执行方式：mysql -u root -p dc_connection < add_more_platforms.sql

SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- 1) 一级平台（父节点）
INSERT INTO platform (id, code, name, parent_id) VALUES
  (20, 'taobao_tmall', '淘宝天猫', NULL),
  (21, 'jd_eco', '京东', NULL),
  (22, 'pdd_eco', '拼多多', NULL),
  (23, 'douyin_eco', '抖音', NULL),
  (24, 'other_eco', '其他平台', NULL)
ON DUPLICATE KEY UPDATE
  name = VALUES(name),
  parent_id = VALUES(parent_id);

-- 2) 二级平台（子节点）
-- 兼容说明：
-- - 保留现有 adapter_key 对应平台 code（taobao/jd/pdd/douyin），直接作为二级平台。
-- - 其余业务平台补充到对应一级下，供前端联动选择。
INSERT INTO platform (id, code, name, parent_id) VALUES
  (1, 'taobao', '生意参谋', 20),
  (30, 'taobao_wanxiangtai', '万相台无界版', 20),
  (2, 'jd', '京东商家后台', 21),
  (31, 'jd_jzt', '京东推广平台', 21),
  (3, 'pdd', '拼多多商家后台', 22),
  (32, 'pdd_promotion', '拼多多推广平台', 22),
  (4, 'douyin', '抖店', 23),
  (33, 'douyin_compass', '电商罗盘', 23),
  (34, 'douyin_alliance', '精选联盟', 23),
  (35, 'douyin_feige', '抖店飞鸽', 23),
  (5, 'xiaohongshu', '小红书', 24),
  (6, 'kuaishou', '快手电商', 24),
  (7, 'weidian', '微店', 24),
  (8, 'vip', '唯品会', 24),
  (9, 'suning', '苏宁易购', 24),
  (11, 'dewu', '得物', 24),
  (12, 'amazon', '亚马逊', 24),
  (13, 'shopify', 'Shopify', 24),
  (14, 'lazada', 'Lazada', 24),
  (15, 'shopee', 'Shopee', 24)
ON DUPLICATE KEY UPDATE
  name = VALUES(name),
  parent_id = VALUES(parent_id);
