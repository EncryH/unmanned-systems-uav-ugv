import time
from pymavlink import mavutil

# ─────────────────────────────────────────
# 방어 대상 설정
# ─────────────────────────────────────────
UAV_HOST = '172.20.0.10'   # UAV 컨테이너 IP
UAV_PORT = 14551            # UAV 명령 수신 포트
GCS_SYS_ID = 255            # 정상 GCS SYS_ID (방어 에이전트가 GCS인 척)


def send_rtl(mav):
    """
    공격 탐지 시 UAV에 RTL(Return To Launch) 명령 전송
    executor의 LAND 명령보다 먼저 도달하면 UAV 보호 가능
    """
    mav.mav.command_long_send(
        target_system=1,                                        # 송골매 SYS_ID
        target_component=1,
        command=mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH,  # RTL 명령
        confirmation=0,
        param1=0, param2=0, param3=0, param4=0,
        param5=0, param6=0, param7=0
    )
    print(f"[RESPONDER] RTL 명령 전송 완료 → UAV {UAV_HOST}:{UAV_PORT}")


def send_safe_mode(mav):
    """
    UAV를 안전 모드로 전환
    비정상 명령 차단 후 안전한 상태 유지
    """
    mav.mav.set_mode_send(
        target_system=1,
        base_mode=mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED,  # 안전 모드
        custom_mode=0
    )
    print(f"[RESPONDER] 안전 모드 전환 완료 → UAV {UAV_HOST}:{UAV_PORT}")


def respond(threats):
    """
    detector.py가 전달한 threats 목록 기반으로 대응
    위협 종류에 따라 RTL 또는 안전 모드 선택
    """
    if not threats:
        return  # 위협 없으면 아무것도 안 함

    # 정상 GCS인 척 UAV에 연결
    mav = mavutil.mavlink_connection(
        f'udpout:{UAV_HOST}:{UAV_PORT}',
        source_system=GCS_SYS_ID
    )

    for threat in threats:
        print(f"[RESPONDER] 위협 대응 시작")
        print(f"[RESPONDER] 원인: {threat['reason']}")

        # ── LAND 명령 주입 공격 → RTL로 대응
        if 'cmd' in threat and threat['cmd'] == mavutil.mavlink.MAV_CMD_NAV_LAND:
            print(f"[RESPONDER] LAND 주입 탐지 → RTL 명령으로 대응")
            send_rtl(mav)

        # ── Replay Attack → 안전 모드로 대응
        elif threat['reason'] == 'Replay Attack 탐지 (SEQ 역전)':
            print(f"[RESPONDER] Replay Attack 탐지 → 안전 모드 전환")
            send_safe_mode(mav)

        # ── 그 외 위협 → RTL로 대응
        else:
            print(f"[RESPONDER] 알 수 없는 위협 → RTL 명령으로 대응")
            send_rtl(mav)

        time.sleep(1)  # 명령 간 간격


if __name__ == '__main__':
    # 단독 실행 시 테스트용 threat로 대응 확인
    test_threats = [
        {
            'reason' : '허용되지 않은 SYS_ID에서 COMMAND_LONG 수신',
            'src_id' : 99,
            'cmd'    : mavutil.mavlink.MAV_CMD_NAV_LAND
        }
    ]
    respond(test_threats)