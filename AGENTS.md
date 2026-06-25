# UAS Comm Lab - 학습 컨텍스트

## 프로젝트 목적

이 저장소는 무인기, 지상국, 중계기, 탑재 컴퓨터, 운항관리 서버, 영상 서비스, 로그 DB 사이의 통신 구조와 데이터 흐름을 이해하기 위한 MVP입니다.

목적은 실제 공격/방어 실습이 아니라 DAH 대회 준비를 위한 학습과 시뮬레이션입니다.


## 1. MAVLink 프로토콜 기초

### 패킷 구조

```text
STX | LEN | SEQ | SYS_ID | COMP_ID | MSG_ID | PAYLOAD | CHECKSUM
```

### 핵심 메시지 타입

| 메시지 | 설명 |
|---|---|
| HEARTBEAT | 1초마다 보내는 생존 신호 |
| SYS_STATUS | 배터리/연료 상태 |
| GLOBAL_POSITION_INT | GPS 위도, 경도, 고도, 속도 |
| COMMAND_LONG | LAND, RTL, TAKEOFF 같은 명령 |

### 주요 개념

- `SYS_ID`: 드론 고유 번호. 예: 송골매 = 1.
- `SEQ`: 패킷 순서 번호. 패킷마다 1씩 증가합니다.
- `UDP 14550`: MAVLink 표준 포트입니다.
- `udpout`: 패킷 전송 방향입니다.
- `udpin`: 패킷 수신 방향입니다.

## 2. UAS 전체 통신 구조

```text
[UAV-SITL]
    |
    | UDP MAVLink 텔레메트리
    v
[MAVLink Router]  <- 1:N 분배를 담당하는 핵심 중계기
    |
    +--> [GCS Simulator] 지상국, 명령 송수신
    +--> [Companion Computer] 탑재 컴퓨터, 임무 처리
    +--> [Telemetry Collector] 텔레메트리 로그 수집
             |
             v
         [Log DB] PostgreSQL

[Companion Computer]
    |
    | HTTP REST
    v
[UTM Server] 비행 허가, 충돌 방지

[UAV-SITL]
    |
    | RTSP
    v
[Payload Video] EO/IR 카메라 영상 서비스

전체 상태 -> [Dashboard] 웹 시각화
```

### 네트워크 분리

팀원 레포 기준 구조:

- `gcs_net`: GCS <-> Router
- `uav_net`: UAV <-> Router <-> Companion <-> Collector
- `ops_net`: UTM <-> Dashboard <-> Log DB

## 3. 실제 UAV 기반 설계: 송골매

| 항목 | 내용 |
|---|---|
| 제조사 | 한국항공우주산업, KAI |
| 운용 | 대한민국 육군 사단급 전술 정찰 |
| 형태 | 고정익, 가솔린 엔진 |
| 고도 | 3,000 ~ 4,500 m |
| 항속거리 | 100 km |
| 탑재 | EO 광학 카메라 + IR 열화상 카메라 |
| 역할 | ISR, 정보/감시/정찰 |

### 비조 UAV

- 제조사: LIG D&A, DAH 대회 주최사.
- 보고서에서 비조 UAV를 언급하면 대회 맥락과 연결하기 좋습니다.

## 4. 실제 사례

### 북한 드론 영공 침범, 2022-12-26

- 드론 5대가 서울 및 수도권에 침범했습니다.
- F-15K와 KA-1이 출격했지만 격추에 실패했습니다.
- 민항기 운항이 중단/지연되었습니다.
- 취약점: 소형 드론은 레이더 탐지가 어렵습니다.

### 이란 RQ-170 Sentinel 탈취, 2011

- 미군 스텔스 정찰 드론 사례입니다.
- GPS 스푸핑을 통해 이란 영토에 강제 착륙한 것으로 알려져 있습니다.
- 드론이 가짜 GPS 신호를 정상 신호로 인식한 사례로 볼 수 있습니다.

### 러시아-우크라이나 GPS 재밍/스푸핑

- 흑해 인근에서 GPS 교란이 지속적으로 발생했습니다.
- 민항기에도 영향이 있었습니다.
- Shahed-136 드론이 일방향 공격 임무에 활용되었습니다.

## 5. MAVLink 보안 취약점

### 보안 요구사항 7가지

1. 기밀성
2. 무결성
3. 가용성
4. 인증
5. 부인 방지
6. 권한 부여
7. 프라이버시

### 공격 유형

| 구분 | 공격 |
|---|---|
| 기밀성 | 도청, 신원 위장, 트래픽 분석 |
| 무결성 | MITM, Replay, Message Modification |
| 가용성 | Jamming, DoS, Flooding |
| 진정성 | Data Fabrication, GCS Spoofing |

### DAH 2026 시나리오 프레이밍

1. 도청으로 `SYS_ID`, `SEQ`, GPS, 연료 정보를 파악합니다.
2. GCS 스푸핑으로 지상국을 위장합니다. 예: `SYS_ID=99`.
3. `COMMAND_LONG` 주입으로 `LAND` 명령을 전송합니다.
4. UAV 강제 착륙으로 임무를 중단시킵니다.

