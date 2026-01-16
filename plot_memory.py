import sys
import glob
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns

debug = True


dest = "/var/scratch/dsys2590/yardstick/20251209T1500/"

mem_files = glob.glob(f"{dest}/**/vanillamc-*/../*/mem.csv", recursive=True)


# Extract the mem data
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
    # df["timestamp"] = df["timestamp"].transform(lambda x: x - x.min())
    df["node"] = Path(mem_file).resolve().parent.parent.name
    df["version"] = Path(mem_file).resolve().parent.parent.parent.parent.parent.name
    df["iter"] = Path(mem_file).resolve().parent.parent.parent.name[-1]
    df["farm_count"] = Path(mem_file).resolve().parent.parent.parent.parent.name
    df["timestamp"] = df["timestamp"].transform(lambda x: x - x.min())
    df["timestamp_m"] = df["timestamp"] / 60

    dfs.append(df)
df = pd.concat(dfs, ignore_index=True)


if debug:
    # For each farm_count, plot their memory usage separatedly
    for farm_count in ["farms_1", "farms_5", "farms_10", "farms_15", "farms_20", "farms_25"]:
        df_fc = df[df["farm_count"] == farm_count]
    
        custom_params = {"axes.spines.right": False, "axes.spines.top": False}
        sns.set_theme(style="ticks", rc=custom_params)
        ax = sns.lineplot(df_fc, x="timestamp_m", y="used_percent", hue="version")
        ax.grid(axis="y")
        ax.set_ylim(bottom=0)
        ax.set_ylabel("Memory usage [%]")
        ax.set_xlabel("Time [m]")
    
        # Save figure under './plots' directory
        plt.savefig(f"./plots/mem/memory_usage_over_time_{farm_count}.png", dpi=300)
        
        # Clear the current figure for the next plot
        plt.clf()
        
# For each version, make a boxplot for each farm count
ax = sns.boxplot(data=df, x="version", y="used_percent", hue="farm_count", palette="Pastel2")
ax.set_title("Memory Utilization")
ax.set_ylabel("Memory Utilization [%]")
ax.set_xlabel("Version")
plt.legend()
plt.savefig("./plots/mem/memory_utilization_boxplot.png", dpi=300)
