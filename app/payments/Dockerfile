FROM golang:1.23-bookworm AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY *.go ./
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -trimpath -ldflags="-s -w" -o /out/payments .

FROM gcr.io/distroless/static-debian12:nonroot
ARG APP_VERSION=0.0.0-dev
ARG APP_VARIANT=stable
ENV APP_VERSION=${APP_VERSION} \
    APP_VARIANT=${APP_VARIANT}
COPY --from=build /out/payments /payments
EXPOSE 8080
USER nonroot:nonroot
ENTRYPOINT ["/payments"]
