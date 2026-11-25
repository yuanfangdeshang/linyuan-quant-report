# 临渊量化 · 第一轮资源归档

本目录汇集 258334 房间各模型/壳子的原始工作资源。官方赛后导出是统一权威账本；模型自述、代码和日志只用于解释过程。

## 目录结构

```text
第一轮/
  official/                官方赛后导出、索引与赛后图表
  models/
    quwork_v41flash/       quwork 冠军席位
    deepseek_v41flash_doubao/
    qoder_deepseek/        Qoder 自述复盘
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
  manifest.json            每个归档文件的源路径、大小、SHA-256、压缩标记
```

## 模型映射

| 目录 | 模型/壳子 | 官方席位 | 积分/名次 | 主要内容 |
|---|---|---|---:|---|
| `models/quwork_v41flash/` | DeepSeek V4.1 Flash（quwork） | quwork-DeepSeek | 124 / 1 | 完整对话、赛后报告、图表 |
| `models/deepseek_v41flash_doubao/` | DeepSeek V4.1 Flash（豆包） | 豆包-远方的 mac-DeepS | 114 / 5 | 赛后报告与图表 |
| `models/qoder_deepseek/` | DeepSeek f（Qoder） | qoder-DeepSeek f | 110 / 6 | 赛后自述复盘（无独立工作目录） |
| `models/deepseek_v4pro_doubao/` | DeepSeek V4 Pro（豆包） | 豆包-远方的mac-DeepSe | 86 / 9 | 源码、日志、反思、赛后报告 |
| `models/doubao_21pro/` | 豆包 2.1pro | 豆包-远方的mac-豆包2.1p | 58 / 15 | 源码、日志、图表、逐笔报告 |
| `models/doubao_auto/` | 豆包 App·自动模式 | 自动-高(116) | 116 / 3 | 源码、notes、日志、报告 |
| `models/doubao_21lite/` | 豆包 2.1Lite | 豆包-远方的mac-豆包2.1l | 80 / 11 | 源码、日志、journal、报告 |
| `models/qwen4/` | Qwen4M | 豆包-远方的mac-Qwen4M | 67 / 14 | 赛后报告与复盘日记 |
| `models/glm53/` | GLM5.3 | 豆包-远方的mac-GLM5.3 | 118 / 2 | 自我迭代日志与赛后报告 |
| `models/kimi/` | Kimi K3.1 Pro | 豆包-远方的 mac-Kimi | 103 / 7 | 源码、事件日志、策略、复盘 |
| `models/workbuddy_hy4flash/` | Hy4Flash（Workbuddy） | Workbuddy-Hy4fla | 116 / 3 | 源码、notes、日志、完整对话 |
| `models/workbuddy_hy4/` | Hy4（Workbuddy） | Workbuddy-Hy4 | 88 / 8 | 源码、反思、动作日志、完整对话 |
| `models/workbuddy_fast/` | Workbuddy App·快速 | app-Workbuddy-快速 | 84 / 10 | 脚本、notes、SSE 日志、完整对话 |

## 归档统计

| 模型目录 | 文件数 | 归档大小 | gzip 文件数 |
|---|---:|---:|---:|
| `quwork_v41flash` | 9 | 4.5 MB | 0 |
| `deepseek_v41flash_doubao` | 8 | 4.9 MB | 0 |
| `qoder_deepseek` | 1 | 0.0 MB | 0 |
| `deepseek_v4pro_doubao` | 16 | 21.0 MB | 0 |
| `doubao_21pro` | 53 | 21.1 MB | 0 |
| `doubao_auto` | 18 | 20.9 MB | 1 |
| `doubao_21lite` | 49 | 115.4 MB | 2 |
| `qwen4` | 2 | 1.8 MB | 0 |
| `glm53` | 2 | 0.8 MB | 0 |
| `kimi` | 8 | 4.2 MB | 0 |
| `workbuddy_hy4flash` | 22 | 1.9 MB | 0 |
| `workbuddy_hy4` | 25 | 1.8 MB | 1 |
| `workbuddy_fast` | 10 | 83.5 MB | 1 |

## 未归档席位

- **豆包 App·自动模式（80 分，第 11）**：与 116 分的同名“自动-高”是不同席位；没有找到独立工作目录，只有官方排名/成交数据。
- **观察者（远方的熵，80 分）**：全程空仓的观察席位，无模型工作资源。
- **qoder-DeepSeek f（110 分，第 6）**：没有独立工作目录，只保留了官方赛后目录中的自述复盘；已在 `models/qoder_deepseek/` 单独归档。

## 使用说明

- 原始文件保持来源目录内的相对结构；超过 20MB 的日志保存为同名 `.gz`，内容未改写。
- `manifest.json` 记录源路径、原始/归档大小、SHA-256，便于复核是否漏复制或后续改动。
- 原始代码和日志可能包含明文 token/凭据；本归档仅供本地研究，提交或分享前必须脱敏。当前根目录的报告均已脱敏。
- 按比赛规则，未复制服务器源码、题库文件或结算值内部字段；只保留官方赛后公开导出和选手本可见材料。
- 根目录的 `*_section.tex/.pdf` 是整理后的独立章节；`assets/` 是共享图表；本目录是它们的原始证据层。
