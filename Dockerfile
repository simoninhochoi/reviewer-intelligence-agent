FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY . .

# 데이터 디렉토리 생성
RUN mkdir -p data/papers data/profiles data/outputs data/chroma_db

EXPOSE 8501

# Railway는 PORT 환경변수를 제공함 — config.toml은 프로젝트 .streamlit/에서 복사됨
CMD streamlit run app.py --server.port=${PORT:-8501} --server.address=0.0.0.0
