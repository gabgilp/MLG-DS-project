import time
from datetime import datetime, timedelta
from yardstick_benchmark.monitoring import Telegraf
import yardstick_benchmark
from yardstick_benchmark.provisioning import Das
import os
from pathlib import Path




if __name__ == "__main__":
    # Start a 5 min das 5 with 1 node and run telegraf monitoring only
    das = Das()
    nodes = das.provision(num=1, time_s=600)
    try:
        telegraf = Telegraf(nodes)
        telegraf.add_input_jolokia_agent(nodes[0])
        telegraf.add_input_execd_minecraft_ticks(nodes[0])
        telegraf.deploy()
        telegraf.start()

        print("Monitoring for 0.5 minutes...")
        time.sleep(30)
        
        # Fetch monitoring data
        timestamp = (
            datetime.now()
            .isoformat(timespec="minutes")
            .replace("-", "")
            .replace(":", "")
        )
        dest = Path(f"/var/scratch/{os.getlogin()}/yardstick/{timestamp}")
        yardstick_benchmark.fetch(dest, nodes)

        telegraf.stop()
        telegraf.cleanup()
    finally:
        yardstick_benchmark.clean(nodes)
        das.release(nodes)