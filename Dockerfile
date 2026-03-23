FROM python:3.12-slim-bookworm

WORKDIR /app

RUN apt-get update -qq && \
    apt-get install -y openssh-client -qq && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agent.py .

CMD ["python", "agent.py"]