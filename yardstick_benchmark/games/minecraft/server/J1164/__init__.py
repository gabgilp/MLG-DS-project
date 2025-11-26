import json
from pathlib import Path
from typing import Dict, List, Union, Optional

from yardstick_benchmark.model import Node, RemoteApplication


_VANILLA_VERSION_FILE = Path(__file__).parent / "vanilla_version_urls.json"


def _select_vanilla_version(version: Union[str, None]) -> Dict[str, str]:
    with _VANILLA_VERSION_FILE.open() as f:
        versions: List[Dict[str, str]] = json.load(f)

    if not versions:
        raise ValueError("vanilla_version_urls.json does not contain any versions")

    if version is None:
        chosen = versions[0]
    else:
        chosen = next(
            (entry for entry in versions if entry["version"] == version), None
        )
        if chosen is None:
            available = ", ".join(entry["version"] for entry in versions)
            raise ValueError(
                f"Vanilla version '{version}' not found. Available: {available}"
            )

    for key in ("url", "dest", "version", "java_version"):
        if key not in chosen:
            raise ValueError(f"Missing '{key}' for vanilla version {chosen}")

    return chosen


def _java_module_from_version(java_version: str) -> str:
    normalized = str(java_version)
    if normalized.startswith(("8", "1.8")):
        return "java/jdk-1.8"
    if normalized.startswith("17"):
        return "java/jdk-17"
    raise ValueError(f"Unsupported java_version '{java_version}' for vanilla server")


class Java1164(RemoteApplication):
    def __init__(self, nodes: list[Node], version: Optional[str] = None):
        version_entry = _select_vanilla_version(version)
        java_version = str(version_entry["java_version"])

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
                "vanilla_server_url": version_entry["url"],
                "vanilla_server_jar": version_entry["dest"],
                "vanilla_version": version_entry["version"],
                "java_version": java_version,
                "java_module": _java_module_from_version(java_version),
            },
        )
