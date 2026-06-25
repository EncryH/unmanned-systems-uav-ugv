import time
import threading
from pymavlink import mavutil
from detector import detect
from responder import respond

# ─────────────────────────────────────────
# 방어 에이전트 설정
# ─────────────────────────────────────────
LISTEN_HOST  = '0.0.0.0'    # 모든 IP에서 오는 패킷 수신
LISTEN_PORT  = 14551         # UAV 텔레메트리 포트 감시
ALLOWED_GCS_ID = 255         # 정상 GCS SYS_ID
CHECK_INTERVAL = 2           # 탐지 주기 (초)

# monitor가 수집한 경보 저장소
alerts = []

# SEQ 역전 탐지용
last_seq = {}


def monitor():
    """
    MAVLink 패킷 실시간 감시
    이상 패킷 발견 시 alerts에 추가
    """
    mav = mavutil.mavlink_connection(f'udpin:{LISTEN_HOST}:{LISTEN_PORT}')
    print(f"[DEFENSE] 감시 시작 → 포트 {LISTEN_PORT}")

    while True:
        msg = mav.recv_match(blocking=True)
        if msg is None:
            continue

        msg_type = msg.get_type()
        src_id   = msg.get_srcSystem()
        seq      = msg._header.seq

        # ── COMMAND_LONG 패킷 감시
        if msg_type == 'COMMAND_LONG':
            cmd = msg.command
            print(f"[DEFENSE] COMMAND_LONG 감지 | SYS_ID={src_id} | 명령={cmd} | SEQ={seq}")

            # 허용되지 않은 SYS_ID → 경보
            if src_id != ALLOWED_GCS_ID:
                alerts.append({
                    'type'   : 'UNKNOWN_SRC',
                    'src_id' : src_id,
                    'cmd'    : cmd,
                    'seq'    : seq
                })
                print(f"[DEFENSE] ⚠️  비정상 출처 → SYS_ID={src_id}")

        # ── Replay Attack 탐지
        if src_id in last_seq:
            if seq <= last_seq[src_id]:
                alerts.append({
                    'type'   : 'REPLAY',
                    'src_id' : src_id,
                    'seq'    : seq
                })
                print(f"[DEFENSE] ⚠️  Replay Attack 의심 → SEQ={seq} (이전={last_seq[src_id]})")

        last_seq[src_id] = seq


def defense_loop():
    """
    주기적으로 alerts 확인
    위협 탐지 시 responder 호출
    """
    while True:
        time.sleep(CHECK_INTERVAL)

        if not alerts:
            continue

        # 쌓인 경보 전달 후 초기화
        current_alerts = alerts.copy()
        alerts.clear()

        # 탐지
        threats = detect(current_alerts)

        if threats:
            print(f"[DEFENSE] 위협 {len(threats)}건 탐지 → 대응 시작")
            respond(threats)


def main():
    print(f"[DEFENSE] 방어 에이전트 시작")
    print(f"[DEFENSE] monitor + detector + responder 통합 실행")
    print("-" * 50)

    # 감시는 별도 스레드로 실행 (논블로킹)
    t = threading.Thread(target=monitor, daemon=True)
    t.start()

    # 메인 스레드에서 탐지 + 대응 루프 실행
    defense_loop()


if __name__ == '__main__':
    main()