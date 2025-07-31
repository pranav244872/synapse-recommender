FROM python:3.12-slim

RUN apt update && apt install -y \
    curl git unzip ripgrep fd-find build-essential python3-dev \
    && apt clean

RUN curl -L -o nvim-linux64.tar.gz https://github.com/neovim/neovim/releases/download/v0.11.2/nvim-linux-x86_64.tar.gz \
    && tar xzf nvim-linux64.tar.gz \
    && mv nvim-linux-x86_64 /opt/nvim \
    && ln -s /opt/nvim/bin/nvim /usr/local/bin/nvim \
    && rm nvim-linux64.tar.gz

RUN adduser --disabled-password --gecos '' devuser && \
    chown -R devuser:devuser /home/devuser

USER devuser
WORKDIR /home/devuser/app

USER root
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY ./app /home/devuser/app

USER devuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
