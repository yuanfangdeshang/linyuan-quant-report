#!/usr/bin/env python3
"""Render the scoring slopegraph and the risk scatter from the official tables."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper" / "assets"

plt.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": ["Songti SC", "STSong", "SimSun"],
        "mathtext.fontset": "stix",
        "axes.unicode_minus": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    }
)

TEAL = "#275E59"
BRICK = "#A63632"
INK = "#222222"
GRID = "#E4E0D6"

# name, official rank, rank by normalized capture, composite rank
SCORING = [
    ("quwork", 1, 3, 1),
    ("GLM5.3", 2, 7, 5),
    ("Hy4Flash", 3, 1, 2),
    ("豆包自动", 3, 2, 3),
    ("豆包 V4.1 Flash", 5, 5, 4),
    ("Qoder V4.1 Flash", 6, 6, 6),
    ("Kimi", 7, 4, 7),
    ("Hy4", 8, 9, 9),
    ("DeepSeek V4 Pro", 9, 8, 8),
    ("快速", 10, 10, 10),
]

COLORS = [
    "#256560",
    "#AA4034",
    "#B58B39",
    "#7E5984",
    "#64748A",
    "#487793",
    "#747943",
    "#AD606C",
    "#B16842",
    "#42848E",
]

# name, formal PnL, max drawdown
RISK = [
    ("quwork", 4148.48, 0.0),
    ("GLM5.3", -3135.84, 4947.4),
    ("豆包自动", -3107.15, 4555.0),
    ("Hy4Flash", 8620.02, 42.5),
    ("豆包 V4.1 Flash", -277.29, 1248.0),
    ("Qoder V4.1 Flash", 723.13, 74.1),
    ("Kimi", 1638.73, 16.8),
    ("Hy4", 2307.48, 64.3),
    ("DeepSeek V4 Pro", 4997.83, 124.3),
    ("快速", 1361.55, 20.0),
    ("Qwen4M", -803.19, 803.3),
    ("豆包 2.1pro", -1534.90, 1830.6),
]


def draw_scoring():
    fig, ax = plt.subplots(figsize=(6.3, 3.4))
    fig.subplots_adjust(left=0.11, right=0.73, top=0.95, bottom=0.18)

    xs = [0, 1, 2]
    for (name, official, capture, composite), color in zip(SCORING, COLORS):
        # Official points have a tie at rank 3; separate it only for legibility.
        y0 = official
        if name == "Hy4Flash":
            y0 -= 0.08
        elif name == "豆包自动":
            y0 += 0.08
        ax.plot(
            xs,
            [y0, capture, composite],
            color=color,
            linewidth=1.6,
            marker="o",
            markersize=4.5,
            markeredgecolor="white",
            markeredgewidth=0.7,
            zorder=3,
        )
        ax.text(
            2.06,
            composite,
            name,
            ha="left",
            va="center",
            fontsize=8.2,
            color=color,
            clip_on=False,
        )

    ax.set_xlim(-0.06, 2.05)
    ax.set_ylim(10.5, 0.5)
    ax.set_xticks(xs)
    ax.set_xticklabels(["官方积分", "仅 $\\bar n$", "复合 60/40"], fontsize=8.5)
    ax.set_yticks(range(1, 11))
    ax.set_yticklabels([str(i) for i in range(1, 11)], fontsize=7.5)
    ax.set_ylabel("名次（1 最好）", fontsize=9, labelpad=8)
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(axis="x", length=0, pad=6)
    ax.tick_params(axis="y", length=2, color="#777777", pad=3)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    for spine in ["left", "bottom"]:
        ax.spines[spine].set_color("#555555")
        ax.spines[spine].set_linewidth(0.7)

    fig.savefig(OUT / "paper_scoring_bump.pdf", format="pdf")
    plt.close(fig)


def draw_risk():
    fig, ax = plt.subplots(figsize=(6.3, 3.8))
    fig.subplots_adjust(left=0.11, right=0.98, top=0.97, bottom=0.34)

    handles = []
    for i, (name, pnl, drawdown) in enumerate(RISK, start=1):
        color = TEAL if pnl >= 0 else BRICK
        x = max(drawdown, 1.0)
        if drawdown == 0:
            ax.scatter(
                x,
                pnl,
                s=72,
                facecolor="white",
                edgecolor=color,
                linewidth=1.4,
                zorder=4,
            )
            ax.text(x, pnl, str(i), ha="center", va="center", fontsize=7.0, color=color, zorder=5)
        else:
            ax.scatter(
                x,
                pnl,
                s=84,
                facecolor=color,
                edgecolor="white",
                linewidth=0.8,
                zorder=4,
            )
            ax.text(x, pnl, str(i), ha="center", va="center", fontsize=7.0, color="white", zorder=5)
        handles.append(
            Line2D(
                [0],
                [0],
                marker="o",
                linestyle="none",
                markerfacecolor=color,
                markeredgecolor="white" if drawdown > 0 else color,
                markersize=4.6,
                label=f"{i}. {name}",
            )
        )

    ax.set_xscale("log")
    ax.set_xlim(0.8, 7000)
    ax.set_ylim(-3500, 9000)
    ax.set_xticks([1, 10, 100, 1000, 5000])
    ax.set_xticklabels(["0/1", "10", "100", "1,000", "5,000"], fontsize=7.5)
    ax.set_yticks([-3000, 0, 3000, 6000, 9000])
    ax.set_yticklabels([f"{v:,}" for v in [-3000, 0, 3000, 6000, 9000]], fontsize=7.5)
    ax.set_xlabel("最大回撤（元，对数刻度；0 回撤置于 1）", fontsize=8.5, labelpad=6)
    ax.set_ylabel("正式 PnL（元）", fontsize=8.5, labelpad=6)
    ax.axhline(0, color="#777777", linewidth=0.7, zorder=1)
    ax.grid(True, which="major", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", length=2, color="#777777", pad=3)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    for spine in ["left", "bottom"]:
        ax.spines[spine].set_color("#555555")
        ax.spines[spine].set_linewidth(0.7)

    ax.legend(
        handles=handles,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.20),
        ncol=3,
        frameon=False,
        fontsize=6.6,
        handletextpad=0.4,
        columnspacing=1.2,
        labelspacing=0.35,
        borderaxespad=0,
    )

    fig.savefig(OUT / "paper_risk_scatter.pdf", format="pdf")
    plt.close(fig)


def main():
    draw_scoring()
    draw_risk()
    print("wrote paper_scoring_bump.pdf and paper_risk_scatter.pdf")


if __name__ == "__main__":
    main()
