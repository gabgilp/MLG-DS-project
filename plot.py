import sys
import glob
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

debug = False

if len(sys.argv) < 2:
    print("Missing argument: data directory name")
    exit(1)

dest = sys.argv[1]
raw_data_files = glob.glob(f"{dest}/**/metrics-*.csv", recursive=True)

# Split metrics into separate files
for raw_data_file in raw_data_files:
    metrics_file = Path(raw_data_file)
    keys = {}
    with open(metrics_file) as fin:
        for line in fin:
            first_delim = line.find(",")
            second_delim = line.find(",", first_delim+1)
            key = line[first_delim+1:second_delim]
            if key not in keys:
                keys[key] = open(metrics_file.parent / f"{key}.csv", "w+")
            keys[key].write(line)
    for key, fd in keys.items():
        fd.close()


def offset_times(df):
    # TODO: verify if this gives the correct offset
    df["timestamp"] = df["timestamp"].replace(mapping)


def get_cpu_df():
    server_cpus = glob.glob(f"{dest}/**/vanillamc-*/../*/cpu.csv", recursive=True)

    dfs = []
    for cpu_file in server_cpus:
        df = pd.read_csv(cpu_file, names=["timestamp", "measurement", "core_id", "cpu", "host", "physical_id", "time_active", "time_guest",
                         "time_guest_nice", "time_idle", "time_iowait", "time_irq", "time_nice", "time_softirq", "time_steal", "time_system", "time_user"])
        df["node"] = Path(cpu_file).resolve().parent.parent.name
        df["version"] = Path(cpu_file).resolve().parent.parent.parent.name
        df["iter"] = Path(cpu_file).resolve().parent.parent.parent.parent.name
        df = df[df.cpu == "cpu-total"]
        df['time_total'] = df.time_active + df.time_idle
        df['util'] = 100 * df.time_active / df.time_total
        df["timestamp_abs"] = df["timestamp"]
        df["timestamp"] = df["timestamp"].transform(lambda x: x - x.min())
        # There is an increase when players arrive
        steep_increase = df[(df["util"] > 5) & (
            df["timestamp"] > 120)]["timestamp"].min()
        df["timestamp"] = df["timestamp"].transform(lambda x: x - steep_increase)
        df["timestamp_m"] = df["timestamp"] / 60
        # very fancy
        df["players"] = np.where(
            df["timestamp_m"].between(0, 1),
            5,
            np.where(
                df["timestamp_m"].between(1, 2),
                10,
                np.where(
                    df["timestamp_m"].between(2, 3),
                    20,
                    0
                )
            )
        )
        df = df.sort_values("util", ascending=False).drop_duplicates(
            subset=["timestamp", "cpu"], keep="first")
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True)


def plot_cpu(plot_ax, boxplot_ax):
    df = get_cpu_df()
    if not debug:
        # If you plan to debug: check if the plots line up
        df = df[df["timestamp_m"].between(-0.5, 3.5)]
        boxplot_ax.set_xlim(-0.5, 3.5)

    custom_params = {"axes.spines.right": False, "axes.spines.top": False}
    sns.set_theme(style="ticks", rc=custom_params)
    ax = sns.lineplot(df, x="timestamp_m", y="util", hue="version", ax=plot_ax)
    ax.grid(axis="y")
    ax.set_title("CPU Utilization")
    ax.set_ylim(bottom=0)
    ax.set_ylabel("CPU utilization [%]")
    ax.set_xlabel("Time [m]")
    ax.legend([], [], frameon=False)

    # Take the average of the entire minute
    avg_util = df.groupby(["version", "iter", "players"])["util"].mean().reset_index()
    avg_util = avg_util[avg_util["players"] != 0]

    ax = sns.boxplot(data=avg_util, x="version", y="util", hue="players", palette="Pastel2", ax=boxplot_ax)
    ax.set_title("CPU Utilization")
    ax.set_ylabel("CPU Utilization [%]")
    ax.set_xlabel("Version")
    ax.legend([], [], frameon=False)


def get_tick_df():
    tick_times_file = glob.glob(f"{dest}/**/vanillamc-*/../*/minecraft_tick_times.csv", recursive=True)

    dfs = []
    for tick_file in tick_times_file:
        df = pd.read_csv(tick_file, names = ["timestamp", "label", "node", "jolokia_endpoint", "tick_duration_ms"])
        offset_times(df)
        # df["timestamp"] = df["timestamp"].transform(lambda x: x - x.min())
        df["timestamp_m"] = df["timestamp"] / 60
        df["version"] = Path(tick_file).resolve().parent.parent.parent.name
        df["iter"] = Path(tick_file).resolve().parent.parent.parent.parent.name
        # very fancy
        df["players"] = np.where(
            df["timestamp_m"].between(0, 1),
            5,
            np.where(
                df["timestamp_m"].between(1, 2),
                10,
                np.where(
                    df["timestamp_m"].between(2, 3),
                    20,
                    0
                )
            )
        )

        dfs.append(df)
    return pd.concat(dfs, ignore_index=True)


