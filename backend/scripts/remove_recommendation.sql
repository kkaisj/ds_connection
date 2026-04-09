-- DC 数据连接器 - 移除应用配置中的 recommendation 字段
-- 用法: mysql -h <host> -P 3306 -u <user> -p<password> dc_connection -e "source backend/scripts/remove_recommendation.sql"

SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

UPDATE connector_app
SET param_schema = JSON_REMOVE(param_schema, '$.recommendation')
WHERE param_schema IS NOT NULL
  AND JSON_EXTRACT(param_schema, '$.recommendation') IS NOT NULL;

