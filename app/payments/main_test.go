package main

import (
	"encoding/json"
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"testing"
	"time"
)

func newTestServer(f Flags) *Server {
	s := NewServer(StaticFlags(f), slog.New(slog.NewJSONHandler(io.Discard, nil)))
	s.sleep = func(time.Duration) {}
	return s
}

func doRequest(t *testing.T, h http.Handler, method, path, body string) (*httptest.ResponseRecorder, map[string]string) {
	t.Helper()
	req := httptest.NewRequest(method, path, strings.NewReader(body))
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	var out map[string]string
	if strings.HasPrefix(rec.Header().Get("Content-Type"), "application/json") {
		if err := json.Unmarshal(rec.Body.Bytes(), &out); err != nil {
			t.Fatalf("invalid JSON response %q: %v", rec.Body.String(), err)
		}
	}
	return rec, out
}

var uuidRe = regexp.MustCompile(`^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$`)

func TestPayApproved(t *testing.T) {
	h := newTestServer(Flags{}).Routes()
	rec, body := doRequest(t, h, http.MethodPost, "/pay", `{"amount": 25.5, "order_ref": "ord-1"}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200; body=%s", rec.Code, rec.Body.String())
	}
	if body["status"] != "approved" {
		t.Errorf("status field = %q, want approved", body["status"])
	}
	if !uuidRe.MatchString(body["transaction_id"]) {
		t.Errorf("transaction_id %q is not a UUID", body["transaction_id"])
	}
}

func TestPayGatewayError(t *testing.T) {
	h := newTestServer(Flags{ErrorRate: 1.0}).Routes()
	rec, body := doRequest(t, h, http.MethodPost, "/pay", `{"amount": 10, "order_ref": "ord-2"}`)
	if rec.Code != http.StatusBadGateway {
		t.Fatalf("status = %d, want 502", rec.Code)
	}
	if body["status"] != "failed" || body["reason"] != "gateway_error" {
		t.Errorf("unexpected body: %v", body)
	}
}

func TestPayBadBody(t *testing.T) {
	h := newTestServer(Flags{}).Routes()
	cases := map[string]string{
		"malformed":       `{"amount":`,
		"missing amount":  `{"order_ref": "ord-3"}`,
		"negative amount": `{"amount": -1, "order_ref": "ord-3"}`,
		"missing ref":     `{"amount": 5}`,
		"wrong type":      `{"amount": "ten", "order_ref": "ord-3"}`,
	}
	for name, payload := range cases {
		t.Run(name, func(t *testing.T) {
			rec, _ := doRequest(t, h, http.MethodPost, "/pay", payload)
			if rec.Code != http.StatusBadRequest {
				t.Errorf("status = %d, want 400", rec.Code)
			}
		})
	}
}

func TestPayAppliesLatency(t *testing.T) {
	s := newTestServer(Flags{LatencyMS: 200, LatencyJitterMS: 100})
	var slept time.Duration
	s.sleep = func(d time.Duration) { slept = d }
	rec, _ := doRequest(t, s.Routes(), http.MethodPost, "/pay", `{"amount": 1, "order_ref": "ord-4"}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", rec.Code)
	}
	if slept < 200*time.Millisecond || slept > 300*time.Millisecond {
		t.Errorf("slept %v, want between 200ms and 300ms", slept)
	}
}

func TestHealthz(t *testing.T) {
	h := newTestServer(Flags{}).Routes()
	rec, body := doRequest(t, h, http.MethodGet, "/healthz", "")
	if rec.Code != http.StatusOK || body["status"] != "ok" {
		t.Fatalf("got %d %v, want 200 ok", rec.Code, body)
	}
}

func TestMetricsExposed(t *testing.T) {
	h := newTestServer(Flags{}).Routes()
	doRequest(t, h, http.MethodPost, "/pay", `{"amount": 3, "order_ref": "ord-5"}`)
	req := httptest.NewRequest(http.MethodGet, "/metrics", nil)
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", rec.Code)
	}
	out := rec.Body.String()
	for _, want := range []string{`payments_requests_total{status="approved"}`, "payments_duration_seconds_bucket"} {
		if !strings.Contains(out, want) {
			t.Errorf("metrics output missing %q", want)
		}
	}
}

func TestFileFlagsOverrideEnv(t *testing.T) {
	path := filepath.Join(t.TempDir(), "flags.json")
	logger := slog.New(slog.NewJSONHandler(io.Discard, nil))
	base := Flags{LatencyMS: 50, LatencyJitterMS: 10, ErrorRate: 0.1}

	ff := NewFileFlags(path, base, logger)
	if got := ff.Current(); got != base {
		t.Fatalf("without file got %+v, want %+v", got, base)
	}

	if err := os.WriteFile(path, []byte(`{"payments": {"error_rate": 0.5, "latency_ms": 300}}`), 0o644); err != nil {
		t.Fatal(err)
	}
	ff.reload()
	want := Flags{LatencyMS: 300, LatencyJitterMS: 10, ErrorRate: 0.5}
	if got := ff.Current(); got != want {
		t.Fatalf("with file got %+v, want %+v", got, want)
	}
}
