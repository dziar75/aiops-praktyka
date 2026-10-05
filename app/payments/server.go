package main

import (
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"log/slog"
	"math"
	mrand "math/rand/v2"
	"net/http"
	"strings"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

var (
	requestsTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "payments_requests_total",
		Help: "Total number of payment requests by outcome.",
	}, []string{"status"})

	durationSeconds = promauto.NewHistogram(prometheus.HistogramOpts{
		Name:    "payments_duration_seconds",
		Help:    "Duration of /pay requests in seconds.",
		Buckets: []float64{0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10},
	})

	buildInfo = promauto.NewGaugeVec(prometheus.GaugeOpts{
		Name: "payments_build_info",
		Help: "Build information of the payments service.",
	}, []string{"version", "variant"})
)

type payRequest struct {
	Amount   *float64 `json:"amount"`
	OrderRef string   `json:"order_ref"`
}

// Server wires HTTP handlers with their dependencies.
type Server struct {
	flags  FlagsProvider
	logger *slog.Logger
	sleep  func(time.Duration)
	rand   func() float64
}

func NewServer(flags FlagsProvider, logger *slog.Logger) *Server {
	return &Server{
		flags:  flags,
		logger: logger,
		sleep:  time.Sleep,
		rand:   mrand.Float64,
	}
}

func (s *Server) Routes() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("POST /pay", s.handlePay)
	mux.HandleFunc("GET /healthz", s.handleHealthz)
	mux.Handle("GET /metrics", promhttp.Handler())
	return mux
}

func (s *Server) handleHealthz(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *Server) handlePay(w http.ResponseWriter, r *http.Request) {
	start := time.Now()
	var (
		code     int
		outcome  string
		orderRef string
	)
	defer func() {
		elapsed := time.Since(start)
		durationSeconds.Observe(elapsed.Seconds())
		requestsTotal.WithLabelValues(outcome).Inc()
		level := slog.LevelInfo
		if code >= 500 {
			level = slog.LevelError
		} else if code >= 400 {
			level = slog.LevelWarn
		}
		s.logger.Log(r.Context(), level, "request handled",
			"route", "/pay",
			"method", r.Method,
			"status", code,
			"outcome", outcome,
			"duration_ms", float64(elapsed.Microseconds())/1000.0,
			"order_ref", orderRef,
		)
	}()

	var req payRequest
	dec := json.NewDecoder(http.MaxBytesReader(w, r.Body, 1<<16))
	dec.DisallowUnknownFields()
	if err := dec.Decode(&req); err != nil {
		code, outcome = http.StatusBadRequest, "error"
		writeJSON(w, code, map[string]string{"status": "error", "reason": "invalid_body"})
		return
	}
	orderRef = req.OrderRef
	if reason := validate(req); reason != "" {
		code, outcome = http.StatusBadRequest, "error"
		writeJSON(w, code, map[string]string{"status": "error", "reason": reason})
		return
	}

	f := s.flags.Current()
	if d := s.delay(f); d > 0 {
		s.sleep(d)
	}

	if f.ErrorRate > 0 && s.rand() < f.ErrorRate {
		code, outcome = http.StatusBadGateway, "failed"
		writeJSON(w, code, map[string]string{"status": "failed", "reason": "gateway_error"})
		return
	}

	code, outcome = http.StatusOK, "approved"
	writeJSON(w, code, map[string]string{"status": "approved", "transaction_id": newTransactionID()})
}

func validate(req payRequest) string {
	switch {
	case req.Amount == nil:
		return "amount_required"
	case math.IsNaN(*req.Amount) || math.IsInf(*req.Amount, 0) || *req.Amount <= 0:
		return "invalid_amount"
	case strings.TrimSpace(req.OrderRef) == "":
		return "order_ref_required"
	}
	return ""
}

func (s *Server) delay(f Flags) time.Duration {
	ms := f.LatencyMS
	if f.LatencyJitterMS > 0 {
		ms += int(s.rand() * float64(f.LatencyJitterMS+1))
	}
	return time.Duration(ms) * time.Millisecond
}

func newTransactionID() string {
	var b [16]byte
	if _, err := rand.Read(b[:]); err != nil {
		return fmt.Sprintf("tx-%d", time.Now().UnixNano())
	}
	b[6] = (b[6] & 0x0f) | 0x40
	b[8] = (b[8] & 0x3f) | 0x80
	h := hex.EncodeToString(b[:])
	return h[0:8] + "-" + h[8:12] + "-" + h[12:16] + "-" + h[16:20] + "-" + h[20:32]
}

func writeJSON(w http.ResponseWriter, code int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	_ = json.NewEncoder(w).Encode(v)
}
