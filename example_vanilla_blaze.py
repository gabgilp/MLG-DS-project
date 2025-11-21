from yardstick_benchmark.provisioning import Das
from yardstick_benchmark.monitoring import Telegraf
from yardstick_benchmark.games.minecraft.server.J1164 import Java1164
from yardstick_benchmark.games.minecraft.workload import BlazeSpawner
import yardstick_benchmark
from time import sleep
from datetime import datetime, timedelta
from pathlib import Path
import os

if __name__ == "__main__":

    ### DEPLOYMENT ENVIRONMENT ###

    # The DAS compute cluster is a medium-sized cluster for research and education.
    # We use it in this example to provision bare-metal machines to run our performance
    # evaluation.
    das = Das()
    # We reserve 2 nodes.
    nodes = das.provision(num=2)

    try:
        # Just in case, we remove data that may have been left from a previous run.
        yardstick_benchmark.clean(nodes)

        ### METRICS ###

        # # Telegraf[](https://www.influxdata.com/time-series-platform/telegraf/)
        # # is the metric collection tool we use to collect performance metrics from the
        # # nodes and any applications deployed on these nodes.
        telegraf = Telegraf(nodes)
        # # We plan to deploy our Minecraft-like game server on node 0.
        # # To obtain application level metrics from the game server,
        # # the next two lines configure node 0 to run additional metric collection
        # # tools.
        telegraf.add_input_jolokia_agent(nodes[0])
        telegraf.add_input_execd_minecraft_ticks(nodes[0])
        # # Perform the actual deployment of Telegraf.
        # # This includes downloading the Telegraf executable and preparing configuration
        # # files.
        res = telegraf.deploy()
        # # Start Telegraf on all remote nodes.
        telegraf.start()

        ### System Under Test (SUT) ###

        # VanillaMC handles deployment of the official Mojang vanilla server JAR.
        # Pass a version from yardstick_benchmark/games/minecraft/server/J1164/vanilla_version_urls.json
        # (defaults to the first entry if omitted).
        vanillamc = Java1164(nodes[:1], version="1.20.1")
        # Perform the deployment, including downloading the vanilla server JAR and
        # correctly configuring the server's properties file.
        vanillamc.deploy()
        # Start the vanilla server.
        vanillamc.start()

        ### WORKLOAD - BLAZE SPAWNER ###

        # BlazeSpawner will spawn blazes in waves and configure the server for users
        # This creates a combat arena with 1000 blazes spawned in waves of 10
        blaze_spawner = BlazeSpawner(
            nodes=nodes[1:],  # Use worker nodes for the spawner bot
            server_host=nodes[0].host,  # Server is on first node
            duration=timedelta(hours=2),  # 2 hour session
            blaze_count=1000,  # Total blazes to spawn
            spawn_area_size=100,  # 100x100 block spawn area
            spawn_height=100,  # Spawn at Y=100
            allow_users=True,  # Allow players to join after setup
            bots_per_node=1
        )

        print("Deploying blaze spawner...")
        blaze_spawner.deploy()

        print("Starting blaze spawner - this will take time as blazes spawn in waves...")
        print("Expected time: ~100 minutes for 1000 blazes (10 per minute)")
        blaze_spawner.start()

        sleep_time = 7200  # 2 hours to allow full blaze spawning process
        print(f"Blaze spawner is running - monitoring for {sleep_time/60:.0f} minutes")
        print("The spawner will:")
        print("- Spawn blazes in waves of 10 every minute")
        print("- Configure server settings for user access")
        print("- Allow players to join and fight blazes")
        sleep(sleep_time)

        print("Stopping blaze spawner...")
        blaze_spawner.stop()
        blaze_spawner.cleanup()

        vanillamc.stop()
        vanillamc.cleanup()

        telegraf.stop()
        telegraf.cleanup()

        timestamp = (
            datetime.now()
            .isoformat(timespec="minutes")
            .replace("-", "")
            .replace(":", "")
        )
        dest = Path(f"/var/scratch/{os.getlogin()}/yardstick/{timestamp}")
        yardstick_benchmark.fetch(dest, nodes)
    finally:
        yardstick_benchmark.clean(nodes)
        das.release(nodes)
