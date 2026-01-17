# Flying spectator benchmark

The flying spectator benchmark starts a server with bots in spectator mode that fly through the world,
which lets us evaluate the performance of world generation and chunk loading.
To run this benchmark,

1. Connect to the DAS-5 cluster and enter a virtual envirionment with the dependencies installed.
   See the [tutorial](tutorial.md) for details.
2. Run `benchmark.py`.
   This takes a couple of hours and creates the directory `/var/scratch/$USER/yardstick/$TIMESTAMP/`
   that contains the raw data.
3. Run `plot.py` with the raw data directory as argument.
   This creates `plot.pdf` with metrics over time,
   and `boxplot.pdf` with metrics per player count.
