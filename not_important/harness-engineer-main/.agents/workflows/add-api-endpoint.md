---
description: 新增一个后端 API 端点的标准流程
---

# 新增后端 API 端点

## 步骤

### 1. 阅读相关文档

- 阅读 `uav-backend/AGENTS.md` 了解后端架构
- 阅读 `docs/conventions/api-design.md` 了解 API 设计规范
- 阅读 `docs/conventions/backend-coding-style.md` 了解编码规范

### 2. 创建/修改 Entity（如需要）

- 路径：`src/main/java/com/uav/entity/`
- 继承 `BaseEntity`
- 使用 `@Data` + `@EqualsAndHashCode(callSuper = true)` + `@Entity`
- 字段使用 `@Column` 注解

### 3. 创建 Repository

- 路径：`src/main/java/com/uav/repository/XxxRepository.java`
- 继承 `JpaRepository<Xxx, Long>`

### 4. 创建 Request DTO

- 路径：`src/main/java/com/uav/dto/request/XxxCreateRequest.java`
- 添加 `@NotBlank`, `@Size` 等验证注解

### 5. 创建 Response VO

- 路径：`src/main/java/com/uav/dto/response/XxxVO.java`
- 不包含敏感字段（如密码）

### 6. 创建 Service

- 路径：`src/main/java/com/uav/service/XxxService.java`
- 使用 `@Service` + `@RequiredArgsConstructor`
- 实现 CRUD 业务逻辑
- Entity ↔ VO 转换在此完成

### 7. 创建 Controller

- 路径：`src/main/java/com/uav/controller/XxxController.java`
- 使用 `@RestController` + `@RequestMapping("/api/xxx")` + `@RequiredArgsConstructor`
- 所有方法返回 `Result<T>`

### 8. 验证

// turbo
```bash
cd uav-backend && mvn test -B
```

确保 ArchUnit 架构测试通过。

### 9. 更新文档

- 更新 `docs/references/api-reference.md` 添加新端点
- 如有 Schema 变更，更新 `docs/references/database-schema.md`
