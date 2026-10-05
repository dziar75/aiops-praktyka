# syntax=docker/dockerfile:1

FROM nginxinc/nginx-unprivileged:1.27-alpine
ARG APP_VERSION=0.0.0-dev
ARG APP_VARIANT=stable
ENV APP_VERSION=${APP_VERSION} \
    APP_VARIANT=${APP_VARIANT} \
    ORDERS_API_UPSTREAM=orders-api:8000 \
    NGINX_ENVSUBST_FILTER=^ORDERS_API_ \
    NGINX_ENVSUBST_OUTPUT_DIR=/tmp
LABEL org.opencontainers.image.title="kantyna-web" \
      org.opencontainers.image.version="${APP_VERSION}"

COPY html/ /usr/share/nginx/html/
COPY nginx/nginx.conf /etc/nginx/nginx.conf
COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template

EXPOSE 8080
