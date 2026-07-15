package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"observability-tool/config"
	"observability-tool/inspector"
	"observability-tool/proxy"
)

func main() {
	log.SetFlags(log.Ldate | log.Ltime | log.Lmicroseconds)
	log.Println("ObservabilityTool starting...")

	// ── Config watcher ────────────────────────────────────────────────────────
	watcher, err := config.NewWatcher()
	if err != nil {
		log.Fatalf("config watcher init failed: %v", err)
	}
	defer watcher.Close()

	go watcher.Watch()

	// Give the watcher a moment to load the initial config.
	time.Sleep(50 * time.Millisecond)

	cfg := watcher.Get()
	log.Printf("Config loaded — target: %s  listen: :%d  flagged terms: %v",
		cfg.MCPServerURL, cfg.ListenPort, cfg.FlaggedTerms)

	// ── Inspector ─────────────────────────────────────────────────────────────
	insp := inspector.New(os.Stdout)

	// ── Proxy ─────────────────────────────────────────────────────────────────
	p := proxy.New(watcher, insp)

	// ── Mux: /event intake + catch-all proxy ──────────────────────────────────
	mux := http.NewServeMux()

	// POST /event — receives user prompts from the Flask app.
	mux.HandleFunc("/event", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		var body struct {
			Content string `json:"content"`
		}
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil || body.Content == "" {
			http.Error(w, "bad request", http.StatusBadRequest)
			return
		}
		log.Printf("[event] user_prompt received (%d chars)", len(body.Content))
		insp.LogUserPrompt(body.Content, watcher.Get().FlaggedTerms)
		w.WriteHeader(http.StatusNoContent)
	})

	// Everything else is reverse-proxied to the REST API.
	mux.Handle("/", p)

	srv := &http.Server{
		Addr:         fmt.Sprintf(":%d", cfg.ListenPort),
		Handler:      mux,
		ReadTimeout:  30 * time.Second,
		WriteTimeout: 60 * time.Second,
		IdleTimeout:  120 * time.Second,
	}

	go func() {
		log.Printf("Proxy listening on :%d → %s", cfg.ListenPort, cfg.MCPServerURL)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("proxy server error: %v", err)
		}
	}()

	// ── Graceful shutdown ─────────────────────────────────────────────────────
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	log.Println("Shutdown signal received — draining connections...")
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := srv.Shutdown(ctx); err != nil {
		log.Printf("shutdown error: %v", err)
	}
	log.Println("ObservabilityTool stopped.")
}
