# 베이스 이미지: Python 3.11 (가벼운 버전)
FROM python:3.11-slim

# 컨테이너 안 작업 폴더 설정
WORKDIR /app

# requirements.txt 먼저 복사 후 패키지 설치
COPY requirements.txt .
RUN pip install -r requirements.txt

# recon.py, executor.py 둘 다 복사
# context가 DAH/ 루트이므로 경로 포함해서 지정
COPY attack_agent/recon.py .
COPY attack_agent/executor.py .

# 기본 실행은 recon.py
# executor는 docker-compose에서 command로 오버라이드
CMD ["python", "recon.py"]