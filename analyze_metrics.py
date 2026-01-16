#!/usr/bin/env python3
"""
Unified metric extraction/plotting for CPU, memory, net I/O, and tick times.

Features:
- get_dataframe_* functions per metric (CPU, memory, netio, tick) that collect metadata
  (version, farm_count, trial, node) from path components.
- apply_offsets() to drop/shift timestamps per (version, farm_count) so pre-setup data
  is discarded.
- plot_* functions that emit per–farm-count time series and boxplots across versions/farm counts.

Usage:
    python analyze_metrics.py /var/scratch/<user>/yardstick/<timestamp>

Edit OFFSETS to set per-(version, farm_count) offsets in seconds.
"""

from __future__ import annotations

import glob
import sys
from pathlib import Path
from typing import Dict, Tuple

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

import math
from typing import Iterable, List, Optional

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Per-(version, farm_count) offsets in seconds to discard pre-setup data.
# Example: OFFSETS[("1.20.1", "farms_5")] = 120
OFFSETS: Dict[Tuple[str, str], float] = {}

# Farm counts to plot (matches directory names)
FARM_COUNTS = ["farms_1", "farms_5", "farms_10", "farms_15", "farms_20", "farms_25"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_metadata(path: Path) -> Dict[str, str]:
    """Extract version/farm_count/trial/node from path components."""
    meta = {"version": None, "farm_count": None, "trial": None, "node": None}
    for part in path.parts:
        if part.startswith("version_"):
            meta["version"] = part.split("version_", 1)[1]
        elif part.startswith("farms_"):
            meta["farm_count"] = part
        elif part.startswith("trial_"):
            meta["trial"] = part.split("trial_", 1)[1]
        elif part.startswith("node"):
            meta["node"] = part
    return meta


def apply_offsets(
    df: pd.DataFrame,
    version: str,
    farm_count: str,
    offset_map: Dict[Tuple[str, str], float],
    ts_col: str = "timestamp",
) -> pd.DataFrame:
    """Shift timestamps so that data before the configured offset is dropped."""
    offset = offset_map.get((version, farm_count), 0)
    if offset == 0:
        return df
    df = df[df[ts_col] >= offset].copy()
    df[ts_col] = df[ts_col] - offset
    return df


def ensure_outdir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def subplot_grid(num: int, ncols: int = 2):
    nrows = math.ceil(num / ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(10, 3 * nrows), squeeze=False)
    return fig, axes.flatten()


def set_shared_legend(fig: plt.Figure, axes: Iterable[plt.Axes], loc: str = "upper right") -> None:
    """Use a single legend for all axes in the figure."""
    handles: Optional[List] = None
    labels: Optional[List[str]] = None
    for ax in axes:
        h, l = ax.get_legend_handles_labels()
        if h and labels is None:
            handles, labels = h, l
        leg = ax.get_legend()
        if leg:
            leg.remove()
    if handles and labels:
        fig.legend(handles, labels, loc=loc, bbox_to_anchor=(1, 1))


# ---------------------------------------------------------------------------
# Dataframe builders
# ---------------------------------------------------------------------------

def get_dataframe_cpu(dest: Path, offset_map: Dict[Tuple[str, str], float] | None = None) -> pd.DataFrame:
    pattern = str(dest / "**" / "cpu.csv")
    dfs = []
    for cpu_file in glob.glob(pattern, recursive=True):
        meta = parse_metadata(Path(cpu_file))
        cols = [
            "timestamp",
            "measurement",
            "core_id",
            "cpu",
            "host",
            "physical_id",
            "time_active",
            "time_guest",
            "time_guest_nice",
            "time_idle",
            "time_iowait",
            "time_irq",
            "time_nice",
            "time_softirq",
            "time_steal",
            "time_system",
            "time_user",
        ]
        df = pd.read_csv(cpu_file, names=cols)
        df = df[df.cpu == "cpu-total"].copy()
        df["time_total"] = df.time_active + df.time_idle
        df["util"] = 100 * df.time_active / df.time_total
        df["timestamp"] = df["timestamp"] - df["timestamp"].min()
        if offset_map is not None:
            df = apply_offsets(df, meta["version"], meta["farm_count"], offset_map)
        df["timestamp_m"] = df["timestamp"] / 60
        df["version"] = meta["version"]
        df["farm_count"] = meta["farm_count"]
        df["trial"] = meta["trial"]
        df["node"] = meta["node"]
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


def get_dataframe_memory(dest: Path, offset_map: Dict[Tuple[str, str], float]) -> pd.DataFrame:
    pattern = str(dest / "**" / "mem.csv")
    dfs = []
    for mem_file in glob.glob(pattern, recursive=True):
        meta = parse_metadata(Path(mem_file))
        cols = [
            "timestamp",
            "label",
            "node",
            "active",
            "available",
            "available_percent",
            "buffered",
            "cached",
            "commit_limit",
            "committed_as",
            "dirty",
            "free",
            "high_free",
            "high_total",
            "huge_page_size",
            "huge_pages_free",
            "huge_pages_total",
            "inactive",
            "low_free",
            "low_total",
            "mapped",
            "page_tables",
            "shared",
            "slab",
            "sreclaimable",
            "sunreclaim",
            "swap_cached",
            "swap_free",
            "swap_total",
            "total",
            "used",
            "used_percent",
            "vmalloc_chunk",
            "vmalloc_total",
            "vmalloc_used",
            "wired",
            "write_back",
            "write_back_tmp",
        ]
        df = pd.read_csv(mem_file, names=cols)
        df["timestamp"] = df["timestamp"] - df["timestamp"].min()
        df = apply_offsets(df, meta["version"], meta["farm_count"], offset_map)
        df["timestamp_m"] = df["timestamp"] / 60
        df["version"] = meta["version"]
        df["farm_count"] = meta["farm_count"]
        df["trial"] = meta["trial"]
        df["node"] = meta["node"]
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


def get_dataframe_netio(dest: Path, offset_map: Dict[Tuple[str, str], float]) -> pd.DataFrame:
    pattern = str(dest / "**" / "net.csv")
    dfs = []
    for net_file in glob.glob(pattern, recursive=True):
        meta = parse_metadata(Path(net_file))
        cols = [
            "timestamp",
            "label",
            "node",
            "interface",
            "bytes_sent",
            "bytes_recv",
            *(f"misc{i}" for i in range(100)),
        ]
        df = pd.read_csv(net_file, names=cols)
        df = df[df["interface"] == "eth0"].copy()
        df["timestamp"] = df["timestamp"] - df["timestamp"].min()
        df = apply_offsets(df, meta["version"], meta["farm_count"], offset_map)
        df = df.sort_values("timestamp")
        df["send_rate_kbps"] = df["bytes_sent"].diff().fillna(0) / df["timestamp"].diff().fillna(1) / 1024
        df["recv_rate_kbps"] = df["bytes_recv"].diff().fillna(0) / df["timestamp"].diff().fillna(1) / 1024
        df["timestamp_m"] = df["timestamp"] / 60
        df["version"] = meta["version"]
        df["farm_count"] = meta["farm_count"]
        df["trial"] = meta["trial"]
        df["node"] = meta["node"]
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


def get_dataframe_tick(dest: Path, offset_map: Dict[Tuple[str, str], float]) -> pd.DataFrame:
    pattern = str(dest / "**" / "minecraft_tick_times.csv")
    dfs = []
    for tick_file in glob.glob(pattern, recursive=True):
        meta = parse_metadata(Path(tick_file))
        cols = ["timestamp", "label", "node", "jolokia_endpoint", "tick_duration_ms"]
        df = pd.read_csv(tick_file, names=cols)
        df["timestamp"] = df["timestamp"] - df["timestamp"].min()
        df = apply_offsets(df, meta["version"], meta["farm_count"], offset_map)
        df["timestamp_m"] = df["timestamp"] / 60
        df["version"] = meta["version"]
        df["farm_count"] = meta["farm_count"]
        df["trial"] = meta["trial"]
        df["node"] = meta["node"]
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


# ---------------------------------------------------------------------------
# Plotting helpers
# ---------------------------------------------------------------------------

def plot_time_series(df: pd.DataFrame, x: str, y: str, hue: str, farm_count: str, title: str, ylabel: str, out: Path) -> None:
    ensure_outdir(out.parent)
    custom_params = {"axes.spines.right": False, "axes.spines.top": False}
    sns.set_theme(style="ticks", rc=custom_params)
    ax = sns.lineplot(df, x=x, y=y, hue=hue)
    ax.grid(axis="y")
    ax.set_ylim(bottom=0)
    ax.set_ylabel(ylabel)
    ax.set_xlabel("Time [m]")
    ax.set_title(title)
    plt.savefig(out, dpi=300, bbox_inches="tight")
    plt.clf()


def plot_box(df: pd.DataFrame, x: str, y: str, hue: str, title: str, ylabel: str, out: Path) -> None:
    ensure_outdir(out.parent)
    sns.set_theme(style="ticks")
    ax = sns.boxplot(data=df, x=x, y=y, hue=hue, palette="Pastel2")
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_xlabel(x.capitalize())
    plt.legend()
    plt.savefig(out, dpi=300, bbox_inches="tight")
    plt.clf()


# ---------------------------------------------------------------------------
# Metric-specific plots
# ---------------------------------------------------------------------------

def plot_cpu(df: pd.DataFrame, outdir: Path) -> None:
    if df.empty:
        return
    ensure_outdir(outdir)
    custom_params = {"axes.spines.right": False, "axes.spines.top": False}
    sns.set_theme(style="ticks", rc=custom_params)
    fig, axes = subplot_grid(len(FARM_COUNTS), ncols=3)
    for ax, farm in zip(axes, FARM_COUNTS):
        df_fc = df[df["farm_count"] == farm]
        if df_fc.empty:
            ax.axis("off")
            continue
        sns.lineplot(df_fc, x="timestamp_m", y="util", hue="version", ax=ax)
        ax.set_title(f"{farm}")
        ax.set_ylabel("CPU utilization [%]")
        ax.set_xlabel("Time [m]")
        ax.grid(axis="y")
        ax.set_ylim(bottom=0)
    fig.suptitle("CPU Utilization over Time")
    set_shared_legend(fig, axes)
    fig.tight_layout()
    fig.savefig(outdir / "cpu_over_time.pdf", dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_memory(df: pd.DataFrame, outdir: Path) -> None:
    if df.empty:
        return
    ensure_outdir(outdir)
    custom_params = {"axes.spines.right": False, "axes.spines.top": False}
    sns.set_theme(style="ticks", rc=custom_params)
    fig, axes = subplot_grid(len(FARM_COUNTS), ncols=3)
    for ax, farm in zip(axes, FARM_COUNTS):
        df_fc = df[df["farm_count"] == farm]
        if df_fc.empty:
            ax.axis("off")
            continue
        sns.lineplot(df_fc, x="timestamp_m", y="used_percent", hue="version", ax=ax)
        ax.set_title(f"{farm}")
        ax.set_ylabel("Memory usage [%]")
        ax.set_xlabel("Time [m]")
        ax.grid(axis="y")
        ax.set_ylim(bottom=0)
    fig.suptitle("Memory Usage over Time")
    set_shared_legend(fig, axes)
    fig.tight_layout()
    fig.savefig(outdir / "memory_over_time.pdf", dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_netio(df: pd.DataFrame, outdir: Path) -> None:
    if df.empty:
        return
    ensure_outdir(outdir)
    custom_params = {"axes.spines.right": False, "axes.spines.top": False}
    sns.set_theme(style="ticks", rc=custom_params)
    nrows = len(FARM_COUNTS)
    fig, axes = plt.subplots(nrows, 2, figsize=(12, 3 * nrows), squeeze=False)
    for row, farm in enumerate(FARM_COUNTS):
        df_fc = df[df["farm_count"] == farm]
        if df_fc.empty:
            axes[row][0].axis("off")
            axes[row][1].axis("off")
            continue
        sns.lineplot(df_fc, x="timestamp_m", y="send_rate_kbps", hue="version", ax=axes[row][0])
        axes[row][0].set_title(f"{farm} - Send")
        axes[row][0].set_ylabel("Send rate [kbps]")
        axes[row][0].set_xlabel("Time [m]")
        axes[row][0].grid(axis="y")
        axes[row][0].set_ylim(bottom=0)

        sns.lineplot(df_fc, x="timestamp_m", y="recv_rate_kbps", hue="version", ax=axes[row][1])
        axes[row][1].set_title(f"{farm} - Receive")
        axes[row][1].set_ylabel("Receive rate [kbps]")
        axes[row][1].set_xlabel("Time [m]")
        axes[row][1].grid(axis="y")
        axes[row][1].set_ylim(bottom=0)
    fig.suptitle("Network I/O over Time")
    set_shared_legend(fig, axes.flatten())
    fig.tight_layout()
    fig.savefig(outdir / "netio_over_time.pdf", dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_tick(df: pd.DataFrame, outdir: Path) -> None:
    if df.empty:
        return
    ensure_outdir(outdir)
    custom_params = {"axes.spines.right": False, "axes.spines.top": False}
    sns.set_theme(style="ticks", rc=custom_params)
    fig, axes = subplot_grid(len(FARM_COUNTS), ncols=3)
    for ax, farm in zip(axes, FARM_COUNTS):
        df_fc = df[df["farm_count"] == farm]
        if df_fc.empty:
            ax.axis("off")
            continue
        sns.lineplot(df_fc, x="timestamp_m", y="tick_duration_ms", hue="version", ax=ax)
        ax.set_title(f"{farm}")
        ax.set_ylabel("Tick duration [ms]")
        ax.set_xlabel("Time [m]")
        ax.grid(axis="y")
        ax.set_ylim(bottom=0)
    fig.suptitle("Minecraft Tick Duration over Time")
    set_shared_legend(fig, axes)
    fig.tight_layout()
    fig.savefig(outdir / "tick_over_time.pdf", dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_box_all(
    cpu_df: pd.DataFrame,
    mem_df: pd.DataFrame,
    net_df: pd.DataFrame,
    tick_df: pd.DataFrame,
    outdir: Path,
) -> None:
    metrics = []
    if not cpu_df.empty:
        metrics.append(("util", "CPU utilization [%]", cpu_df, "CPU Utilization"))
    if not mem_df.empty:
        metrics.append(("used_percent", "Memory usage [%]", mem_df, "Memory Usage"))
    if not net_df.empty:
        metrics.append(("send_rate_kbps", "Send rate [kbps]", net_df, "Network Send Rate"))
        metrics.append(("recv_rate_kbps", "Receive rate [kbps]", net_df, "Network Receive Rate"))
    if not tick_df.empty:
        metrics.append(("tick_duration_ms", "Tick duration [ms]", tick_df, "Minecraft Tick Duration"))

    if not metrics:
        return

    ensure_outdir(outdir)
    ncols = 2
    nrows = math.ceil(len(metrics) / ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(12, 4 * nrows), squeeze=False)
    sns.set_theme(style="ticks")
    for ax, (ycol, ylabel, data, title) in zip(axes.flatten(), metrics):
        sns.boxplot(data=data, x="version", y=ycol, hue="farm_count", palette="Pastel2", ax=ax)
        ax.set_title(title)
        ax.set_ylabel(ylabel)
        ax.set_xlabel("Version")
    # Hide any unused axes
    for ax in axes.flatten()[len(metrics):]:
        ax.axis("off")
    fig.suptitle("Resource Utilization (Boxplots)")
    set_shared_legend(fig, axes.flatten())
    fig.tight_layout()
    fig.savefig(outdir / "boxplots_all_metrics.pdf", dpi=300, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Offset computation from CPU peaks
# ---------------------------------------------------------------------------

def compute_offsets_from_cpu(cpu_df: pd.DataFrame) -> Dict[Tuple[str, str], float]:
    """
    Compute per-(version, farm_count) offsets by detecting the first peak in CPU util.
    For each trial, take the timestamp of the max util (after aligning to start).
    For each (version, farm_count), use the median peak time, then double it to
    skip past the initial spike.
    """
    offsets: Dict[Tuple[str, str], float] = {}
    if cpu_df.empty:
        return offsets
    peak_rows = []
    grouped = cpu_df.groupby(["version", "farm_count", "trial"])
    for (version, farm, trial), g in grouped:
        if g.empty:
            continue
        peak_ts = g.loc[g["util"].idxmax(), "timestamp"]
        peak_rows.append((version, farm, peak_ts))
    if not peak_rows:
        return offsets
    peaks_df = pd.DataFrame(peak_rows, columns=["version", "farm_count", "peak_ts"])
    for (version, farm), group in peaks_df.groupby(["version", "farm_count"]):
        offsets[(version, farm)] = group["peak_ts"].median() * 2.0
    return offsets


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # if len(sys.argv) < 2:
    #     print("Usage: python analyze_metrics.py <dest_root>")
    #     sys.exit(1)

    dest = Path("/var/scratch/dsys2590/yardstick/20251209T1500/").expanduser().resolve()
    outdir = Path("./plots_altogether")
    ensure_outdir(outdir)

    # Load CPU once to derive offsets, then reload with offsets applied.
    cpu_df_raw = get_dataframe_cpu(dest, offset_map=None)
    offset_map = {**OFFSETS}
    auto_offsets = compute_offsets_from_cpu(cpu_df_raw)
    # Do not overwrite explicit OFFSETS; only add missing entries.
    for key, val in auto_offsets.items():
        offset_map.setdefault(key, val)

    cpu_df = get_dataframe_cpu(dest, offset_map=offset_map)
    mem_df = get_dataframe_memory(dest, offset_map=offset_map)
    net_df = get_dataframe_netio(dest, offset_map=offset_map)
    tick_df = get_dataframe_tick(dest, offset_map=offset_map)

    if cpu_df.empty and mem_df.empty and net_df.empty and tick_df.empty:
        print("No data found under", dest)
        sys.exit(0)

    if not cpu_df.empty:
        plot_cpu(cpu_df, outdir / "cpu")
    if not mem_df.empty:
        plot_memory(mem_df, outdir / "mem")
    if not net_df.empty:
        plot_netio(net_df, outdir / "netio")
    if not tick_df.empty:
        plot_tick(tick_df, outdir / "tick")
    plot_box_all(cpu_df, mem_df, net_df, tick_df, outdir / "boxplots")


if __name__ == "__main__":
    main()
