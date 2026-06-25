"""
Companion Computer — UAV 탑재 컴퓨터
역할: Autopilot(FC)에서 MAVLink 수신 → JSON 변환 → Mission Control HTTP 전송
"""
import json
import os
import time
import urllib.request
from pymavlink import mavutil

MAVLINK_HOST = "0.0.0.0"
MAVLINK_PORT = int(os.getenv("MAVLINK_PORT", "14550"))
MISSION_URL  = os.getenv("MISSION_CONTROL_URL", "http://mission-control:8080")
PLATFORM_ID  = "UAV-001"

state = {}


def post_to_mission(payload):
    data = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(
        f"{MISSION_URL}/api/companion",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=1.0):
            pass
    except Exception as e:
        print(f"[CC] Mission Control 전송 실패: {e}")


def main():
    mav = mavutil.mavlink_connection(f"udpin:{MAVLINK_HOST}:{MAVLINK_PORT}")
    print(f"[CC] Companion Computer 시작")
    print(f"[CC] MAVLink 수신 → {MAVLINK_HOST}:{MAVLINK_PORT}")
    print(f"[CC] Mission Control → {MISSION_URL}/api/companion")
    print("-" * 50)

    while True:
        msg = mav.recv_match(blocking=True, timeout=5)
        if msg is None:
            continue

        msg_type = msg.get_type()
        sys_id   = msg.get_srcSystem()
        seq      = msg._header.seq

        if msg_type == "HEARTBEAT":
            state["sys_id"] = sys_id
            state["mode"]   = msg.base_mode
            print(f"[CC] HEARTBEAT   | SYS_ID={sys_id} | SEQ={seq}")

        elif msg_type == "SYS_STATUS":
            state["fuel"] = msg.battery_remaining
            print(f"[CC] SYS_STATUS  | fuel={state['fuel']}% | SEQ={seq}")

        elif msg_type == "GLOBAL_POSITION_INT":
            state["lat"]   = msg.lat / 1e7
            state["lon"]   = msg.lon / 1e7
            state["alt"]   = msg.alt / 1000
            state["speed"] = round(((msg.vx ** 2 + msg.vy ** 2) ** 0.5) / 100 * 3.6, 1)
            print(f"[CC] POSITION    | lat={state['lat']} lon={state['lon']} alt={state['alt']}m | SEQ={seq}")

            if "fuel" in state:
                payload = {
                    "platform_id":   PLATFORM_ID,
                    "platform_type": "UAV",
                    "message_type":  "telemetry",
                    "source":        "companion_computer",
                    "seq":           seq,
                    **state,
                    "timestamp": time.time(),
                }
                post_to_mission(payload)


if __name__ == "__main__":
    main()
