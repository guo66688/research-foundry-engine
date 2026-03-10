# 文档总览

这套文档按“入口 -> 结构 -> 契约 -> 运行”的顺序组织，默认面向中文使用者。

## 阅读顺序

第一次接触项目：

1. [README.md](/home/icoffee/Projects/codex-arxiv-tools/README.md)
2. [QUICKSTART.md](/home/icoffee/Projects/codex-arxiv-tools/QUICKSTART.md)
3. [architecture.md](/home/icoffee/Projects/codex-arxiv-tools/docs/architecture.md)
4. [configuration.md](/home/icoffee/Projects/codex-arxiv-tools/docs/configuration.md)

准备改脚本或接新阶段：

1. [architecture.md](/home/icoffee/Projects/codex-arxiv-tools/docs/architecture.md)
2. [data-models.md](/home/icoffee/Projects/codex-arxiv-tools/docs/data-models.md)
3. [conventions.md](/home/icoffee/Projects/codex-arxiv-tools/docs/conventions.md)
4. [runtime.md](/home/icoffee/Projects/codex-arxiv-tools/docs/runtime.md)

准备在 Codex 中使用 skills：

1. [skills.md](/home/icoffee/Projects/codex-arxiv-tools/docs/skills.md)
2. `.agents/skills/*/SKILL.md`

## 文档分层

- 根目录文档
- [README.md](/home/icoffee/Projects/codex-arxiv-tools/README.md)：项目定位、模块关系、最小运行路径。
- [QUICKSTART.md](/home/icoffee/Projects/codex-arxiv-tools/QUICKSTART.md)：最短路径，不展开设计细节。

- `docs/` 主题文档
- [architecture.md](/home/icoffee/Projects/codex-arxiv-tools/docs/architecture.md)：模块职责、顺序、依赖关系。
- [configuration.md](/home/icoffee/Projects/codex-arxiv-tools/docs/configuration.md)：配置文件怎么写、字段怎么用。
- [data-models.md](/home/icoffee/Projects/codex-arxiv-tools/docs/data-models.md)：数据契约、状态流转、命名规则。
- [runtime.md](/home/icoffee/Projects/codex-arxiv-tools/docs/runtime.md)：运行目录、产物位置、验证命令。
- [conventions.md](/home/icoffee/Projects/codex-arxiv-tools/docs/conventions.md)：命名、slug、时间戳、状态词汇。
- [skills.md](/home/icoffee/Projects/codex-arxiv-tools/docs/skills.md)：五个 skills 的触发边界和使用方式。

## 使用建议

- 想尽快跑通一次流程，优先读 `README -> QUICKSTART -> configuration`。
- 想保证不同阶段能拼起来，优先读 `architecture -> data-models`。
- 想避免新脚本和旧约定冲突，优先读 `conventions -> runtime`。
