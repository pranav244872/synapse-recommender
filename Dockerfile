FROM python:3.12-slim

# Create a non-root user with UID 1000 (matches host UID)
RUN useradd -m -u 1000 devuser

# Switch to root for installing packages
USER root

# Install developer tools and system dependencies
RUN apt-get update && \
    apt-get install -y \
        curl \
        git \
        unzip \
        ripgrep \
        fd-find \
        build-essential \
        python3-dev \
        && apt-get clean && rm -rf /var/lib/apt/lists/*

# Symlink `fd` (for fd-find)
RUN ln -s $(which fdfind) /usr/local/bin/fd || true

# Optional: Install Neovim (latest prebuilt binary)
RUN curl -L -o nvim-linux64.tar.gz https://github.com/neovim/neovim/releases/download/v0.11.2/nvim-linux-x86_64.tar.gz && \
    tar xzf nvim-linux64.tar.gz && \
    mv nvim-linux-x86_64 /opt/nvim && \
    ln -s /opt/nvim/bin/nvim /usr/local/bin/nvim && \
    rm nvim-linux64.tar.gz

# Install Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy app source code
COPY ./app /home/devuser/app

# Set proper ownership
RUN chown -R devuser:devuser /home/devuser/app

# Switch to dev user
USER devuser

# Set working directory
WORKDIR /home/devuser/app

# Use empty ENTRYPOINT (optional, avoids inherited entrypoint behavior)
ENTRYPOINT []

# Default command: FastAPI with reload (can change to bash if interactive dev preferred)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
