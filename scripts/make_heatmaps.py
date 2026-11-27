#!/usr/bin/env python3
"""Render the rank and trade-count heatmaps from the official export."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "official" / "arena_258334.json"
OUT = ROOT / "paper" / "assets"

# Display labels keyed by the official seat id, in final-standings order.
SEATS = [
    ("18d5e35cf73ffb62", "DeepSeek V4.1 Flash（quwork）"),
    ("a2a99d356ca56b0a", "GLM5.3"),
    ("63f1c2dc9a71f995", "豆包 App·自动（116）"),
    ("ade088e45fff4840", "Hy4Flash（Workbuddy）"),
    ("9c56abd9d236b7cb", "DeepSeek V4.1 Flash（豆包）"),
    ("f4ce592d358a40db", "DeepSeek（Qoder）"),
    ("490881fafe932e33", "Kimi K3.1 Pro"),
    ("fc7feaeda7932a8d", "Hy4（Workbuddy）"),
    ("91c1e1af28134d3f", "DeepSeek V4 Pro（豆包）"),
    ("cc442098a77095b7", "Workbuddy 快速"),
    ("de4aac79f0780ead", "豆包 App·自动（80）"),
    ("c64f9cfced6ef32b", "豆包 2.1l"),
    ("e413aec5733e9717", "观察者（空仓）"),
    ("480e4b250171ed9c", "Qwen4M"),
    ("bc1554e1705eff9a", "豆包 2.1pro（特定）"),
]

plt.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": ["Songti SC", "STSong", "SimSun"],
        "axes.unicode_minus": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    }
)


def load_matrices():
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    games = payload["games"]
    standings = {s["id"]: s for s in payload["standings"]}

    test_rank = {row["id"]: row["rank"] for row in games[0]["ranking"]}
    ranks, qty = [], []
    for seat_id, _ in SEATS:
        results = {r["number"]: r["rank"] for r in standings[seat_id]["results"]}
        ranks.append([test_rank[seat_id]] + [results[n] for n in range(2, 13)])

        per_game = []
        for game in games:
            player = next((p for p in game["review"]["players"] if p["id"] == seat_id), None)
            per_game.append(sum(abs(t["qty"]) for t in player["trades"]) if player else 0)
        qty.append(per_game)

    return np.array(ranks), np.array(qty)


def draw(matrix, path, title, cmap, vmin, vmax, ticks, cbar_label, annot_fmt="{:d}"):
    fig = plt.figure(figsize=(16, 8.6))
    ax = fig.add_axes([0.21, 0.105, 0.68, 0.79])
    cax = fig.add_axes([0.915, 0.105, 0.017, 0.79])

    rows, cols = matrix.shape
    mesh = ax.pcolormesh(
        np.arange(cols + 1),
        np.arange(rows + 1),
        matrix,
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        edgecolors="white",
        linewidth=0.8,
    )
    ax.set_xlim(0, cols)
    ax.set_ylim(rows, 0)

    ax.set_xticks(np.arange(cols) + 0.5)
    ax.set_xticklabels(["测试"] + [str(i) for i in range(1, 12)], fontsize=14)
    ax.set_yticks(np.arange(rows) + 0.5)
    ax.set_yticklabels([name for _, name in SEATS], fontsize=15)
    ax.tick_params(length=0, pad=6)
    for spine in ax.spines.values():
        spine.set_visible(False)

    ax.set_xlabel("局（测试 + 正式 1–11）", fontsize=15, labelpad=8)
    ax.set_ylabel("席位（按最终名次排序）", fontsize=15, labelpad=14)
    ax.set_title(title, fontsize=19, pad=14)

    # Slightly wider gap between the unscored test game and the eleven formal games.
    ax.axvline(1, color="white", linewidth=2.2)

    for i in range(rows):
        for j in range(cols):
            ax.text(
                j + 0.5,
                i + 0.5,
                annot_fmt.format(int(matrix[i, j])),
                ha="center",
                va="center",
                fontsize=13.5,
                color="#111111",
            )

    cb = fig.colorbar(mesh, cax=cax, ticks=ticks)
    cb.outline.set_visible(False)
    cb.ax.tick_params(length=3, labelsize=13)
    cb.set_label(cbar_label, fontsize=15, labelpad=10)

    fig.savefig(path, format="pdf")
    plt.close(fig)


def main():
    ranks, qty = load_matrices()
    assert ranks.shape == (15, 12) and qty.shape == (15, 12)
    assert ranks.min() == 1 and ranks.max() == 15

    draw(
        ranks,
        OUT / "rank_heatmap.pdf",
        "临渊量化：全部 15 席 × 12 局名次热力图（1 最好，15 最差）",
        plt.get_cmap("RdYlGn_r"),
        1,
        15,
        range(2, 15, 2),
        "名次（1 最好，15 最差）",
    )
    draw(
        qty,
        OUT / "trade_heatmap.pdf",
        "临渊量化：全部 15 席 × 12 局成交手数热力图（0 = 空仓）",
        plt.get_cmap("Blues"),
        0,
        140,
        range(0, 141, 20),
        "成交手数",
    )
    print("rank matrix:\n", ranks)
    print("trade matrix:\n", qty)


if __name__ == "__main__":
    main()
