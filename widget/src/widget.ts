// Embeddable chatbot widget: a floating action button that expands into a
// chat panel, mounted inside a Shadow DOM so host-page CSS can't bleed in
// (and vice versa). Loaded via:
//   <script src=".../widget.js" data-project="wk_..." async></script>

const currentScript = document.currentScript as HTMLScriptElement | null;

function getConfig() {
  const projectKey = currentScript?.dataset.project;
  if (!projectKey) {
    console.error("[chatbot-widget] missing required data-project attribute on the <script> tag");
    return null;
  }
  const apiBase =
    currentScript?.dataset.apiBase ||
    (currentScript?.src ? new URL(currentScript.src).origin : window.location.origin);
  return { projectKey, apiBase };
}

const STYLES = `
  :host { all: initial; }
  * { box-sizing: border-box; font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; }
  .fab {
    position: fixed; bottom: 20px; right: 20px; width: 56px; height: 56px;
    border-radius: 50%; background: #0f172a; color: white; border: none;
    box-shadow: 0 4px 12px rgba(0,0,0,0.25); cursor: pointer; font-size: 24px;
    display: flex; align-items: center; justify-content: center; z-index: 2147483000;
  }
  .panel {
    position: fixed; bottom: 88px; right: 20px; width: 340px; max-width: calc(100vw - 40px);
    height: 480px; max-height: calc(100vh - 120px); background: white; border-radius: 12px;
    box-shadow: 0 8px 30px rgba(0,0,0,0.25); display: none; flex-direction: column;
    overflow: hidden; z-index: 2147483000;
  }
  .panel.open { display: flex; }
  .header { background: #0f172a; color: white; padding: 12px 16px; font-weight: 600; font-size: 14px; }
  .messages { flex: 1; overflow-y: auto; padding: 12px; display: flex; flex-direction: column; gap: 8px; }
  .msg { max-width: 85%; padding: 8px 12px; border-radius: 10px; font-size: 14px; line-height: 1.4; white-space: pre-wrap; }
  .msg.user { align-self: flex-end; background: #0f172a; color: white; }
  .msg.bot { align-self: flex-start; background: #f1f5f9; color: #0f172a; }
  .sources { font-size: 11px; color: #94a3b8; margin-top: 2px; }
  .composer { display: flex; border-top: 1px solid #e2e8f0; padding: 8px; gap: 6px; }
  .composer input {
    flex: 1; border: 1px solid #e2e8f0; border-radius: 8px; padding: 8px 10px; font-size: 14px; outline: none;
  }
  .composer button {
    background: #0f172a; color: white; border: none; border-radius: 8px; padding: 8px 14px;
    font-size: 14px; cursor: pointer;
  }
  .composer button:disabled { opacity: 0.5; cursor: default; }
`;

function mount() {
  const config = getConfig();
  if (!config) return;

  const host = document.createElement("div");
  document.body.appendChild(host);
  const root = host.attachShadow({ mode: "open" });

  const style = document.createElement("style");
  style.textContent = STYLES;
  root.appendChild(style);

  const fab = document.createElement("button");
  fab.className = "fab";
  fab.setAttribute("aria-label", "Open chat");
  fab.textContent = "💬";
  root.appendChild(fab);

  const panel = document.createElement("div");
  panel.className = "panel";
  panel.innerHTML = `
    <div class="header">Ask a question</div>
    <div class="messages"></div>
    <form class="composer">
      <input type="text" placeholder="Type a message..." autocomplete="off" />
      <button type="submit">Send</button>
    </form>
  `;
  root.appendChild(panel);

  const messagesEl = panel.querySelector(".messages") as HTMLDivElement;
  const form = panel.querySelector(".composer") as HTMLFormElement;
  const input = panel.querySelector("input") as HTMLInputElement;
  const sendButton = panel.querySelector("button[type=submit]") as HTMLButtonElement;

  fab.addEventListener("click", () => {
    panel.classList.toggle("open");
    if (panel.classList.contains("open")) input.focus();
  });

  function addMessage(role: "user" | "bot", text: string, sources?: string[]) {
    const el = document.createElement("div");
    el.className = `msg ${role}`;
    el.textContent = text;
    if (sources && sources.length > 0) {
      const src = document.createElement("div");
      src.className = "sources";
      src.textContent = `Sources: ${sources.join(", ")}`;
      el.appendChild(src);
    }
    messagesEl.appendChild(el);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;

    addMessage("user", text);
    input.value = "";
    input.disabled = true;
    sendButton.disabled = true;

    try {
      const res = await fetch(`${config.apiBase}/public/${config.projectKey}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      if (!res.ok) throw new Error(`Request failed (${res.status})`);
      const data = await res.json();
      addMessage("bot", data.response, data.sources);
    } catch (err) {
      addMessage("bot", "Sorry, something went wrong. Please try again.");
    } finally {
      input.disabled = false;
      sendButton.disabled = false;
      input.focus();
    }
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", mount);
} else {
  mount();
}
