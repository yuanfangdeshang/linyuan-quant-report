# 临渊量化课程报告工作区

## 目录结构

```text
模拟做市商/
  INDEX.md                       本索引
  research_paper.pdf              单篇综合论文（32 页，本轮交付）
  archive/                       旧版合集与 13 个单章（证据归档）
  data/official/                 官方赛后导出（JSON）
  docs/                          参赛提示词与交易界面截图
  server/                        本地撮合引擎与交易席/主持台前端
  assets/                        共享图表与对手账本片段
  第一轮/                        原始资源（代码、日志、对话、报告；本地归档）
    INDEX.md                     原始资源说明
    manifest.json                文件级来源、大小、SHA-256
    official/                    官方赛后导出、索引与赛后图表
    models/                      按模型/壳子归档的源码、日志、笔记、报告、对话
```

## 单篇交付与资料归档

> 本轮只交付 `research_paper.pdf` 这一篇合成文章。下面的独立章节与旧合集是证据归档，不再作为阅读路径；单篇论文已跳过各章重复的环境、合规和逐模型传记。


| 章节 | 模型/壳子 | 官方积分/名次 | 文件 |
|---|---|---:|---|
| **单篇综合论文（交付）** | 模型 × 壳子/执行框架 × 赛制 | -- | [PDF](research_paper.pdf)（32 页） |
| 旧版资料合集 | 36 页旧稿 + 13 个单章 | -- | [PDF](archive/LLM 交易智能体中的模型能力、壳子执行力与赛制激励.pdf)（192 页，非本轮） |
| 归档 quwork 冠军 | DeepSeek V4.1 Flash（quwork） | 124 / 1 | [PDF](archive/chapters/quwork_v41flash_section.pdf) |
| 归档 GLM5.3 | GLM5.3（豆包） | 118 / 2 | [PDF](archive/chapters/glm_section.pdf) |
| 归档 豆包自动模式 | 豆包 App·自动模式（116 分席位） | 116 / 3 | [PDF](archive/chapters/doubao_auto_section.pdf) |
| 归档 Hy4Flash | Hy4Flash（Workbuddy） | 116 / 3 | [PDF](archive/chapters/workbuddy_hy4flash_section.pdf) |
| 归档 V4.1 Flash 豆包 | DeepSeek V4.1 Flash（豆包） | 114 / 5 | [PDF](archive/chapters/deepseek_v41flash_section.pdf) |
| 归档 Qoder | qoder-DeepSeek f（Qoder） | 110 / 6 | [PDF](archive/chapters/qoder_deepseek_section.pdf) |
| 归档 Kimi | Kimi K3.1 Pro（DoubaoWork） | 103 / 7 | [PDF](archive/chapters/kimi_section.pdf) |
| 归档 Hy4 | Hy4（Workbuddy，双边阶梯） | 88 / 8 | [PDF](archive/chapters/workbuddy_hy4_section.pdf) |
| 归档 V4 Pro | DeepSeek V4 Pro（豆包） | 86 / 9 | [PDF](archive/chapters/deepseek_v4pro_section.pdf) |
| 归档 快速模式 | Workbuddy App·快速 | 84 / 10 | [PDF](archive/chapters/workbuddy_fast_section.pdf) |
| 归档 豆包 2.1Lite | 豆包 2.1Lite | 80 / 11 | [PDF](archive/chapters/doubao_21lite_section.pdf) |
| 归档 Qwen4M | Qwen4M（豆包） | 67 / 14 | [PDF](archive/chapters/qwen4_section.pdf) |
| 归档 豆包 2.1pro | 豆包 2.1pro（特定模型） | 58 / 15 | [PDF](archive/chapters/doubao_21pro_section.pdf) |
| 未来设计 | 赛制、评价与提示词设计（已并入单篇第 11 节） | -- | [PDF](archive/chapters/future_design_section.pdf) |

尚未单独成章：豆包 App 自动模式 80 分席位（第 11）、观察者（空仓基线）。Qoder 已完成独立章节，但只有自述复盘、没有源码日志。

## 原始资源

- [参赛提示词](docs/prompt.md)：13 个席位共同使用的同一份提示词。
- [交易界面](docs/screenshots/trading.png)、[主持台](docs/screenshots/host.png)：本地复刻版界面截图。
- [撮合引擎](server/README.md)：`server.js`、`public/` 前端与接口说明。
- [资源索引](第一轮/INDEX.md)：按 12+1 个模型/来源列出目录、席位和内容。
- [官方赛后导出](data/official/arena_258334.json)：所有报告的权威账本（可直接复现用）。
- [原始资源归档](第一轮/INDEX.md)：代码、日志、对话与报告；仓库内保留，可能含竞赛 token。
- [rooms 原始快照](第一轮/official/rooms-原始快照-20261122-004051.json)：脚本 prior、成交簿等赛后公开字段。
- [文件清单](第一轮/manifest.json)：每个归档文件的源路径、原始/归档大小、SHA-256、是否 gzip。

`第一轮/models/` 下的主要目录：

```text
quwork_v41flash/
deepseek_v41flash_doubao/
qoder_deepseek/
deepseek_v4pro_doubao/
doubao_21pro/
doubao_auto/
doubao_21lite/
qwen4/
glm53/
kimi/
workbuddy_hy4flash/
workbuddy_hy4/
workbuddy_fast/
```

超过 20 MB 的日志保存为 `.gz`；原始内容未改写。原始代码/日志可能含明文凭据，提交或分享前必须脱敏；根目录报告均已脱敏。

## 共享图表

- `assets/rank_heatmap.pdf`：15 席 × 12 局名次热力图
- `assets/activity_heatmap.pdf`：15 席 × 12 局成交手数热力图
- `assets/pie_*.pdf`、`assets/opp_*.tex`：各模型的对手盈亏饼图与逐局矩阵
- `assets/latency_*.pdf/.tex`：各模型的延迟/抢单代理指标
- `assets/*_norm*.pdf`：归一化 PnL 图
- `assets/paper_table_*.tex`：综合论文的逐局名次、PnL 矩阵、题型适配、风险、评分敏感性、对手账本、同局对照、失败模式与策略原型表
- `assets/opp_heatmap.pdf`：对手账本热力图（行=收钱方，列=付钱方）
- `assets/question_cards.pdf`：F1/F6/F8 官方题面重绘的赛题卡
- `assets/paper_range_bar.pdf`：每局 PnL 区间（对数刻度）
- `assets/paper_paths.pdf`：四个关键局的相对真值价格路径
- `assets/paper_risk_scatter.pdf`：收益—最大回撤象限图
- `assets/quwork_points_race.pdf`：六席累计积分

## 编译

```bash
xelatex -interaction=nonstopmode -halt-on-error <file>.tex
xelatex -interaction=nonstopmode -halt-on-error <file>.tex
```

编译产物（`.aux/.log/.out`）不保留。

## 口径

- 官方赛后导出优先于本地日志和模型自述。
- 价格以“分”返回，报告统一除以 100。
- 测试局不计分；正式局 15 席，积分 = 15 − 名次 + 1。
- 对手盈亏按每笔成交价与结算真值归属，行和恒等于官方单局 PnL。
- 归一化 PnL 是赛后指标，赛中不可见；用于比较不同价格尺度的题，不替代名次积分。
