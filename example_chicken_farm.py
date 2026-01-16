from datetime import datetime, timedelta
import time
from pathlib import Path
import os

from yardstick_benchmark.provisioning import Das
from yardstick_benchmark.monitoring import Telegraf
from yardstick_benchmark.games.minecraft.server.J1164 import Java1164
from yardstick_benchmark.games.minecraft.workload import ChickenFarm
import yardstick_benchmark

# Local ansible config, same pattern as example_vanilla.py
ansible_config_path = "ansible.cfg"
content = """\
[defaults]
host_key_checking = False

[ssh_connection]
pipelining = True
ssh_args = -o ControlMaster=auto -o ControlPersist=60s
"""
with open(ansible_config_path, "w") as f:
    f.write(content)
os.environ["ANSIBLE_CONFIG"] = str(Path.cwd() / ansible_config_path)


if __name__ == "__main__":
    das = Das()
    # node0: server, node1: workload
    nodes = das.provision(num=2)

    # Configurable durations
    warmup = 0  # seconds to let world/workload settle before measuring, actually discard this, telegraf starts at the beginning anyway
    measurement = 300  # seconds to keep workload/monitoring running

    try:
        yardstick_benchmark.clean(nodes)

        # Monitoring
        telegraf = Telegraf(nodes)
        telegraf.add_input_jolokia_agent(nodes[0])
        telegraf.add_input_execd_minecraft_ticks(nodes[0])
        telegraf.deploy()
        telegraf.start()

        # Server 
        server = Java1164(nodes[:1], version="1.20.1")
        server.deploy()
        server.start()

        # Workload: chicken farms, one per player/node in workload group
        workload = ChickenFarm(
            nodes[1:],
            nodes[0].host,
            duration=timedelta(seconds=warmup + measurement + 30),
            spawn_x=0,
            spawn_y=0,
            player_count=5
        )
        workload.deploy()
        workload.start()

        # print(f"Warmup for {warmup} seconds...")
        # time.sleep(warmup)
        print(f"Sleep for 60 seconds...")
        time.sleep(60)

        # Shutdown
        server.stop()
        server.cleanup()

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
