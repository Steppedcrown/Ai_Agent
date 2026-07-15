// Package inspector parses MCP JSON-RPC payloads and emits structured
// telemetry events as newline-delimited JSON to any io.Writer.
package inspector

import (
        "bytes"
        "encoding/json"
        "io"
        "log"
        "strings"
        "time"
)

// ── MCP / JSON-RPC types ──────────────────────────────────────────────────────

// rpcEnvelope is a minimal decode of any JSON-RPC 2.0 message.
type rpcEnvelope struct {
        JSONRPC string          `json:"jsonrpc"`
        ID      json.RawMessage `json:"id"`
        Method  string          `json:"method"`
        Params  json.RawMessage `json:"params"`
}

// toolCallParams mirrors the MCP tools/call parameter schema.
type toolCallParams struct {
        Name      string          `json:"name"`
        Arguments json.RawMessage `json:"arguments"`
}

// message represents a single entry in a messages array (e.g. OpenAI-style).
type message struct {
        Role    string `json:"role"`
        Content string `json:"content"`
}

// samplingRequest loosely covers the MCP sampling/createMessage params.
type samplingRequest struct {
        Messages []message `json:"messages"`
        System   string    `json:"system"`
}

// ── Event types ───────────────────────────────────────────────────────────────

// EventType classifies an intercepted telemetry event.
type EventType string

const (
        EventToolCall    EventType = "tool_call"
        EventPromptAudit EventType = "prompt_audit"
        EventCompletion  EventType = "completion"
        EventRaw         EventType = "raw_request"
        EventUserPrompt  EventType = "user_prompt"
)

// Event is the structured log record written to the output stream.
type Event struct {
        Timestamp    time.Time   `json:"timestamp"`
        EventType    EventType   `json:"event_type"`
        Path         string      `json:"path,omitempty"`
        Method       string      `json:"rpc_method,omitempty"`
        ToolName     string      `json:"tool_name,omitempty"`
        Arguments    interface{} `json:"arguments,omitempty"`
        Content      string      `json:"content,omitempty"`
        SystemPrompt string      `json:"system_prompt,omitempty"`
        FlaggedTerms []string    `json:"flagged_terms_found,omitempty"`
        StatusCode   int         `json:"status_code,omitempty"`
        LatencyMS    float64     `json:"latency_ms,omitempty"`
}

// ── Inspector ─────────────────────────────────────────────────────────────────

// Inspector parses request bodies and writes telemetry events.
type Inspector struct {
        out io.Writer
        enc *json.Encoder
}

// New creates an Inspector that writes newline-delimited JSON to out.
func New(out io.Writer) *Inspector {
        enc := json.NewEncoder(out)
        enc.SetIndent("", "  ")
        return &Inspector{out: out, enc: enc}
}

// Inspect parses bodyBytes and emits the appropriate telemetry events.
// flaggedTerms is read from the live config so it reflects the latest rules.
func (ins *Inspector) Inspect(bodyBytes []byte, path string, flaggedTerms []string) {
        if len(bytes.TrimSpace(bodyBytes)) == 0 {
                return
        }

        var env rpcEnvelope
        if err := json.Unmarshal(bodyBytes, &env); err != nil {
                // Not JSON-RPC — emit a raw event for debugging.
                ins.emit(Event{
                        EventType: EventRaw,
                        Path:      path,
                })
                return
        }

        switch env.Method {
        case "tools/call":
                ins.handleToolCall(env, path)

        case "sampling/createMessage":
                ins.handleSampling(env, path, flaggedTerms)

        default:
                // For any other method, still check for embedded system prompts.
                ins.auditArbitraryPrompts(env, path, flaggedTerms)
        }
}

// LogUserPrompt records a user message sent to the chatbot.
func (ins *Inspector) LogUserPrompt(content string) {
        ins.emit(Event{
                EventType: EventUserPrompt,
                Content:   truncate(content, 500),
        })
}

