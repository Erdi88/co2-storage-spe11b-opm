"""
Post-processing of OPM Flow summary output for the three SPE11B variants.

The summary vectors were exported from ResInsight as tab-separated CSV files
(results/summary/). Region quantities are summed over FIPNUM regions:
    Box A      = regions 2 + 4 + 5
    Box B      = regions 3 + 6
    Seal Box A = region 5,  Seal Box B = region 6,  total seal = region 7

Column suffixes refer to the deck that produced them:
    .BASIC -> Task 2 (PV multipliers)   .TASK9 -> Task 5 (numerical aquifer)
    .TASK7 -> Task 6 (PERMZ = 0.5 * PERMX)

Run from the repository root:  python analysis/plot_summary.py
"""
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "results" / "summary"
FIG_DIR = ROOT / "figures" / "summary"

TASKS = {
    "BASIC": dict(label="Task 2 - PV multipliers", color="steelblue", ls="-"),
    "TASK9": dict(label="Task 5 - Numerical aquifer", color="green", ls="-"),
    "TASK7": dict(label="Task 6 - Higher PERMZ", color="darkorange", ls="--"),
}
BOX_A = [2, 4, 5]
BOX_B = [3, 6]
END_OF_INJECTION = 2050  # simulation starts 1 Jan 2000, injection stops at year 50


def read_summary(name):
    df = pd.read_csv(DATA_DIR / name, sep="\t")
    df = df.rename(columns={"Date and time": "Year"})
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
    return df


def region_sum(df, vectors, regions, task):
    """Sum one or more region vectors (e.g. RGMDS) over FIPNUM regions for one task."""
    return sum(df[f"{v}:{r}.{task}"] for v in vectors for r in regions)


def plot_tasks(df, series, ylabel, title, filename):
    """series(task) -> pd.Series to plot for that task."""
    fig, ax = plt.subplots(figsize=(10, 5))
    for task, style in TASKS.items():
        ax.plot(df["Year"], series(task), color=style["color"], linestyle=style["ls"],
                linewidth=2, label=style["label"])
    ax.axvline(END_OF_INJECTION, color="red", linestyle=":", linewidth=1.5,
               label="End of injection (year 50)")
    ax.set_xlabel("Year", fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(title, fontsize=13)
    ax.set_xlim(2000, 3000)
    ax.set_ylim(bottom=0)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=11)
    fig.tight_layout()
    fig.savefig(FIG_DIR / filename, dpi=150)
    plt.close(fig)
    print("wrote", filename)


def pressure_plots():
    for name, cell, label in [("BWPR_POP1_2_5_6.csv", "451,1,70", "POP1 (Facies 5)"),
                              ("BWPR_POP2_2_5_6.csv", "511,1,10", "POP2 (Facies 1)")]:
        df = read_summary(name)
        plot_tasks(df, lambda t: df[f"BWPR:{cell}.{t}"],
                   "Water phase pressure [bar]",
                   f"Water phase pressure at {label}",
                   name.replace(".csv", ".png"))


def phase_plots():
    phases = [("RGMMO", "Mobile", "Mobile_RGMMO"),
              ("RGMUS", "Immobile", "Immobile_RGMUS"),
              ("RGMDS", "Dissolved", "Dissolved_RGMDS")]
    for vec, label, prefix in phases:
        for box, regions in [("BoxA", BOX_A), ("BoxB", BOX_B)]:
            name = f"{prefix}_{box}_2_5_6.csv"
            df = read_summary(name)
            regs = "+".join(map(str, regions))
            plot_tasks(df, lambda t: region_sum(df, [vec], regions, t) / 1e6,
                       f"{label} CO$_2$ mass [×10$^6$ kg]",
                       f"{label} CO$_2$ in {box[:3]} {box[3]} (FIPNUM {regs})",
                       name.replace(".csv", ".png"))


def total_plots():
    for box, regions, name in [("Box A", BOX_A, "RGMDS_RGMMO_RGMUS_BoxA.csv"),
                               ("Box B", BOX_B, "RGMDS_RGMMO_RGMUS_BoxB.csv")]:
        df = read_summary(name)
        plot_tasks(df, lambda t: region_sum(df, ["RGMDS", "RGMMO", "RGMUS"], regions, t) / 1e6,
                   "Total CO$_2$ mass [×10$^6$ kg]",
                   f"Total CO$_2$ in {box} (mobile + immobile + dissolved)",
                   f"Total_CO2_{box.replace(' ', '')}_2_5_6.png")


def seal_plots():
    for name, region, label in [("RGMST_SealA_2_5_6.csv", 5, "seal facies, Box A (region 5)"),
                                ("RGMST_SealB_2_5_6.csv", 6, "seal facies, Box B (region 6)"),
                                ("RGMST_Fipnum7_2_5_6.csv", 7, "seal facies, whole domain (region 7)")]:
        df = read_summary(name)
        plot_tasks(df, lambda t: df[f"RGMST:{region}.{t}"] / 1e6,
                   "CO$_2$ mass in seal [×10$^6$ kg]",
                   f"CO$_2$ in {label}",
                   name.replace(".csv", ".png"))


def well_plot():
    df = read_summary("Wgit_Wgir_Wbhp_Basic.csv")
    panels = [("WGIR", "Gas injection rate (WGIR)", "Rate [Sm$^3$/day]", 1),
              ("WGIT", "Cumulative injection (WGIT)", "Cumulative [×10$^6$ Sm$^3$]", 1e6),
              ("WBHP", "Bottom hole pressure (WBHP)", "Pressure [bar]", 1)]
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    fig.suptitle("Injection well performance - Task 2 (base case)", fontsize=13, fontweight="bold")
    for ax, (vec, title, ylabel, scale) in zip(axes, panels):
        ax.plot(df["Year"], df[f"{vec}:INJ1.BASIC"] / scale, color="steelblue", lw=2, label="INJ1")
        ax.plot(df["Year"], df[f"{vec}:INJ2.BASIC"] / scale, color="darkorange", lw=2, ls="--", label="INJ2")
        ax.set_title(title, fontsize=11)
        ax.set_xlabel("Year")
        ax.set_ylabel(ylabel)
        ax.set_xlim(2000, 3000)
        ax.set_ylim(bottom=0)
        ax.grid(True, alpha=0.3)
        ax.legend()
    fig.tight_layout()
    fig.savefig(FIG_DIR / "Wgit_Wgir_Wbhp_Basic.png", dpi=150)
    plt.close(fig)
    print("wrote Wgit_Wgir_Wbhp_Basic.png")


if __name__ == "__main__":
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    well_plot()
    pressure_plots()
    phase_plots()
    total_plots()
    seal_plots()
