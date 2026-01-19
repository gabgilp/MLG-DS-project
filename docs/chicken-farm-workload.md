# Chicken farm workload

This workload builds and runs an array of automated chicken farms to stress-test entity ticking, redstone, hoppers, and chunk loading while bots observe in spectator mode.


## Workload behavior (see `example_chicken_farm.py`)
- Deployment installs Node.js 22 with `nvm`, copies workload scripts, and launches `player_count` bots (default 5 in the example script).
- `set_spawn.js` connects over RCON, sets world spawn at `SPAWN_X,4,SPAWN_Z`, and ops bots `bot-0..bot-n`.
- Bot 0 (builder) runs `chicken_farm.js`: sets day/clear/peaceful, disables daylight cycle and mob spawning, switches to creative, clears a padded area with `/fill ... air`, builds a 7×3×6 farm blueprint via `/setblock`, clones the farm in a grid (12×8 spacing) for each player slot, summons 8 chickens per farm, seeds dispensers with eggs, and places hopper minecarts.
- Other bots wait for the structure to appear, then all bots switch to spectator and teleport above their assigned farm; chunk-load checks ensure the area is ready before watching.
- Duration is passed via `DURATION` (example sets 0s warmup + 300s measurement + 30s buffer), but the example script currently only keeps the server up for ~60s before shutdown.

## Running the example
1) Follow `docs/tutorial.md` to prepare the Yardstick environment on DAS.
2) Run `python example_chicken_farm.py` (assumes `ansible.cfg` is written next to the script and `ANSIBLE_CONFIG` is set by the script).
3) The script starts Telegraf, the Minecraft server, and the chicken-farm workload, then sleeps 60s before stopping everything.
4) Results are copied to `/var/scratch/$USER/yardstick/$TIMESTAMP/`; logs from each bot remain on the workload node.
5) To process the result, first run `analyze_metrics.py` with the collected data under `/var/scratch/$USER/yardstick/$TIMESTAMP/`, then run `plot_cpu.py`, `plot_memory.py`, `plot_netio.py`, `plot_tick.py` to generate the corresponding plot of the result. This will create a collection of plots across different workloads for different metrics.
