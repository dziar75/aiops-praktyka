package main

import (
	"context"
	"errors"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"
)

const (
	listenPort       = "8080"
	defaultFlagsFile = "/etc/kantyna/flags/flags.json"
	flagsReloadEvery = 15 * time.Second
)

func main() {
	version := envString("APP_VERSION", "0.0.0-dev")
	variant := envString("APP_VARIANT", "stable")

	logger := slog.New(slog.NewJSONHandler(os.Stdout, nil)).With(
		"service", "payments",
		"version", version,
		"variant", variant,
	)
	slog.SetDefault(logger)

	buildInfo.WithLabelValues(version, variant).Set(1)

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	flags := NewFileFlags(envString("FLAGS_FILE", defaultFlagsFile), FlagsFromEnv(), logger)
	go flags.Watch(ctx, flagsReloadEvery)

	if ep := os.Getenv("OTEL_EXPORTER_OTLP_ENDPOINT"); ep != "" {
		logger.Info("OTLP endpoint configured; tracing export is not enabled in this build", "endpoint", ep)
	}

	srv := &http.Server{
		Addr:              ":" + listenPort,
		Handler:           NewServer(flags, logger).Routes(),
		ReadHeaderTimeout: 5 * time.Second,
	}

	go func() {
		<-ctx.Done()
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		_ = srv.Shutdown(shutdownCtx)
	}()

	f := flags.Current()
	logger.Info("payments service starting",
		"port", listenPort,
		"latency_ms", f.LatencyMS,
		"latency_jitter_ms", f.LatencyJitterMS,
		"error_rate", f.ErrorRate,
	)
	if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
		logger.Error("server failed", "error", err.Error())
		os.Exit(1)
	}
	logger.Info("payments service stopped")
}
