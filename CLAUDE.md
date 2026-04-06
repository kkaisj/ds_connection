# CLAUDE.md

## Project

`ds_connection`

## spec
1. 全部用中文回复
2. 不能写兼容性代码，除非我主动要求
3. 写代码前先描述方案，等我批准再动手
4. 需求不明确时，先提问澄清再写代码
5. 写完代码后，列出可能出现的问题并建议测试相应用例来覆盖这些问题
6. 一项任务需要修改超过3个文件，先停下来，拆分成更小的任务
7. 发现bug时，先编写一个能够重现该bug的测试，然后不断修复它，直到测试通过为止
8. 每次被纠正之后，就在 CLAUDE.md 文件中添加一条新规则，下次不要再犯相同的错误
9. 每次回复时都叫我 【困困】
10. SQLAlchemy 查询中不要使用 `.nullslast()` / `.nullsfirst()`，MySQL 不支持该语法；MySQL 的 `ORDER BY col DESC` 默认已将 NULL 排在最后
11. ORM 模型中二进制字段使用 `LargeBinary` 而非 `VarBinary`（SQLAlchemy 没有 VarBinary）
12. 所有代码必须写好注释：文件顶部说明用途，关键函数/组件写中文注释说明职责和逻辑
