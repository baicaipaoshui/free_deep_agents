# Retained Libraries

当前 `libs/` 目录只保留与 [设计架构文档](../设计架构文档.md) 实现直接相关的两个包：

```txt
deepagents/   # Core SDK — create_deep_agent, middleware, backends
cli/          # Hooks / Skills 参考实现
```

## 用途

- `deepagents/`：`apps/iav-fusa-platform/backend` 通过本地 editable dependency 直接引用。
- `cli/`：作为设计文档中 Hooks 机制、Skills 加载方式和内置技能格式的参考实现保留。
