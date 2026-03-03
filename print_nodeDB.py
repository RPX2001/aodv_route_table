#!/usr/bin/env python3
"""Connect to a Meshtastic device over serial and print/stream NodeDB details."""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import meshtastic.serial_interface
from meshtastic.mesh_interface import MeshInterface


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Print or stream Meshtastic nodes from a serial-connected device."
    )
    parser.add_argument(
        "--port",
        dest="port",
        type=str,
        default=None,
        help="Serial port path (example: /dev/ttyUSB0). If omitted, auto-detect is used.",
    )
    parser.add_argument(
        "--timeout",
        dest="timeout",
        type=int,
        default=60,
        help="Timeout in seconds for connection/config download.",
    )
    parser.add_argument(
        "--exclude-self",
        dest="exclude_self",
        action="store_true",
        help="Exclude local node from output.",
    )
    parser.add_argument(
        "--stream",
        dest="stream",
        action="store_true",
        help="Continuously stream NodeDB updates.",
    )
    parser.add_argument(
        "--interval",
        dest="interval",
        type=float,
        default=2.0,
        help="Polling interval in seconds for --stream mode.",
    )
    parser.add_argument(
        "--ndjson",
        dest="ndjson",
        action="store_true",
        help="Emit newline-delimited JSON objects (recommended for --stream).",
    )
    return parser.parse_args()


def _filtered_nodes(iface: Any, exclude_self: bool) -> Dict[Any, Any]:
    """Return nodes, optionally excluding local node."""
    nodes = dict(iface.nodes or {})
    if not exclude_self:
        return nodes

    my_num = getattr(getattr(iface, "localNode", None), "nodeNum", None)
    if my_num is None:
        return nodes

    # Keys may be int/str depending on library version.
    keys_to_remove = {my_num, str(my_num)}
    return {k: v for k, v in nodes.items() if k not in keys_to_remove}


def _print_snapshot(iface: Any, exclude_self: bool, ndjson: bool) -> None:
    nodes = _filtered_nodes(iface, exclude_self=exclude_self)

    if ndjson:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "nodes": nodes,
        }
        print(json.dumps(payload, separators=(",", ":")), flush=True)
        return

    print("=== Node Table ===")
    iface.showNodes(includeSelf=not exclude_self)
    print("\n=== Node DB (JSON) ===")
    print(json.dumps(nodes, indent=2), flush=True)


def _stream_snapshots(iface: Any, exclude_self: bool, interval: float, ndjson: bool) -> None:
    """Continuously print updates only when NodeDB content changes."""
    last_sig: Optional[str] = None

    while True:
        nodes = _filtered_nodes(iface, exclude_self=exclude_self)
        sig = json.dumps(nodes, sort_keys=True, default=str)

        if sig != last_sig:
            if ndjson:
                payload = {
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "nodes": nodes,
                }
                print(json.dumps(payload, separators=(",", ":")), flush=True)
            else:
                print("\n=== Node DB Update ===")
                print(datetime.now(timezone.utc).isoformat())
                print(json.dumps(nodes, indent=2), flush=True)
            last_sig = sig

        time.sleep(max(0.1, interval))


def main() -> int:
    """Entry point."""
    args = parse_args()
    dev_path: Optional[str] = args.port

    try:
        with meshtastic.serial_interface.SerialInterface(
            devPath=dev_path,
            timeout=args.timeout,
        ) as iface:
            if args.stream:
                _stream_snapshots(
                    iface=iface,
                    exclude_self=args.exclude_self,
                    interval=args.interval,
                    ndjson=args.ndjson,
                )
            else:
                _print_snapshot(
                    iface=iface,
                    exclude_self=args.exclude_self,
                    ndjson=args.ndjson,
                )
            return 0

    except KeyboardInterrupt:
        print("\nStopped.", file=sys.stderr)
        return 130
    except MeshInterface.MeshInterfaceError as ex:
        print(f"Meshtastic error: {ex}", file=sys.stderr)
        return 2
    except Exception as ex:  # pylint: disable=broad-except
        print(f"Unexpected error: {ex}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())