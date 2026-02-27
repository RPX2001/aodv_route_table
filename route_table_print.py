#!/usr/bin/env python3
import argparse
import time
from pubsub import pub
from meshtastic.serial_interface import SerialInterface
import aodv_pb2

AODV_ROUTING_APP_PORTNUM = 75

class RouteTableClient:
    def __init__(self):
        self.request_id = int(time.time())
        self.route_table = None

    def on_receive(self, packet, interface):
        try:
            decoded = packet.get("decoded", {})
            portnum = decoded.get("portnum")
            if portnum not in ("AODV_ROUTING_APP", AODV_ROUTING_APP_PORTNUM):
                return

            payload = decoded.get("payload")
            if not payload:
                return

            msg = aodv_pb2.AODV()
            msg.ParseFromString(payload)

            # Requires proto support
            if "rt_response" in msg.DESCRIPTOR.fields_by_name and msg.HasField("rt_response"):
                rt = msg.rt_response
                if rt.request_id == self.request_id:
                    self.route_table = rt.routes
        except Exception as e:
            print(f"[recv] parse error: {e}")

    def print_routes(self):
        if self.route_table is None:
            print("No route table received.")
            return

        print("\nAODV ROUTE TABLE")
        print(f"{'Destination':<15} {'NextHop':<15} {'Hops':<6} {'Seq':<8} {'Lifetime':<10} {'Valid':<6}")
        print("-" * 70)
        for r in self.route_table:
            valid = "Y" if getattr(r, "valid", False) else "N"
            print(
                f"!{r.destination:08x}      "
                f"!{r.next_hop:08x}         "
                f"{r.hop_count:<6} "
                f"{r.destination_seq_num:<8}  "
                f"{r.lifetime:<10} "
                f"{valid:<6}"
            )

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-p", "--port", required=True, help="Serial device, e.g. /dev/ttyACM0")
    ap.add_argument("-t", "--timeout", type=int, default=10)
    args = ap.parse_args()

    # Proto capability check
    test_msg = aodv_pb2.AODV()
    if "rt_request" not in test_msg.DESCRIPTOR.fields_by_name:
        print("Error: aodv.proto/aodv_pb2.py has no rt_request field.")
        print("Add RouteTableRequest/RouteTableResponse to aodv.proto and regenerate.")
        return

    client = RouteTableClient()
    pub.subscribe(client.on_receive, "meshtastic.receive")

    iface = SerialInterface(devPath=args.port)
    try:
        node = iface.getMyNodeInfo()
        node_num = node.get("num")
        print(f"Connected: !{node_num:08x} on {args.port}")

        msg = aodv_pb2.AODV()
        msg.rt_request.request_id = client.request_id
        payload = msg.SerializeToString()

        iface.sendData(
            data=payload,
            destinationId=f"!{node_num:08x}",
            portNum=AODV_ROUTING_APP_PORTNUM,
            wantAck=False,
            channelIndex=0,
        )

        start = time.time()
        while time.time() - start < args.timeout:
            if client.route_table is not None:
                break
            time.sleep(0.2)

        client.print_routes()
    finally:
        iface.close()

if __name__ == "__main__":
    main()
