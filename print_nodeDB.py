#!/usr/bin/env python3
"""Connect to a Meshtastic device over serial and print NodeDB details."""

import argparse
import json
import sys
from typing import Optional

import meshtastic.serial_interface
from meshtastic.mesh_interface import MeshInterface


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Print Meshtastic nodes from a serial-connected device."
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
        help="Exclude local node from table output.",
    )
    return parser.parse_args()


def main() -> int:
    """Entry point."""
    args = parse_args()
    dev_path: Optional[str] = args.port

    try:
        with meshtastic.serial_interface.SerialInterface(
            devPath=dev_path,
            timeout=args.timeout,
        ) as iface:
            print("=== Node Table ===")
            iface.showNodes(includeSelf=not args.exclude_self)

            print("\n=== Node DB (JSON) ===")
            print(json.dumps(iface.nodes or {}, indent=2))
            return 0

    except MeshInterface.MeshInterfaceError as ex:
        print(f"Meshtastic error: {ex}", file=sys.stderr)
        return 2
    except Exception as ex:  # pylint: disable=broad-except
        print(f"Unexpected error: {ex}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())