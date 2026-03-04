#!/usr/bin/env python3
# SDN RouteInstall sender via Meshtastic serial interface

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


def pack_hop_path(hops):
    """
    Pack up to 8 one-byte hops into fixed64.
    byte0=first hop, byte1=second hop, ...
    """
    if len(hops) == 0:
        raise ValueError("Path cannot be empty")
    if len(hops) > 8:
        raise ValueError("Maximum 8 hops allowed")

    hop_path = 0
    for i, hop in enumerate(hops):
        if hop < 0 or hop > 0xFF:
            raise ValueError(f"Hop {i} value {hop} out of range (0..255)")
        hop_path |= (hop << (i * 8))
    return hop_path


def unpack_hop_path(hop_path):
    """Unpack fixed64 to hop list, stopping at first zero byte."""
    hops = []
    for i in range(8):
        hop = (hop_path >> (i * 8)) & 0xFF
        if hop == 0:
            break
        hops.append(hop)
    return hops


def parse_node_id(value: str) -> int:
    """Accept hex or decimal (example: 0x14 or 20)."""
    return int(value, 0)


def parse_path(value: str):
    """Parse comma-separated path (example: 0x12,0x13,0x14)."""
    hops = [int(x.strip(), 0) for x in value.split(",") if x.strip()]
    if not hops:
        raise ValueError("Path cannot be empty")
    for h in hops:
        if h < 0 or h > 0xFF:
            raise ValueError(f"Hop out of range (0..255): {h}")
    return hops


def send_route_install_serial(
    port: str,
    destination: int,
    path,
    install_id: int = 1,
    start_node: int = None,
    channel_index: int = 0,
    want_ack: bool = False,
):
    if start_node is None:
        start_node = path[0]

    route_install = sdn_pb2.SDNRouteInstall()
    route_install.destination = destination
    route_install.hop_path = pack_hop_path(path)
    route_install.install_id = install_id & 0xFF

    sdn_msg = sdn_pb2.SDN()
    sdn_msg.route_install.CopyFrom(route_install)
    payload = sdn_msg.SerializeToString()

    iface = SerialInterface(devPath=port)
    try:
        # Small delay gives interface time to settle on some systems
        time.sleep(0.5)

        iface.sendData(
            data=payload,
            destinationId=f"!{start_node:08x}",
            portNum=portnums_pb2.PortNum.SDN_APP,
            wantAck=want_ack,
            channelIndex=channel_index,
        )

        print("✓ SDN RouteInstall sent via serial")
        print(f"  serial_port = {port}")
        print(f"  start_node  = !{start_node:08x}")
        print(f"  destination = 0x{destination:08x}")
        print(f"  install_id  = {route_install.install_id}")
        print(f"  path        = {' -> '.join([f'0x{x:02x}' for x in path])}")
        print(f"  hop_path    = 0x{route_install.hop_path:016x}")
        print(f"  channel     = {channel_index}")
        print(f"  wantAck     = {want_ack}")
    finally:
        iface.close()


def test_packing():
    print("Testing hop_path packing/unpacking...")
    tests = [
        [0x12, 0x34, 0x56],
        [0xAB],
        [0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88],
    ]
    for idx, path in enumerate(tests, start=1):
        packed = pack_hop_path(path)
        unpacked = unpack_hop_path(packed)
        assert unpacked == path, f"Test {idx} failed: {unpacked} != {path}"
        print(f"  Test {idx}: OK  path={path} packed=0x{packed:016x}")
    print("✓ All packing tests passed")


def main():
    parser = argparse.ArgumentParser(description="Send SDN RouteInstall via serial")
    sub = parser.add_subparsers(dest="cmd")

    p_send = sub.add_parser("send", help="Send RouteInstall over serial")
    p_send.add_argument("--port", required=True, help="Serial device (example: /dev/ttyUSB0)")
    p_send.add_argument("--destination", required=True, help="Destination node id (hex/dec)")
    p_send.add_argument("--path", required=True, help="Comma-separated hops (example: 0x12,0x13,0x14)")
    p_send.add_argument("--install-id", type=int, default=1, help="Install ID (0..255)")
    p_send.add_argument("--start-node", help="Start node id (hex/dec). Default: first hop in path")
    p_send.add_argument("--channel-index", type=int, default=0, help="Meshtastic channel index")
    p_send.add_argument("--want-ack", action="store_true", help="Request ACK")

    sub.add_parser("pack", help="Run pack/unpack self-test")

    args = parser.parse_args()

    if args.cmd == "pack":
        test_packing()
        return

    if args.cmd == "send":
        destination = parse_node_id(args.destination)
        path = parse_path(args.path)
        start_node = parse_node_id(args.start_node) if args.start_node else None

        send_route_install_serial(
            port=args.port,
            destination=destination,
            path=path,
            install_id=args.install_id,
            start_node=start_node,
            channel_index=args.channel_index,
            want_ack=args.want_ack,
        )
        return

    parser.print_help()


if __name__ == "__main__":
    main()