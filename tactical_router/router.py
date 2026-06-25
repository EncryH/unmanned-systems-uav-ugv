import json
import os
import select
import socket
import time

UAV_LISTEN_PORT = int(os.getenv("UAV_LISTEN_PORT", "14560"))
UGV_LISTEN_PORT = int(os.getenv("UGV_LISTEN_PORT", "14660"))

MISSION_HOST = os.getenv("MISSION_HOST", "mission-control")
MISSION_PORT = int(os.getenv("MISSION_PORT", "14540"))
COLLECTOR_HOST = os.getenv("COLLECTOR_HOST", "telemetry-collector")
COLLECTOR_PORT = int(os.getenv("COLLECTOR_PORT", "14541"))


def bind_udp(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", port))
    return sock


def forward(sock, payload, target):
    sock.sendto(json.dumps(payload).encode("utf-8"), target)


def main():
    uav_sock = bind_udp(UAV_LISTEN_PORT)
    ugv_sock = bind_udp(UGV_LISTEN_PORT)
    out_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    inputs = [uav_sock, ugv_sock]

    print("[ROUTER] TICN 전술 라우터 시작")
    print(f"[ROUTER] UAV UDP {UAV_LISTEN_PORT} / UGV UDP {UGV_LISTEN_PORT}")
    print(f"[ROUTER] fan-out -> {MISSION_HOST}:{MISSION_PORT}, {COLLECTOR_HOST}:{COLLECTOR_PORT}")

    while True:
        readable, _, _ = select.select(inputs, [], [], 1)
        for sock in readable:
            data, _ = sock.recvfrom(8192)
            try:
                payload = json.loads(data.decode("utf-8"))
            except json.JSONDecodeError:
                print("[ROUTER] invalid telemetry dropped")
                continue

            payload["router_received_at"] = time.time()
            payload["router"] = "dah-tactical-router"
            payload["network"] = "TICN"

            forward(out_sock, payload, (MISSION_HOST, MISSION_PORT))
            forward(out_sock, payload, (COLLECTOR_HOST, COLLECTOR_PORT))

            print(
                f"[ROUTER] {payload.get('platform_id')} "
                f"{payload.get('message_type')} seq={payload.get('seq')} fan-out=2"
            )


if __name__ == "__main__":
    main()
