# FROM mcr.microsoft.com/vscode/devcontainers/python:3.11
FROM python:3.11-slim

# Avoid warnings by switching to noninteractive
ENV DEBIAN_FRONTEND=noninteractive
ENV POETRY_HOME="/opt/poetry"
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_VERSION=1.7.1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    PATH="${POETRY_HOME}/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl build-essential libpq-dev openssh-client \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir wheel \
    && curl -sSL https://install.python-poetry.org | python3 -


# Add Poetry to PATH
ENV PATH="${POETRY_HOME}/bin:$PATH"

# Create a non-root user
RUN useradd -ms /bin/bash vscode \
    && mkdir -p /workspace/MediCore \
    && chown -R vscode:vscode /workspace/MediCore

# Set working directory
WORKDIR /workspace/MediCore


COPY pyproject.toml poetry.lock* ./
RUN poetry install --no-root --with test,docs

USER vscode