def plot_tick(plot_ax, boxplot_ax):
    df = get_tick_df()
    if not debug:
        df = df[df["timestamp_m"].between(-0.5, 3.5)]
        boxplot_ax.set_xlim(-0.5, 3.5)

    custom_params = {"axes.spines.right": False, "axes.spines.top": False}
    sns.set_theme(style="ticks", rc=custom_params)
    ax = sns.lineplot(df, x="timestamp_m", y="tick_duration_ms", hue="version", ax=plot_ax)
    ax.grid(axis="y")
    ax.set_title("Tick duration")
    ax.set_ylim(bottom=0)
    ax.set_ylabel("Tick duration [ms]")
    ax.set_xlabel("Time [m]")
    ax.legend([], [], frameon=False)

    # Take the average of the entire minute
    avg_td = df.groupby(["version", "iter", "players"])["tick_duration_ms"].mean().reset_index()
    avg_td = avg_td[avg_td["players"] != 0]

    ax = sns.boxplot(data=avg_td, x="version", y="tick_duration_ms", hue="players", palette="Pastel2", ax=boxplot_ax)
    ax.set_title("Tick duration")
    ax.set_ylabel("Tick duration [ms]")
    ax.set_xlabel("Version")
    # There are fliers in the thousands
    ax.set_ylim(0, 300)
    ax.legend([], [], frameon=False)


def get_mem_df():
    mem_files = glob.glob(f"{dest}/**/vanillamc-*/../*/mem.csv", recursive=True)

    dfs = []
    for mem_file in mem_files:
        df = pd.read_csv(mem_file, names=[
            "timestamp", "label", "node", "active", "available",
            "available_percent", "buffered", "cached", "commit_limit", "committed_as", "dirty",
            "free", "high_free", "high_total", "huge_page_size", "huge_pages_free",
            "huge_pages_total", "inactive", "low_free", "low_total", "mapped", "page_tables",
            "shared", "slab", "sreclaimable", "sunreclaim", "swap_cached", "swap_free",
            "swap_total", "total", "used", "used_percent", "vmalloc_chunk", "vmalloc_total",
            "vmalloc_used", "wired", "write_back", "write_back_tmp"
        ])
        offset_times(df)
        # df["timestamp"] = df["timestamp"].transform(lambda x: x - x.min())
        df["timestamp_m"] = df["timestamp"] / 60
        df["version"] = Path(mem_file).resolve().parent.parent.parent.name
        df["iter"] = Path(mem_file).resolve().parent.parent.parent.parent.name
        # very fancy
        df["players"] = np.where(
            df["timestamp_m"].between(0, 1),
            5,
            np.where(
                df["timestamp_m"].between(1, 2),
                10,
                np.where(
                    df["timestamp_m"].between(2, 3),
                    20,
                    0
                )
            )
        )

        dfs.append(df)
    return pd.concat(dfs, ignore_index=True)


def plot_mem(plot_ax, boxplot_ax):
    df = get_mem_df()
    if not debug:
        df = df[df["timestamp_m"].between(-0.5, 3.5)]
        boxplot_ax.set_xlim(-0.5, 3.5)

    custom_params = {"axes.spines.right": False, "axes.spines.top": False}
    sns.set_theme(style="ticks", rc=custom_params)
    ax = sns.lineplot(df, x="timestamp_m", y="used_percent", hue="version", ax=plot_ax)
    ax.grid(axis="y")
    ax.set_title("Memory Utilization")
    ax.set_ylim(bottom=0)
    ax.set_ylabel("Tick duration [ms]")
    ax.set_xlabel("Time [m]")
    ax.legend([], [], frameon=False)

    # Take the average of the entire minute
    avg_td = df.groupby(["version", "iter", "players"])["used_percent"].mean().reset_index()
    avg_td = avg_td[avg_td["players"] != 0]

    ax = sns.boxplot(data=avg_td, x="version", y="used_percent", hue="players", palette="Pastel2", ax=boxplot_ax)
    ax.set_title("Memory Utilization")
    ax.set_ylabel("Memory Utilization [%]")
    ax.set_xlabel("Version")
    ax.legend([], [], frameon=False)


cpu_df = get_cpu_df()
mapping = pd.Series(cpu_df["timestamp"].values, index=cpu_df["timestamp_abs"]).to_dict()

fig_plot, axs_plot = plt.subplots(3, 2, figsize=(6, 7))
fig_boxplot, axs_boxplot = plt.subplots(3, 2, figsize=(6, 7))

# metrics: ["RAM usage", "CPU load", "Disk usage", "Network usage", "Tick duration"]
plot_mem(axs_plot[0, 0], axs_boxplot[0, 0])
plot_cpu(axs_plot[0, 1], axs_boxplot[0, 1])
plot_tick(axs_plot[2, 0], axs_boxplot[2, 0])

axs_plot[2, 0].legend(loc=(1.5, 0.5))
fig_plot.subplots_adjust(0.11, 0.11, 0.95, 0.95, hspace=0.7, wspace=0.3)
axs_boxplot[2, 0].legend(loc=(1.5, 0.5))
fig_boxplot.subplots_adjust(0.11, 0.11, 0.95, 0.95, hspace=0.7, wspace=0.3)
axs_plot[2, 1].remove()
axs_boxplot[2, 1].remove()

fig_plot.savefig("plot.pdf")
fig_boxplot.savefig("boxplot.pdf")
