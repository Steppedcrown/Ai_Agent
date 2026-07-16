// Package config handles dynamic configuration loading and file-system watching
// for the ObservabilityTool agent.
package config

import (
        "encoding/json"
        "log"
        "os"
        "path/filepath"
        "sync"

        "github.com/fsnotify/fsnotify"
)

const defaultConfigPath = "mcp_config.json"

// AgentConfig is the configuration schema read from mcp_config.json.
type AgentConfig struct {
        MCPServerURL string   `json:"mcp_server_url"`
        ListenPort   int      `json:"listen_port"`
        FlaggedTerms []string `json:"flagged_terms"`
}

// defaults returns a safe fallback configuration.
func defaults() AgentConfig {
        return AgentConfig{
                MCPServerURL: "http://localhost:8000",
                ListenPort:   3001,
                FlaggedTerms: []string{},
        }
}

// Watcher monitors a config file on disk and keeps an in-memory AgentConfig
// up to date without restarting the proxy listener.
type Watcher struct {
        path    string
        mu      sync.RWMutex
        current AgentConfig
        fsw     *fsnotify.Watcher
}

// NewWatcher creates a Watcher for the default config path (~/.myagent/mcp_config.json).
// If the file or directory does not exist, they are created with default values.
func NewWatcher() (*Watcher, error) {
        path := expandHome(defaultConfigPath)

        if err := ensureConfig(path); err != nil {
                return nil, err
        }

        fsw, err := fsnotify.NewWatcher()
        if err != nil {
                return nil, err
        }

        w := &Watcher{
                path:    path,
                current: defaults(),
                fsw:     fsw,
        }

        // Load once synchronously so config is available before Watch() goroutine starts.
        if err := w.reload(); err != nil {
                log.Printf("[config] initial load failed (%v) — using defaults", err)
        }

        // Watch the parent directory so renames/atomic writes are also caught.
        if err := fsw.Add(filepath.Dir(path)); err != nil {
                return nil, err
        }

        return w, nil
}

// Watch blocks and processes fsnotify events. Run this in a goroutine.
func (w *Watcher) Watch() {
        log.Printf("[config] watching %s", w.path)
        for {
                select {
                case event, ok := <-w.fsw.Events:
                        if !ok {
                                return
                        }
                        if filepath.Clean(event.Name) != filepath.Clean(w.path) {
                                continue
                        }
                        if event.Has(fsnotify.Write) || event.Has(fsnotify.Create) {
                                log.Printf("[config] change detected (%s) — reloading", event.Op)
                                if err := w.reload(); err != nil {
                                        log.Printf("[config] reload error: %v", err)
                                } else {
                                        cfg := w.Get()
                                        log.Printf("[config] updated — target: %s  port: %d  flagged: %v",
                                                cfg.MCPServerURL, cfg.ListenPort, cfg.FlaggedTerms)
                                }
                        }

                case err, ok := <-w.fsw.Errors:
                        if !ok {
                                return
                        }
                        log.Printf("[config] fsnotify error: %v", err)
                }
        }
}

// Get returns a snapshot of the current config under a read lock.
func (w *Watcher) Get() AgentConfig {
        w.mu.RLock()
        defer w.mu.RUnlock()
        return w.current
}

// Close releases the underlying fsnotify watcher.
func (w *Watcher) Close() error {
        return w.fsw.Close()
}

// reload reads the config file from disk and replaces the in-memory copy.
// Called under no lock; takes the write lock internally.
func (w *Watcher) reload() error {
        f, err := os.Open(w.path)
        if err != nil {
                return err
        }
        defer f.Close()

        var cfg AgentConfig
        if err := json.NewDecoder(f).Decode(&cfg); err != nil {
                return err
        }

        // Apply defaults for missing fields.
        if cfg.MCPServerURL == "" {
                cfg.MCPServerURL = defaults().MCPServerURL
        }
        if cfg.ListenPort == 0 {
                cfg.ListenPort = defaults().ListenPort
        }

        w.mu.Lock()
        w.current = cfg
        w.mu.Unlock()
        return nil
}

// expandHome replaces a leading ~ with the actual home directory.
func expandHome(path string) string {
        if len(path) >= 2 && path[:2] == "~/" {
                home, err := os.UserHomeDir()
                if err != nil {
                        return path
                }
                return filepath.Join(home, path[2:])
        }
        return path
}

// ensureConfig creates the config file with defaults if it doesn't exist.
func ensureConfig(path string) error {
        if _, err := os.Stat(path); err == nil {
                return nil // already exists
        }

        if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
                return err
        }

        cfg := defaults()
        data, err := json.MarshalIndent(cfg, "", "  ")
        if err != nil {
                return err
        }

        if err := os.WriteFile(path, data, 0o644); err != nil {
                return err
        }

        log.Printf("[config] created default config at %s", path)
        return nil
}
