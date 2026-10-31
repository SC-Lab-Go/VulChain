#!/usr/bin/env python3
"""Generate the ICDE RQ1 offline DOT assembly scalability figure.

Created: 2026-10-15
Version: v2026.10.15-01

Usage:
    python3 rq1_scaling_figure.py

The script writes PDF and 600-DPI PNG outputs to the current directory.
Only matplotlib and the Python standard library are required.
"""

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt


# Measurements: three sequential runs per input size; error bars are sample SD.
INPUT_PERCENT = [25, 50, 100]
EDGES_MILLIONS = [1.944, 3.888, 7.776]

WALL_MEAN_S = [13.30, 26.58, 53.34]
WALL_SD_S = [0.16, 0.23, 0.96]

RSS_MEAN_GIB = [0.207, 0.326, 0.447]

THROUGHPUT_MEAN_KEDGES_S = [146.2, 146.3, 145.8]
THROUGHPUT_SD_KEDGES_S = [1.7, 1.2, 2.6]

# Colorblind-safe, print-friendly colors from the Okabe--Ito palette.
WALL_COLOR = "#0072B2"       # blue
RSS_COLOR = "#D55E00"        # vermillion
THROUGHPUT_COLOR = "#009E73" # bluish green


def configure_style() -> None:
    """Set compact, grayscale-safe defaults appropriate for a paper figure."""
    mpl.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["DejaVu Serif"],
            "font.size": 11,
            "axes.labelsize": 11,
            "axes.labelweight": "bold",
            "axes.titlesize": 11,
            "axes.titleweight": "bold",
            "xtick.labelsize": 11,
            "ytick.labelsize": 11,
            "axes.linewidth": 0.7,
            "xtick.major.width": 0.7,
            "ytick.major.width": 0.7,
            "xtick.major.size": 3,
            "ytick.major.size": 3,
            "lines.linewidth": 1.15,
            "lines.markersize": 4.5,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "savefig.facecolor": "white",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )


def format_axis(ax: plt.Axes) -> None:
    ax.set_xlim(20, 105)
    ax.set_xticks(INPUT_PERCENT)
    ax.tick_params(axis="both", pad=2)
    for tick_label in (*ax.get_xticklabels(), *ax.get_yticklabels()):
        tick_label.set_fontweight("bold")
    # ax.grid(axis="y", color="0.87", linewidth=0.55, linestyle="-")
    ax.set_axisbelow(True)
    # Keep all four spines visible for a closed plotting box.
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(0.7)


def main() -> None:
    configure_style()
    fig, axes = plt.subplots(1, 3, figsize=(7, 2.0), constrained_layout=False)

    common = dict(
        markerfacecolor="white",
        markeredgecolor="black",
        markeredgewidth=0.9,
        ecolor="0.20",
        capsize=4.0,
        capthick=1.1,
        elinewidth=1.1,
        barsabove=True,
        zorder=4,
    )

    # Error bars show sample standard deviation across the three runs.
    axes[0].errorbar(
        INPUT_PERCENT,
        WALL_MEAN_S,
        yerr=WALL_SD_S,
        color=WALL_COLOR,
        marker="o",
        **common,
    )
    axes[0].set_ylabel("Seconds (s)", labelpad=3)
    axes[0].set_ylim(0, 60)
    axes[0].set_yticks([0, 15, 30, 45, 60])

    # RSS SD rounds to 0.000 GiB at the supplied precision, so no artificial
    # error bars are drawn.
    axes[1].plot(
        INPUT_PERCENT,
        RSS_MEAN_GIB,
        color=RSS_COLOR,
        marker="s",
        markerfacecolor="white",
        markeredgecolor="black",
        markeredgewidth=0.9,
    )
    axes[1].set_ylabel("GiB", labelpad=3)
    axes[1].set_ylim(0, 0.50)
    axes[1].set_yticks([0.0, 0.1, 0.2, 0.3, 0.4, 0.5])

    axes[2].errorbar(
        INPUT_PERCENT,
        THROUGHPUT_MEAN_KEDGES_S,
        yerr=THROUGHPUT_SD_KEDGES_S,
        color=THROUGHPUT_COLOR,
        marker="^",
        **common,
    )
    axes[2].set_ylabel("kedges/sec", labelpad=3)
    # Starting at zero avoids exaggerating the sub-percent mean differences.
    axes[2].set_ylim(0, 155)
    axes[2].set_yticks([0, 50, 100, 150])

    for ax in axes:
        format_axis(ax)

    # Place panel labels inside the bottom center of each closed plotting box.
    for ax, label, x_position in zip(
        axes,
        ("(a) Wall time", "(b) Peak memory", "(c) Throughput"),
        (0.5, 0.5, 0.5),
    ):
        ax.text(
            x_position,
            0.055,
            label,
            transform=ax.transAxes,
            ha="center",
            va="bottom",
            fontsize=11,
            fontweight="bold",
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.9, "pad": 0.8},
            zorder=10,
        )

    fig.supxlabel("Input size (%)", fontsize=11, fontweight="bold", y=0.025)
    fig.subplots_adjust(left=0.085, right=0.995, bottom=0.245, top=0.96, wspace=0.42)

    output = Path.cwd()
    pdf = output / "rq1_scaling_figure.pdf"
    png = output / "rq1_scaling_figure.png"
    cropped_pdf = output / "rq1_scaling_figure_cropped.pdf"
    cropped_png = output / "rq1_scaling_figure_cropped.png"

    fig.savefig(pdf, bbox_inches="tight", pad_inches=0.02)
    fig.savefig(png, dpi=600, bbox_inches="tight", pad_inches=0.02)
    # Explicitly named LaTeX-ready copies use a smaller exterior pad.
    fig.savefig(cropped_pdf, bbox_inches="tight", pad_inches=0.005)
    fig.savefig(cropped_png, dpi=600, bbox_inches="tight", pad_inches=0.005)
    plt.close(fig)

    print(f"Wrote {pdf}")
    print(f"Wrote {png}")
    print(f"Wrote {cropped_pdf}")
    print(f"Wrote {cropped_png}")


if __name__ == "__main__":
    main()
