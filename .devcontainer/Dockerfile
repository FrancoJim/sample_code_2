FROM python:3.14-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# ── System packages ──────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        git make curl wget jq unzip vim less \
        ca-certificates gnupg \
        bash-completion \
    && rm -rf /var/lib/apt/lists/*

# ── Docker CLI (for docker socket access / OrbStack) ─────────────────────────
RUN install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg \
       | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
    && . /etc/os-release \
    && echo \
       "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
       https://download.docker.com/linux/debian ${VERSION_CODENAME} stable" \
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

# ── PS1 & shell config ────────────────────────────────────────────────────────
COPY scripts/devcontainer-ps1.sh /etc/profile.d/devcontainer-ps1.sh
RUN chmod +x /etc/profile.d/devcontainer-ps1.sh \
    && echo 'source /etc/profile.d/devcontainer-ps1.sh' >> /root/.bashrc \
    && echo 'source /etc/bash_completion' >> /root/.bashrc

WORKDIR /workspace
