import threading
import json
import os
import socket
import time
from pymavlink import mavutil

# ─────────────────────────────────────────
# 송골매 UAV 기본 설정값
# ─────────────────────────────────────────
UAV_HOST = '172.20.0.255'   # 텔레메트리 전송 대상 (recon 컨테이너 IP)
UAV_PORT = 14550            # 텔레메트리 전송 포트
ROUTER_HOST = os.getenv('ROUTER_HOST', 'dah-tactical-router')
ROUTER_PORT = int(os.getenv('ROUTER_PORT', '14560'))
CMD_PORT = 14551            # 명령 수신 포트 (executor가 여기로 공격)
SYS_ID   = 1               # 송골매 고유 번호
PLATFORM_ID = 'UAV-001'
MISSION  = 'RECON'         # 현재 임무
ALTITUDE = 3500            # 초기 고도 (m)
FUEL     = 78              # 연료 잔량 (%)
SPEED    = 150             # 속도 (km/h)
GPS_LAT  = 37.9            # 위도 (경기 북부 가상 좌표)
GPS_LON  = 126.8           # 경도
EO_STATUS = 'ACTIVE'       # 광학 카메라 상태
IR_STATUS = 'ACTIVE'       # 열화상 카메라 상태

# 드론 현재 상태 (공격 받으면 landed=True 로 바뀜)
status = {'landed': False}


def send_router_telemetry(sock, seq, alt):
    """
    기본 통신 파이프라인용 JSON 텔레메트리.
    UAV -> Tactical Router -> Mission Control / Collector 로 흐른다.
    """
    payload = {
        'platform_id': PLATFORM_ID,
        'platform_type': 'UAV',
        'message_type': 'telemetry',
        'mission': MISSION,
        'seq': seq,
        'lat': GPS_LAT,
        'lon': GPS_LON,
        'alt': alt,
        'speed': SPEED,
        'fuel': FUEL,
        'eo_status': EO_STATUS,
        'ir_status': IR_STATUS,
        'link': 'TICN/SATCOM',
        'status': 'LANDED' if status['landed'] else 'ACTIVE',
        'timestamp': time.time(),
    }
    sock.sendto(json.dumps(payload).encode('utf-8'), (ROUTER_HOST, ROUTER_PORT))


def listen_for_commands():
    """
    별도 스레드에서 실행
    executor.py가 보내는 MAVLink 명령을 14551 포트에서 수신
    """
    # udpin = 외부에서 들어오는 패킷을 받는 방향
    cmd_conn = mavutil.mavlink_connection(f'udpin:0.0.0.0:{CMD_PORT}')
    print(f"[송골매] 명령 수신 대기 중 → 포트 {CMD_PORT}")

    while True:
        # COMMAND_LONG 타입 패킷만 필터링해서 수신
        msg = cmd_conn.recv_match(type='COMMAND_LONG', blocking=True)
        if msg is None:
            continue

        src = msg.get_srcSystem()  # 명령을 보낸 SYS_ID
        cmd = msg.command          # 명령 종류 (LAND, RTL 등)

        # MAV_CMD_NAV_LAND = 착륙 명령
        if cmd == mavutil.mavlink.MAV_CMD_NAV_LAND:
            print(f"[송골매] LAND 명령 수신 SYS_ID={src}")
            status['landed'] = True
        # MAV_CMD_NAV_RETURN_TO_LAUNCH = RTB (Return to Base)
        elif cmd == mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH:
            print(f"[송골매] RTB 명령 수신 SYS_ID={src} → 귀환 착륙 실행")
            status['landed'] = True


def main():
    # 명령 수신을 별도 스레드로 실행 (메인 루프와 동시에 돌아감)
    # daemon=True → 메인 프로세스 종료 시 같이 종료
    t = threading.Thread(target=listen_for_commands, daemon=True)
    t.start()

    # udpout = dah-net 브로드캐스트로 MAVLink 전송 (recon/CC 수신)
    mav = mavutil.mavlink_connection(
        f'udpout:{UAV_HOST}:{UAV_PORT}',
        source_system=SYS_ID
    )
    mav.port.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    router_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    seq = 1          # 패킷 순서 번호 (recon이 이걸 보고 SEQ 파악)
    alt = ALTITUDE   # 현재 고도 (착륙 명령 받으면 점점 감소)

    while True:

        if status['landed']:
            # ── 공격 성공: 고도를 100m씩 낮춰서 착륙 시뮬레이션
            alt = max(0, alt - 100)
            print(f"[송골매] 착륙 중... 현재 고도={alt}m")
            if alt == 0:
                print(f"[송골매] 착륙 완료. 임무 중단.")
                break  # 완전 착륙 후 루프 종료
        else:
            # ── 정상 비행 중: 상태 로그 출력
            print(f"[송골매] HEARTBEAT | SEQ={seq}   | 임무={MISSION}")
            print(f"[송골매] SYS_STATUS | 연료={FUEL}% | SEQ={seq+1}")
            print(f"[송골매] POSITION   | 위도={GPS_LAT} 경도={GPS_LON} 고도={alt}m | SEQ={seq+2}")
            print(f"[송골매] ISR        | EO={EO_STATUS} | IR={IR_STATUS} | 정찰 데이터 수집 중")
            print(f"[송골매] ROUTER     | {ROUTER_HOST}:{ROUTER_PORT} 로 전술 텔레메트리 송신")
            print("-" * 50)

        # ── HEARTBEAT 패킷 전송 (1초마다 "나 살아있음" 신호)
        mav.mav.heartbeat_send(
            type=mavutil.mavlink.MAV_TYPE_FIXED_WING,          # 고정익 기체
            autopilot=mavutil.mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA,
            base_mode=mavutil.mavlink.MAV_MODE_AUTO_ARMED,     # 자동 비행 + 무장 상태
            custom_mode=0,
            system_status=mavutil.mavlink.MAV_STATE_ACTIVE
        )

        # ── SYS_STATUS 패킷 전송 (연료/배터리 상태)
        mav.mav.sys_status_send(
            onboard_control_sensors_present=0,
            onboard_control_sensors_enabled=0,
            onboard_control_sensors_health=0,
            load=300,
            voltage_battery=12000,    # 배터리 전압 (mV)
            current_battery=1500,     # 전류 (mA)
            battery_remaining=FUEL,   # 연료 잔량 % ← recon이 이 값 추출
            drop_rate_comm=0,
            errors_comm=0,
            errors_count1=0, errors_count2=0,
            errors_count3=0, errors_count4=0
        )

        # ── GLOBAL_POSITION_INT 패킷 전송 (GPS 좌표 + 고도 + 속도)
        mav.mav.global_position_int_send(
            time_boot_ms=seq * 1000,
            lat=int(GPS_LAT * 1e7),       # 위도: 정수형으로 변환 (×1e7)
            lon=int(GPS_LON * 1e7),       # 경도: 정수형으로 변환 (×1e7)
            alt=int(alt * 1000),          # 고도: mm 단위로 변환 (×1000)
            relative_alt=int(alt * 1000),
            vx=int(SPEED * 100 / 3.6),   # 속도: cm/s 단위로 변환
            vy=0, vz=0, hdg=0
        )

        send_router_telemetry(router_sock, seq, alt)

        seq += 3   # 패킷 3개 보냈으니 SEQ 3 증가
        time.sleep(1)  # 1초 대기 후 반복


if __name__ == '__main__':
    main()
