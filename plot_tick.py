import sys
import glob
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

debug = True


dest = "/var/scratch/dsys2590/yardstick/20251209T1500/"
tick_times_file = glob.glob(f"{dest}/**/vanillamc-*/../*/minecraft_tick_times.csv", recursive=True)

dfs = []
for tick_file in tick_times_file:
    df = pd.read_csv(tick_file, names = ["timestamp", "label", "node", "jolokia_endpoint", "tick_duration_ms"])
    df["timestamp"] = df["timestamp"].transform(lambda x: x - x.min())
    df["timestamp_m"] = df["timestamp"] / 60
    
    df["node"] = Path(tick_file).resolve().parent.parent.name
    df["version"] = Path(tick_file).resolve().parent.parent.parent.parent.parent.name
    df["iter"] = Path(tick_file).resolve().parent.parent.parent.name[-1]
    df["farm_count"] = Path(tick_file).resolve().parent.parent.parent.parent.name

    dfs.append(df)
df = pd.concat(dfs, ignore_index=True)


if debug:
    # For each farm count, plot their tick times separately
    for farm_count in ["farms_1", "farms_5", "farms_10", "farms_15", "farms_20", "farms_25"]:
        df_fc = df[df["farm_count"] == farm_count]
    
        custom_params = {"axes.spines.right": False, "axes.spines.top": False}
        sns.set_theme(style="ticks", rc=custom_params)
        ax = sns.lineplot(df_fc, x="timestamp_m", y="tick_duration_ms", hue="version")
        ax.grid(axis="y")
        ax.set_ylim(bottom=0)
        ax.set_ylabel("Minecraft Tick Duration [ms]")
        ax.set_xlabel("Time [m]")
    
        # Save figure under './plots' directory
        plt.savefig(f"./plots/tick/minecraft_tick_duration_over_time_{farm_count}.png", dpi=300)
        
        # Clear the current figure for the next plot
        plt.clf()
        
# For each version, make a boxplot for each farm count
ax = sns.boxplot(data=df, x="version", y="tick_duration_ms", hue="farm_count", palette="Pastel2")
ax.set_title("Minecraft Tick Duration")
ax.set_ylabel("Minecraft Tick Duration [ms]")
ax.set_xlabel("Version")
plt.legend()
plt.savefig(f"./plots/tick/minecraft_tick_duration_boxplot.png", dpi=300)
