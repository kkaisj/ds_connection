---
description: 新增一个数据库实体的标准流程
---

# 新增数据库实体

## 步骤

### 1. 阅读相关文档

- 阅读 `docs/references/database-schema.md` 了解现有表结构
- 阅读 `docs/conventions/naming-conventions.md` 了解命名规范
- 阅读 `docs/conventions/backend-coding-style.md` 了解 Entity 编码规范

### 2. 创建 Entity

- 路径：`src/main/java/com/uav/entity/Xxx.java`
- 继承 `BaseEntity`（自动获得 `id`, `createdAt`, `updatedAt`）
- 表名使用 `sys_` 前缀 + 下划线命名

```java
@Data
@EqualsAndHashCode(callSuper = true)
@Entity
@Table(name = "sys_xxx")
public class Xxx extends BaseEntity {

    @Column(name = "field_name", nullable = false, length = 50)
    private String fieldName;
}
```

### 3. 创建 Repository

- 路径：`src/main/java/com/uav/repository/XxxRepository.java`

```java
public interface XxxRepository extends JpaRepository<Xxx, Long> {
    // 自定义查询方法
}
```

### 4. 创建 DTO

- Request：`src/main/java/com/uav/dto/request/XxxCreateRequest.java`
- Response：`src/main/java/com/uav/dto/response/XxxVO.java`

### 5. 创建 Service

- 路径：`src/main/java/com/uav/service/XxxService.java`
- 包含 Entity ↔ VO 的转换逻辑

### 6. 更新初始化数据（如需要）

- 路径：`src/main/resources/data.sql`//
- 添加初始数据 INSERT 语句

### 7. 验证

// turbo
```bash
cd uav-backend && mvn test -B
```

JPA `ddl-auto: update` 会自动创建表。

### 8. 更新文档

- 更新 `docs/references/database-schema.md` 添加新表结构
