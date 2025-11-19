from yardstick_benchmark.model import RemoteApplication, Node
import os
from pathlib import Path


class Java1164(RemoteApplication):
    def __init__(self, nodes: list[Node]):
        super().__init__(
            "vanillamc",
            nodes,
            Path(__file__).parent / "vanilla_deploy.yml",
            Path(__file__).parent / "vanilla_start.yml",
            Path(__file__).parent / "vanilla_stop.yml",
            Path(__file__).parent / "vanilla_cleanup.yml",
            extravars={
                "hostnames": [n.host for n in nodes],
                "vanilla_template": str(Path(__file__).parent / "server.properties.j2"),
            },
        )
