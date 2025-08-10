FROM python:3.12-slim

RUN apt update && apt install -y \
    curl git unzip ripgrep fd-find build-essential python3-dev \
    && apt clean

RUN adduser --disabled-password --gecos '' devuser && \
    chown -R devuser:devuser /home/devuser

USER devuser
WORKDIR /home/devuser/app

USER root
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY ./app /home/devuser/app

USER devuser

ENTRYPOINT []

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
