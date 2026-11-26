# 自动做市程序

`auto_mm.js` 连接临渊量化房间的 WebSocket，按当前均价/盘口挂双边限价单：

- 公允价：`average`（没有则用 `price`/`openingPrice`）；
- 基础双边：fair ± 4 分，遇到更窄盘口时向盘口内收 1 分；
- 库存偏斜：多头超过 2 手时整体下移，空头超过 2 手时整体上移；
- 接近 ±8 手时停止继续加同方向库存；
- 每 2.5 秒请求一次 `resync`，轮次结束/暂停时撤销挂单；
- 不包含 token；token 从本地 `/tmp/lq_session.json` 读取，文件权限 600。

运行：

```bash
node scripts/auto_mm.js
```

可用环境变量 `LQ_SESSION` 指定会话文件；文件格式：

```json
{"ws":"wss://.../ws","code":"338323","token":"..."}
```

该程序只做模拟盘做市，不访问外部行情或答案。