### 방어 방법

- MAVLink 2.0 패킷 서명, SHA-256 기반.
- AES 대칭키 암호화.
- ECC 기반 인증.
- IDS 탐지 방식: 규칙 기반, 서명 기반, 이상 탐지, 하이브리드.

## 6. 핵심 용어

| 용어 | 설명 |
|---|---|
| UAV | Unmanned Aerial Vehicle, 무인항공기 |
| UGV | Unmanned Ground Vehicle, 무인지상차량 |
| GCS | Ground Control Station/System, 지상통제체계 |
| MAVLink | 드론과 GCS 사이의 경량 통신 프로토콜 |
| SITL | Software In The Loop, 소프트웨어 기반 드론 시뮬레이션 |
| Companion Computer | 드론 탑재 컴퓨터, 임무 처리 컴퓨터 |
| UTM | UAS Traffic Management, 무인항공 교통관리 |
| ISR | Intelligence, Surveillance, Reconnaissance, 정보/감시/정찰 |
| HEARTBEAT | MAVLink 생존 신호, 보통 1초 주기 |
| SEQ | 패킷 순서 번호 |
| SYS_ID | 드론 시스템 식별자 |
| ATCIS | 육군전술지휘정보체계 |
| ANASIS-II | 한국군 군사전용위성 |
| tc/netem | 위성망 지연 모사 도구. 예: delay 600ms, loss 2% |
| pymavlink | Python MAVLink 라이브러리 |
| BVLOS | Beyond Visual Line of Sight, 가시권 밖 비행 |
| FIMS | Flight Information Management System, 비행정보관리시스템 |

## 7. 참고 자료

- Empirical Analysis of MAVLink Protocol Vulnerability
- MAVLink in a Nutshell
- Unmanned Aircraft System Traffic Management ConOps
- CNPC Waveform Trade Studies
- ANASIS-II 위성망 구조
- 한국 UTM 구조: FIMS, USS, BVLOS
- DAH 2026 예선 안내서

## 8. 기술 스택

- 언어: Python
- 통신: pymavlink, UDP
- 서버: Flask, FastAPI
- 데이터베이스: PostgreSQL
- 컨테이너: Docker, docker-compose
- 네트워크: bridge network, 고정 IP

## 9. Docker 네트워크 예시

DAH 실습형 네트워크:

| 서비스 | IP | 역할 |
|---|---:|---|
| `dah-uav` | `172.20.0.10` | UAV 시뮬레이터 |
| `dah-recon` | `172.20.0.40` | 정찰 에이전트 |
| `dah-executor` | `172.20.0.50` | 실행/공격 에이전트 |
| `dah-defense` | `172.20.0.60` | 방어 에이전트 |
| `dah-dashboard` | `172.20.0.70` | 대시보드, 예정 |

서브넷:

```text
172.20.0.0/24
```

## 10. 구현 목표

- `uav-sitl`: MAVLink 텔레메트리 생성.
- `mavlink-router`: GCS, 탑재 컴퓨터, 수집기로 메시지 중계.
- `companion`: HTTP로 UTM 서버에 상태 보고.
- `gcs-simulator`: 지상국 동작 시뮬레이션.
- `utm-server`: PostgreSQL 기반 운항관리 서버.
- `payload-video`: FastAPI 기반 모의 탑재체 영상 서비스.
- `telemetry-collector`: 텔레메트리 로그 수집.
- `log-db`: PostgreSQL 데이터베이스.
- `dashboard`: 웹 시각화.

## 11. Claude Code에서 옮긴 컨텍스트

이 내용은 이전 Claude Code 학습 및 실습 메모에서 옮긴 것입니다.

이전에 언급된 자료:

- PDF 파일, 수신했지만 파싱 실패:
  - `Empirical Analysis of MAVLink Protocol Vulnerability.pdf`
  - `MAVLink in a Nutshell.pdf`
  - `Unmanned Aircraft System Traffic Management ConOps.pdf`
  - `CNPC Waveform Trade Studies.pdf`
  - `DAH 예선_안내서.pdf`
  - `OTKCRK230286.pdf`, 415페이지
- 읽기 성공한 이미지:
  - ANASIS-II 위성망 구조도
  - FIMS, USS, BVLOS가 포함된 한국 UTM 구조도
- 직접 붙여넣은 논문 텍스트:
  - MAVLink 보안 요구사항 및 위협 정리
  - 기밀성, 무결성, 가용성, 인증, 부인 방지, 권한 부여, 프라이버시
  - 공격 유형 분류표
  - 하드웨어/소프트웨어 보안 솔루션
  - IDS 탐지 방식: 규칙, 서명, 이상, 하이브리드
  - 블록체인 기반 보안 솔루션
  - DAH 2026 보고서 연결 포인트

## 저장소 이름 컨텍스트

- 레포 이름: `unmanned-systems-uav-ugv`
- 표시 제목: `Unmanned Systems (UAV/UGV)`
- 한국어 용어: `무인체계`
- GitHub 설명 추천:

```text
UAV/UGV unmanned systems project for DAH competition preparation.
```
