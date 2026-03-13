# 文档索引

这套文档默认按“先用起来，再理解结构”的顺序组织，并以 `standalone` 内置分发版作为默认推荐路径。

## 推荐阅读顺序

### 日常使用者

1. [README.md](../README.md)
2. [QUICKSTART.md](../QUICKSTART.md)
3. [skills.md](skills.md)
4. [runtime.md](runtime.md)

### 开发者

1. [README.md](../README.md)
2. [architecture.md](architecture.md)
3. [configuration.md](configuration.md)
4. [data-models.md](data-models.md)
5. [conventions.md](conventions.md)
6. [runtime.md](runtime.md)

## 文档分层

- 根目录文档
- [README.md](../README.md)：项目定位、双模式说明、推荐入口
- [QUICKSTART.md](../QUICKSTART.md)：最短安装和使用路径

- `docs/` 主题文档
- [architecture.md](architecture.md)：命令层、phase skills、双 backend 的分层关系
- [configuration.md](configuration.md)：Vault、runtime、source 与策略配置
- [data-models.md](data-models.md)：跨阶段共享的数据契约
- [runtime.md](runtime.md)：运行目录、产物位置、standalone 安装位置
- [conventions.md](conventions.md)：命名与路径约定
- [skills.md](skills.md)：phase skills、AGENTS 路由与 standalone 分发关系

## 默认建议

- 默认安装方式：`standalone-skills/` + 一键安装脚本
- 默认使用入口：Vault `AGENTS.md` 中的中文命令
- 默认运行环境：固定虚拟环境 `research-foundry-standalone`
- 默认存储策略：Vault 只放 Markdown 和图片，runtime 放到 Vault 外

## 2026-03 新增文档

- [source-routing.md](source-routing.md): 来源角色化、分池与分桶路由设计。

- [design.md](design.md)：离线回放与 source-routing 回归设计
- [system.md](system.md)：离线回放系统视角
- [modules.md](modules.md)：source-routing 相关模块清单
- [incidents.md](incidents.md)：事故回放与回归流程
