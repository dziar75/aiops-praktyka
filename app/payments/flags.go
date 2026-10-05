package main

import (
	"context"
	"encoding/json"
	"errors"
	"io/fs"
	"log/slog"
	"os"
	"strconv"
	"sync"
	"time"
)

// Flags holds runtime-tunable settings used for resilience testing of the
// payment gateway integration.
type Flags struct {
	LatencyMS       int     `json:"latency_ms"`
	LatencyJitterMS int     `json:"latency_jitter_ms"`
	ErrorRate       float64 `json:"error_rate"`
}

// FlagsProvider returns the currently effective flags.
type FlagsProvider interface {
	Current() Flags
}

// StaticFlags is a FlagsProvider that always returns the same values.
type StaticFlags Flags

func (s StaticFlags) Current() Flags { return Flags(s) }

// fileFlags mirrors the flags file layout. Pointers distinguish "absent"
// from "zero" so that only keys present in the file override env values.
type fileFlags struct {
	Payments *struct {
		LatencyMS       *int     `json:"latency_ms"`
		LatencyJitterMS *int     `json:"latency_jitter_ms"`
		ErrorRate       *float64 `json:"error_rate"`
	} `json:"payments"`
}

// FileFlags merges env-derived defaults with values from a JSON file,
// reloading the file periodically.
type FileFlags struct {
	path   string
	base   Flags
	logger *slog.Logger

	mu      sync.RWMutex
	current Flags
}

func NewFileFlags(path string, base Flags, logger *slog.Logger) *FileFlags {
	f := &FileFlags{path: path, base: base, logger: logger, current: base}
	f.reload()
	return f
}

func (f *FileFlags) Current() Flags {
	f.mu.RLock()
	defer f.mu.RUnlock()
	return f.current
}

// Watch reloads the flags file at the given interval until ctx is done.
func (f *FileFlags) Watch(ctx context.Context, interval time.Duration) {
	t := time.NewTicker(interval)
	defer t.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-t.C:
			f.reload()
		}
	}
}

func (f *FileFlags) reload() {
	next := f.base
	data, err := os.ReadFile(f.path)
	switch {
	case err == nil:
		var ff fileFlags
		if err := json.Unmarshal(data, &ff); err != nil {
			f.logger.Warn("invalid flags file", "path", f.path, "error", err.Error())
			return
		}
		if p := ff.Payments; p != nil {
			if p.LatencyMS != nil {
				next.LatencyMS = *p.LatencyMS
			}
			if p.LatencyJitterMS != nil {
				next.LatencyJitterMS = *p.LatencyJitterMS
			}
			if p.ErrorRate != nil {
				next.ErrorRate = *p.ErrorRate
			}
		}
	case errors.Is(err, fs.ErrNotExist):
		// No file: env values apply.
	default:
		f.logger.Warn("cannot read flags file", "path", f.path, "error", err.Error())
		return
	}
	next = sanitize(next)

	f.mu.Lock()
	changed := next != f.current
	f.current = next
	f.mu.Unlock()
	if changed {
		f.logger.Info("flags updated",
			"latency_ms", next.LatencyMS,
			"latency_jitter_ms", next.LatencyJitterMS,
			"error_rate", next.ErrorRate)
	}
}

func sanitize(f Flags) Flags {
	if f.LatencyMS < 0 {
		f.LatencyMS = 0
	}
	if f.LatencyJitterMS < 0 {
		f.LatencyJitterMS = 0
	}
	if f.ErrorRate < 0 {
		f.ErrorRate = 0
	}
	if f.ErrorRate > 1 {
		f.ErrorRate = 1
	}
	return f
}

// FlagsFromEnv reads LATENCY_MS, LATENCY_JITTER_MS and ERROR_RATE.
func FlagsFromEnv() Flags {
	return sanitize(Flags{
		LatencyMS:       envInt("LATENCY_MS", 0),
		LatencyJitterMS: envInt("LATENCY_JITTER_MS", 0),
		ErrorRate:       envFloat("ERROR_RATE", 0),
	})
}

func envString(key, def string) string {
	if v, ok := os.LookupEnv(key); ok && v != "" {
		return v
	}
	return def
}

func envInt(key string, def int) int {
	if v, err := strconv.Atoi(os.Getenv(key)); err == nil {
		return v
	}
	return def
}

func envFloat(key string, def float64) float64 {
	if v, err := strconv.ParseFloat(os.Getenv(key), 64); err == nil {
		return v
	}
	return def
}
