from yardstick_benchmark.model import RemoteApplication, Node
from pathlib import Path
import os
from datetime import timedelta


class Fly(RemoteApplication):
    def __init__(
        self,
        nodes: list[Node],
        server_host: str,
        duration: timedelta = timedelta(seconds=200),
        spawn_x: int = 0,
        spawn_y: int = 0,
        workload_variant: str = "fly",
    ):
        super().__init__(
            "walkaround",
            nodes,
            Path(__file__).parent / "bot_deploy.yml",
            Path(__file__).parent / "bot_start.yml",
            Path(__file__).parent / "bot_stop.yml",
            Path(__file__).parent / "bot_cleanup.yml",
            extravars={
                "hostnames": [n.host for n in nodes],
                "scripts": [
                    str(Path(__file__).parent / "set_spawn.js"),
                    str(Path(__file__).parent / "bot.js"),
                    str(Path(__file__).parent / "package.json"),
                    str(Path(__file__).parent / "package-lock.json"),
                ],
                "duration": duration.total_seconds(),
                "mc_host": server_host,
                "spawn_x": spawn_x,
                "spawn_y": spawn_y,
                "workload_variant": workload_variant,
            },
        )
