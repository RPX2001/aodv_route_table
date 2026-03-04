#!/usr/bin/env python3
# SDN RouteSwitch sender via Meshtastic serial interface

import argparse
import sys
import time
from pathlib import Path

from meshtastic.serial_interface import SerialInterface

# Prefer local generated protobufs in ./meshtastic
BASE_DIR = Path(__file__).resolve().parent
LOCAL_MESHTASTIC_DIR = BASE_DIR / "meshtastic"
LOCAL_NANOPB_PROTO_DIR = BASE_DIR / "nanopb-0.4.9-linux-x86" / "generator" / "proto"

for p in (LOCAL_MESHTASTIC_DIR, LOCAL_NANOPB_PROTO_DIR):
    p = str(p)
    if Path(p).exists() and p not in sys.path:
        sys.path.insert(0, p)

import sdn_pb2
import portnums_pb2


def parse_int(value: str) -> int:
    """Accept hex or decimal (example: 0x15 or 21)."""
    return int(value, 0)


def send_route_switch_serial(
    port: str,
    target_node: int,
    destination: int,
    next_hop: int,
    channel_index: int = 0,
    want_ack: bool = False,
):
    if next_hop < 0 or next_hop > 0xFF:
        raise ValueError("next_hop must be in range 0..255")

    route_cmd = sdn_pb2.SDNRouteCommand()
    route_cmd.destination = destination
    route_cmd.next_hop = next_hop

    sdn_msg = sdn_pb2.SDN()
    sdn_msg.route_command.CopyFrom(route_cmd)
    payload = sdn_msg.SerializeToString()

    iface = SerialInterface(devPath=port)
    try:
        time.sleep(0.5)  # let serial interface settle

        iface.sendData(
            data=payload,
            destinationId=f"!{target_node:08x}",
            portNum=portnums_pb2.PortNum.SDN_APP,
            wantAck=want_ack,
            channelIndex=channel_index,
        )

        print("✓ SDN RouteSwitch sent via serial")
        print(f"  serial_port = {port}")
        print(f"  target_node = !{target_node:08x}")
        print(f"  destination = 0x{destination:08x}")
        print(f"  next_hop    = 0x{next_hop:02x}")
        print(f"  channel     = {channel_index}")
        print(f"  wantAck     = {want_ack}")
    finally:
        iface.close()


def main():
    parser = argparse.ArgumentParser(description="Send SDN RouteSwitch via serial")
    parser.add_argument("--port", required=True, help="Serial device (example: /dev/ttyUSB0)")
    parser.add_argument("--target-node", required=True, help="Node that should apply switch (hex/dec)")
    parser.add_argument("--destination", required=True, help="Destination node id (hex/dec)")
    parser.add_argument("--next-hop", required=True, help="Backup next hop (hex/dec, 0..255)")
    parser.add_argument("--channel-index", type=int, default=0, help="Meshtastic channel index")
    parser.add_argument("--want-ack", action="store_true", help="Request ACK")

    args = parser.parse_args()

    send_route_switch_serial(
        port=args.port,
        target_node=parse_int(args.target_node),
        destination=parse_int(args.destination),
        next_hop=parse_int(args.next_hop),
        channel_index=args.channel_index,
        want_ack=args.want_ack,
    )


if __name__ == "__main__":
    main()