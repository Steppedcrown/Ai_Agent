// Package proxy implements a low-latency reverse proxy that intercepts
// MCP traffic, delegates inspection to the inspector package, and forwards
// requests to the configured upstream target.
package proxy

import (
	"bytes"
	"io"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"time"

	"observability-tool/config"
	"observability-tool/inspector"
)

// ObservabilityProxy is an http.Handler that sits between the agent and the
// MCP server, intercepting and logging all traffic.
type ObservabilityProxy struct {
	watcher *config.Watcher
	insp    *inspector.Inspector
}

// New constructs an ObservabilityProxy.
func New(w *config.Watcher, insp *inspector.Inspector) *ObservabilityProxy {
	return &ObservabilityProxy{watcher: w, insp: insp}
}

// ServeHTTP implements http.Handler.
//
// Flow:
//  1. Snapshot the current config (target URL, flagged terms).
//  2. Read and buffer the request body so it can be both inspected and forwarded.
//  3. Run the inspector against the buffered bytes.
//  4. Build a single-host reverse proxy for the live target URL.
//  5. Override the Director to restore the buffered body on the outbound request.
//  6. Wrap the ResponseWriter to capture status code for the completion log.
//  7. Measure end-to-end latency and emit a completion event.
func (op *ObservabilityProxy) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	start := time.Now()
	cfg := op.watcher.Get()

	// ── 1. Buffer request body ─────────────────────────────────────────────────
	bodyBytes := readAndRestore(r)

	// ── 2. Inspect ─────────────────────────────────────────────────────────────
	op.insp.Inspect(bodyBytes, r.URL.Path, cfg.FlaggedTerms)

	// ── 3. Build reverse proxy for the live target ────────────────────────────
	targetURL, err := url.Parse(cfg.MCPServerURL)
	if err != nil {
		log.Printf("[proxy] invalid target URL %q: %v", cfg.MCPServerURL, err)
		http.Error(w, "bad gateway configuration", http.StatusBadGateway)
		return
	}

	rp := httputil.NewSingleHostReverseProxy(targetURL)

	// ── 4. Override Director to restore body on the forwarded request ─────────
	// httputil's default Director rewrites Host/Scheme but doesn't touch Body.
	// We replace the Body here so the upstream receives the full payload even
	// after we consumed it above.
	origDirector := rp.Director
	rp.Director = func(req *http.Request) {
		origDirector(req)
		req.Body = io.NopCloser(bytes.NewReader(bodyBytes))
		req.ContentLength = int64(len(bodyBytes))
	}

	// ── 5. Capture status code via response recorder ──────────────────────────
	rec := &responseRecorder{ResponseWriter: w, statusCode: http.StatusOK}

	// ── 6. Error handler — log upstream errors instead of letting them panic ──
	rp.ErrorHandler = func(rw http.ResponseWriter, req *http.Request, err error) {
		log.Printf("[proxy] upstream error (path=%s): %v", req.URL.Path, err)
		http.Error(rw, "upstream unavailable", http.StatusBadGateway)
	}

	rp.ServeHTTP(rec, r)

	// ── 7. Emit completion telemetry ──────────────────────────────────────────
	op.insp.LogCompletion(r.URL.Path, rec.statusCode, time.Since(start))
}

// ── Helpers ───────────────────────────────────────────────────────────────────

// readAndRestore drains r.Body into a byte slice and replaces r.Body with a
// fresh reader over the same bytes, leaving the request intact for forwarding.
func readAndRestore(r *http.Request) []byte {
	if r.Body == nil {
		return nil
	}
	b, err := io.ReadAll(r.Body)
	r.Body.Close()
	if err != nil {
		log.Printf("[proxy] body read error: %v", err)
	}
	r.Body = io.NopCloser(bytes.NewReader(b))
	return b
}

// responseRecorder wraps http.ResponseWriter to capture the status code written
// by the reverse proxy so we can include it in the completion event.
type responseRecorder struct {
	http.ResponseWriter
	statusCode int
}

func (rr *responseRecorder) WriteHeader(code int) {
	rr.statusCode = code
	rr.ResponseWriter.WriteHeader(code)
}

// Flush implements http.Flusher if the underlying writer supports it, ensuring
// streaming / SSE responses are not buffered inside the recorder.
func (rr *responseRecorder) Flush() {
	if f, ok := rr.ResponseWriter.(http.Flusher); ok {
		f.Flush()
	}
}
