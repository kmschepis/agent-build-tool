from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .compiler import CompilationError, compile_project


HTML_PAGE = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>ABT Local Chat</title>
    <style>
      :root {
        color-scheme: light dark;
        font-family: system-ui, -apple-system, sans-serif;
      }
      body {
        margin: 0;
        padding: 2rem;
        background: #0f172a;
        color: #e2e8f0;
      }
      h1 {
        margin-top: 0;
      }
      .layout {
        display: grid;
        grid-template-columns: 260px 1fr;
        gap: 1.5rem;
      }
      .panel {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 12px;
        padding: 1rem;
      }
      .messages {
        height: 50vh;
        overflow-y: auto;
        padding-right: 0.5rem;
      }
      .message {
        margin-bottom: 0.75rem;
        padding: 0.75rem;
        border-radius: 8px;
        background: rgba(148, 163, 184, 0.1);
      }
      .message.user {
        background: rgba(59, 130, 246, 0.2);
      }
      .meta {
        font-size: 0.75rem;
        color: #94a3b8;
        margin-bottom: 0.25rem;
      }
      label {
        display: block;
        font-size: 0.85rem;
        margin-bottom: 0.25rem;
      }
      select,
      textarea,
      button {
        width: 100%;
        border-radius: 8px;
        border: 1px solid #1f2937;
        padding: 0.65rem;
        background: #0b1120;
        color: inherit;
        font-size: 0.9rem;
      }
      textarea {
        min-height: 120px;
        resize: vertical;
      }
      button {
        margin-top: 0.75rem;
        cursor: pointer;
        background: #2563eb;
        border: none;
      }
      button:disabled {
        opacity: 0.6;
        cursor: not-allowed;
      }
      .status {
        margin-top: 0.5rem;
        font-size: 0.85rem;
        color: #fca5a5;
      }
    </style>
  </head>
  <body>
    <h1>ABT Local Chat</h1>
    <div class="layout">
      <div class="panel">
        <label for="agent">Agent</label>
        <select id="agent"></select>
        <p class="meta" id="agent-meta"></p>
      </div>
      <div class="panel">
        <div class="messages" id="messages"></div>
        <label for="prompt">Message</label>
        <textarea id="prompt" placeholder="Ask the agent something..."></textarea>
        <button id="send">Send</button>
        <div class="status" id="status"></div>
      </div>
    </div>
    <script>
      const agentSelect = document.getElementById("agent");
      const agentMeta = document.getElementById("agent-meta");
      const messagesEl = document.getElementById("messages");
      const promptEl = document.getElementById("prompt");
      const sendBtn = document.getElementById("send");
      const statusEl = document.getElementById("status");
      const history = [];

      function renderMessages() {
        messagesEl.innerHTML = "";
        history.forEach((message) => {
          const div = document.createElement("div");
          div.className = `message ${message.role}`;
          const meta = document.createElement("div");
          meta.className = "meta";
          meta.textContent = message.role.toUpperCase();
          const content = document.createElement("div");
          content.textContent = message.content;
          div.appendChild(meta);
          div.appendChild(content);
          messagesEl.appendChild(div);
        });
        messagesEl.scrollTop = messagesEl.scrollHeight;
      }

      function setStatus(text) {
        statusEl.textContent = text || "";
      }

      async function loadAgents() {
        const response = await fetch("/api/agents");
        const data = await response.json();
        agentSelect.innerHTML = "";
        data.agents.forEach((agent) => {
          const opt = document.createElement("option");
          opt.value = agent.name;
          opt.textContent = agent.name;
          opt.dataset.provider = agent.model_provider || "unknown";
          opt.dataset.model = agent.model || "default";
          agentSelect.appendChild(opt);
        });
        updateMeta();
      }

      function updateMeta() {
        const selected = agentSelect.selectedOptions[0];
        if (!selected) {
          agentMeta.textContent = "";
          return;
        }
        agentMeta.textContent = `Provider: ${selected.dataset.provider} · Model: ${selected.dataset.model}`;
      }

      async function sendMessage() {
        const agent = agentSelect.value;
        const message = promptEl.value.trim();
        if (!agent || !message) {
          return;
        }
        sendBtn.disabled = true;
        setStatus("");
        history.push({ role: "user", content: message });
        renderMessages();
        promptEl.value = "";
        try {
          const response = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ agent, message, history }),
          });
          const data = await response.json();
          if (!response.ok) {
            throw new Error(data.error || "Request failed");
          }
          history.push({ role: "assistant", content: data.reply });
          renderMessages();
        } catch (err) {
          setStatus(err.message);
        } finally {
          sendBtn.disabled = false;
        }
      }

      agentSelect.addEventListener("change", updateMeta);
      sendBtn.addEventListener("click", sendMessage);
      promptEl.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
          sendMessage();
        }
      });

      loadAgents().catch((err) => setStatus(err.message));
    </script>
  </body>
</html>
"""


def run_server(root: Path, host: str, port: int) -> None:
    manifest = compile_project(root)

    class RuntimeHandler(BaseHTTPRequestHandler):
        def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_html(self, body: str) -> None:
            data = body.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/" or self.path.startswith("/index.html"):
                self._send_html(HTML_PAGE)
                return
            if self.path.startswith("/api/agents"):
                agents = []
                for name, agent in manifest.get("agents", {}).items():
                    agents.append(
                        {
                            "name": name,
                            "model_provider": agent.get("model_provider"),
                            "model": agent.get("model"),
                        }
                    )
                self._send_json({"agents": agents})
                return
            self.send_error(404, "Not Found")

        def do_POST(self) -> None:  # noqa: N802
            if not self.path.startswith("/api/chat"):
                self.send_error(404, "Not Found")
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self._send_json({"error": "Invalid Content-Length"}, status=400)
                return
            body = self.rfile.read(length)
            try:
                payload = json.loads(body.decode("utf-8"))
            except json.JSONDecodeError:
                self._send_json({"error": "Invalid JSON body"}, status=400)
                return

            agent_name = payload.get("agent")
            message = payload.get("message")
            history = payload.get("history") or []
            if not agent_name or not message:
                self._send_json({"error": "Missing agent or message"}, status=400)
                return

            agent = manifest.get("agents", {}).get(agent_name)
            if not agent:
                self._send_json({"error": f"Unknown agent '{agent_name}'"}, status=404)
                return

            try:
                reply = _chat_with_agent(agent, history, message)
            except RuntimeError as exc:
                self._send_json({"error": str(exc)}, status=500)
                return

            self._send_json({"reply": reply})

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
            return

    server = ThreadingHTTPServer((host, port), RuntimeHandler)
    address = f"http://{host}:{port}"
    print(f"ABT runtime listening on {address}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()


def _chat_with_agent(agent: dict[str, Any], history: list[dict[str, Any]], message: str) -> str:
    provider = agent.get("model_provider") or "openai"
    if provider != "openai":
        raise RuntimeError(f"Unsupported model_provider '{provider}'")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = agent.get("model") or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    messages = [{"role": "system", "content": agent.get("system_prompt", "")}]
    for item in history:
        role = item.get("role")
        content = item.get("content")
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": message})

    payload = json.dumps(
        {
            "model": model,
            "messages": messages,
            "temperature": agent.get("temperature", 0.2),
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8")
        raise RuntimeError(f"OpenAI request failed: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"OpenAI request failed: {exc.reason}") from exc

    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("OpenAI response missing choices")
    message_data = choices[0].get("message") or {}
    content = message_data.get("content")
    if not content:
        raise RuntimeError("OpenAI response missing content")
    return content.strip()
