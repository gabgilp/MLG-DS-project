import sys
import glob
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns

debug = False

if len(sys.argv) < 2:
    print("Missing argument: data directory name")
    exit(1)

dest = sys.argv[1]
raw_data_files = glob.glob(f"{dest}/**/metrics-*.csv", recursive=True)

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
    df["timestamp"] = df["timestamp"].transform(lambda x: x - x.min())
    # There is an increase when players arrive
    steep_increase = df[(df["util"] > 5) & (
        df["timestamp"] > 120)]["timestamp"].min()
    df["timestamp"] = df["timestamp"].transform(lambda x: x - steep_increase)
    df["timestamp_m"] = df["timestamp"] / 60
    df = df.sort_values("util", ascending=False).drop_duplicates(
        subset=["timestamp", "cpu"], keep="first")
    dfs.append(df)
df = pd.concat(dfs, ignore_index=True)

if debug:
    # If you plan to debug: check if the plots line up
    custom_params = {"axes.spines.right": False, "axes.spines.top": False}
    sns.set_theme(style="ticks", rc=custom_params)
    ax = sns.lineplot(df, x="timestamp_m", y="util", hue="version")
    ax.grid(axis="y")
    ax.set_ylim(bottom=0)
    ax.set_ylabel("CPU utilization [%]")
    ax.set_xlabel("Time [m]")
    plt.show()

p5 = df[df["timestamp_m"].between(0, 1)]
p10 = df[df["timestamp_m"].between(1, 2)]
p20 = df[df["timestamp_m"].between(2, 3)]

for p, n in zip([p5, p10, p20], [5, 10, 20]):
    util = p.groupby("version")["util"]
    plt.errorbar(util.mean().index, util.mean(), yerr=util.std(),
                 capsize=3, fmt="-o", label=f"{n} players")

plt.legend()
plt.show()
