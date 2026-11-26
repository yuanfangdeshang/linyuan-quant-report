# 临渊量化 · 本地撮合引擎与交易席 UI

本目录是本地复刻版的服务端与前端，来源：

`/Users/yuanf/DoubaoWork/chats/2026-11-19/new-chat-1/linyuan-quant`

包含：

- `server.js`：房间、SSE、集合竞价、连续撮合、持仓/结算、机器人、导出接口；
- `public/`：大厅、交易席、主持台前端；
- `package.json`。

**未包含**：`questions.js`/题库、`data/rooms.json`、备份文件和历史日志。题库含答案与结算值，按比赛约束不放入仓库；需要本地运行时请从原始工作目录复制题库，或按原 README 的 schema 自建。

启动（需要本地 `questions.js`）：

```bash
PORT=7788 node server.js
```

游戏规则与接口见根目录 `docs/prompt.md` 和本目录源码。
