FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# ── System packages ──────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3.10 python3.10-venv python3-pip \
        git make curl wget jq unzip vim \
        ca-certificates gnupg lsb-release \
        bash-completion \
    && ln -sf /usr/bin/python3.10 /usr/local/bin/python \
    && ln -sf /usr/bin/python3.10 /usr/local/bin/python3 \
    && ln -sf /usr/bin/pip3      /usr/local/bin/pip \
    && rm -rf /var/lib/apt/lists/*

# ── Docker CLI (for docker socket access / OrbStack) ─────────────────────────
RUN install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
       | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
    && echo \
       "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
       https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
       > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends docker-ce-cli docker-compose-plugin \
    && rm -rf /var/lib/apt/lists/*

# ── AWS CLI v2 ────────────────────────────────────────────────────────────────
RUN ARCH=$(uname -m) \
    && curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-${ARCH}.zip" \
       -o /tmp/awscliv2.zip \
    && unzip -q /tmp/awscliv2.zip -d /tmp \
    && /tmp/aws/install \
    && rm -rf /tmp/awscliv2.zip /tmp/aws

# ── Python tooling (baked in so they're available before post-create runs) ───
RUN pip3 install --no-cache-dir \
        poetry \
        ruff \
        black \
        isort \
        pre-commit

# ── PS1 & shell config ────────────────────────────────────────────────────────
COPY scripts/devcontainer-ps1.sh /etc/profile.d/devcontainer-ps1.sh
RUN chmod +x /etc/profile.d/devcontainer-ps1.sh \
    && echo 'source /etc/profile.d/devcontainer-ps1.sh' >> /root/.bashrc \
    && echo 'source /etc/bash_completion' >> /root/.bashrc

WORKDIR /workspace
