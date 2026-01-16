import sys
import glob
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns

debug = False


dest = "/var/scratch/dsys2590/yardstick/20251209T1500/"
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

