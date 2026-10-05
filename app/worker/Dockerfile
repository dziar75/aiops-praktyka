# syntax=docker/dockerfile:1

FROM python:3.12-slim AS build
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build
COPY requirements.txt .
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install -r requirements.txt

FROM python:3.12-slim
ARG APP_VERSION=0.0.0-dev
ARG APP_VARIANT=stable
ENV APP_VERSION=${APP_VERSION} \
    APP_VARIANT=${APP_VARIANT} \
    PATH="/opt/venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
LABEL org.opencontainers.image.title="kantyna-worker" \
      org.opencontainers.image.version="${APP_VERSION}"

RUN groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app

COPY --from=build /opt/venv /opt/venv
WORKDIR /srv
COPY app ./app

USER 10001:10001
EXPOSE 9000
CMD ["python", "-m", "app.main"]