// LogCompletion records the HTTP response metadata once the round-trip ends.
func (ins *Inspector) LogCompletion(path string, statusCode int, latency time.Duration) {
        ins.emit(Event{
                EventType:  EventCompletion,
                Path:       path,
                StatusCode: statusCode,
                LatencyMS:  float64(latency.Microseconds()) / 1000.0,
        })
}

// ── Internal handlers ─────────────────────────────────────────────────────────

func (ins *Inspector) handleToolCall(env rpcEnvelope, path string) {
        var params toolCallParams
        if err := json.Unmarshal(env.Params, &params); err != nil {
                log.Printf("[inspector] tools/call param parse error: %v", err)
                return
        }

        var args interface{}
        if len(params.Arguments) > 0 {
                if err := json.Unmarshal(params.Arguments, &args); err != nil {
                        args = string(params.Arguments)
                }
        }

        ins.emit(Event{
                EventType: EventToolCall,
                Path:      path,
                Method:    env.Method,
                ToolName:  params.Name,
                Arguments: args,
        })
}

func (ins *Inspector) handleSampling(env rpcEnvelope, path string, flaggedTerms []string) {
        var sr samplingRequest
        if err := json.Unmarshal(env.Params, &sr); err != nil {
                log.Printf("[inspector] sampling/createMessage param parse error: %v", err)
                return
        }

        // Collect system prompt text from top-level field and/or role=system messages.
        var promptParts []string
        if sr.System != "" {
                promptParts = append(promptParts, sr.System)
        }
        for _, msg := range sr.Messages {
                if strings.EqualFold(msg.Role, "system") {
                        promptParts = append(promptParts, msg.Content)
                }
        }

        fullPrompt := strings.Join(promptParts, "\n")
        ins.emitPromptAudit(path, env.Method, fullPrompt, flaggedTerms)
}

// auditArbitraryPrompts scans any RPC method's raw params for system-role
// message arrays, covering non-standard or forwarded Anthropic API traffic.
func (ins *Inspector) auditArbitraryPrompts(env rpcEnvelope, path string, flaggedTerms []string) {
        if len(env.Params) == 0 {
                return
        }

        // Try to extract a "messages" array from params.
        var container struct {
                Messages []message `json:"messages"`
                System   string    `json:"system"`
        }
        if err := json.Unmarshal(env.Params, &container); err != nil {
                return
        }

        var promptParts []string
        if container.System != "" {
                promptParts = append(promptParts, container.System)
        }
        for _, msg := range container.Messages {
                if strings.EqualFold(msg.Role, "system") {
                        promptParts = append(promptParts, msg.Content)
                }
        }

        if len(promptParts) == 0 {
                return
        }

        ins.emitPromptAudit(path, env.Method, strings.Join(promptParts, "\n"), flaggedTerms)
}

func (ins *Inspector) emitPromptAudit(path, method, prompt string, flaggedTerms []string) {
        found := matchFlaggedTerms(prompt, flaggedTerms)
        ins.emit(Event{
                EventType:    EventPromptAudit,
                Path:         path,
                Method:       method,
                SystemPrompt: truncate(prompt, 500),
                FlaggedTerms: found,
        })
}

// ── Helpers ───────────────────────────────────────────────────────────────────

func (ins *Inspector) emit(e Event) {
        e.Timestamp = time.Now().UTC()
        if err := ins.enc.Encode(e); err != nil {
                log.Printf("[inspector] emit error: %v", err)
        }
}

// matchFlaggedTerms returns any flaggedTerms found (case-insensitive) in text.
func matchFlaggedTerms(text string, terms []string) []string {
        lower := strings.ToLower(text)
        var found []string
        for _, term := range terms {
                if strings.Contains(lower, strings.ToLower(term)) {
                        found = append(found, term)
                }
        }
        return found
}

// truncate cuts s to maxLen runes and appends "…" if it was cut.
func truncate(s string, maxLen int) string {
        runes := []rune(s)
        if len(runes) <= maxLen {
                return s
        }
        return string(runes[:maxLen]) + "…"
}
