import sys
import glob
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns

debug = True

dest = "/var/scratch/dsys2590/yardstick/20251209T1500/"

net_files = glob.glob(f"{dest}/**/vanillamc-*/../*/net.csv", recursive=True)

dfs = []
for net_file in net_files:
    df = pd.read_csv(net_file, names=[
        "timestamp", "label", "node", "interface", "bytes_sent", "bytes_recv",
        # There are more columns, but we don't need them and I'm not sure what they are
        *(f"misc{i}" for i in range(100))
    ])
    df = df[df["interface"] == "eth0"]
    df["timestamp"] = df["timestamp"].transform(lambda x: x - x.min())
    df["timestamp_m"] = df["timestamp"] / 60
    df["bytes_sent"] = df["bytes_sent"].transform(lambda x: x - df[df["timestamp"] == 0]["bytes_sent"])
    df["send_rate"] = df["bytes_sent"] / df["timestamp"]
    df["send_rate_kbps"] = df["send_rate"] / 1024
    
    df["recv_rate"] = df["bytes_recv"] / df["timestamp"]
    df["recv_rate_kbps"] = df["recv_rate"] / 1024
    
    df["node"] = Path(net_file).resolve().parent.parent.name
    df["version"] = Path(net_file).resolve().parent.parent.parent.parent.parent.name
    df["iter"] = Path(net_file).resolve().parent.parent.parent.name[-1]
    df["farm_count"] = Path(net_file).resolve().parent.parent.parent.parent.name
    
    dfs.append(df)
df = pd.concat(dfs, ignore_index=True)


if debug == True:
    # For each farm count, plot their netio separately
    for farm_count in ["farms_1", "farms_5", "farms_10", "farms_15", "farms_20", "farms_25"]:
        df_fc = df[df["farm_count"] == farm_count]
        custom_params = {"axes.spines.right": False, "axes.spines.top": False}
        sns.set_theme(style="ticks", rc=custom_params)
        
        # Plot for send rate over time
        plt.subplot(2, 1, 1)
        ax = sns.lineplot(df_fc, x="timestamp_m", y="send_rate_kbps", hue="version")
        ax.grid(axis="y")
        ax.set_ylim(bottom=0)
        ax.set_ylabel("Network send rate [kbps]")
        ax.set_xlabel("Time [m]")
        
        # Plot for recv rate over time, two plots in one figure
        plt.subplot(2, 1, 2)
        ax = sns.lineplot(df_fc, x="timestamp_m", y="recv_rate_kbps", hue="version")
        ax.grid(axis="y")
        ax.set_ylim(bottom=0)
        ax.set_ylabel("Network receive rate [kbps]")
        ax.set_xlabel("Time [m]")

        # Save figure under './plots' directory
        plt.savefig(f"./plots/netio/network_send_recv_rate_over_time_{farm_count}.png", dpi=300)
        
        # Clear the current figure for the next plot
        plt.clf()
    

# For each version, make a boxplot for each farm count
plt.subplot(2, 1, 1)
ax = sns.boxplot(data=df, x="version", y="send_rate_kbps", hue="farm_count", palette="Pastel2")
ax.set_title("Network Send Rate")
ax.set_ylabel("Network Send Rate [kbps]")
ax.set_xlabel("Version")

plt.subplot(2, 1, 2)
ax = sns.boxplot(data=df, x="version", y="recv_rate_kbps", hue="farm_count", palette="Pastel2")
ax.set_title("Network Receive Rate")
ax.set_ylabel("Network Receive Rate [kbps]")
ax.set_xlabel("Version")

plt.legend()
plt.savefig("./plots/netio/network_send_recv_rate_boxplot.png", dpi=300)