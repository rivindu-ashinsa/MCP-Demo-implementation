const form = document.getElementById("chat-form");
const input = document.getElementById("chat-input");
const messages = document.getElementById("messages");
const typingIndicator = document.getElementById("typing-indicator");
const statusLine = document.getElementById("status-line");

// Matches "/reports/whatever.pdf" anywhere in the agent's reply text
const REPORT_URL_PATTERN = /(\/reports\/[A-Za-z0-9_\-.]+\.pdf)/;

// Minimal, safe markdown -> HTML for the small subset an LLM typically produces:
// **bold**, *italic*, `code`, [text](url), and line breaks. Escapes HTML first
// so the model can never inject arbitrary tags.
function renderMarkdown(text) {
  const escapeHtml = (s) =>
    s.replace(/&/g, "&amp;")
     .replace(/</g, "&lt;")
     .replace(/>/g, "&gt;");

  let html = escapeHtml(text);

  // Links: [label](url) — only keep if url is non-empty, otherwise just show label
  html = html.replace(/\[([^\]]+)\]\(([^)]*)\)/g, (_, label, url) => {
    const trimmedUrl = url.trim();
    if (!trimmedUrl) return label;
    return `<a href="${trimmedUrl}" target="_blank" rel="noopener noreferrer">${label}</a>`;
  });

  // Bold: **text**
  html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");

  // Italic: *text* (after bold, so it doesn't eat the ** pairs)
  html = html.replace(/\*([^*]+)\*/g, "<em>$1</em>");

  // Inline code: `text`
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");

  // Line breaks
  html = html.replace(/\n/g, "<br>");

  return html;
}

function addMessage(text, sender) {
  const wrapper = document.createElement("div");
  wrapper.className = `msg ${sender}`;

  const label = document.createElement("div");
  label.className = "msg-label";
  label.textContent = sender === "user" ? "You" : "Desk";

  const bubble = document.createElement("div");
  bubble.className = "msg-bubble";

  const match = sender === "bot" ? text.match(REPORT_URL_PATTERN) : null;

  if (match) {
    const reportUrl = match[1];
    const cleanText = text.replace(reportUrl, "").replace(/\s{2,}/g, " ").trim();
    bubble.innerHTML = sender === "user" ? escapeForUser(cleanText) : renderMarkdown(cleanText);
    wrapper.appendChild(label);
    wrapper.appendChild(bubble);

    const reportChip = document.createElement("a");
    reportChip.className = "report-chip";
    reportChip.href = reportUrl;
    reportChip.download = reportUrl.split("/").pop();
    reportChip.innerHTML = `
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 3v12m0 0l-4-4m4 4l4-4M5 21h14" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      <span>Download report (PDF)</span>
    `;
    wrapper.appendChild(reportChip);
  } else {
    bubble.innerHTML = sender === "user" ? escapeForUser(text) : renderMarkdown(text);
    wrapper.appendChild(label);
    wrapper.appendChild(bubble);
  }

  messages.appendChild(wrapper);
  messages.scrollTop = messages.scrollHeight;
}

// User's own typed message: escape only, no markdown rendering (it's their raw input)
function escapeForUser(s) {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function setThinking(isThinking) {
  typingIndicator.classList.toggle("hidden", !isThinking);
  statusLine.classList.toggle("thinking", isThinking);
  if (isThinking) {
    messages.scrollTop = messages.scrollHeight;
  }
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text) return;

  addMessage(text, "user");
  input.value = "";
  setThinking(true);

  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });

    if (!res.ok) {
      addMessage(`Something went wrong on the server (${res.status}). Try again.`, "error");
      return;
    }

    const data = await res.json();
    addMessage(data.assistant ?? "I didn't get a response back. Try rephrasing.", "bot");
  } catch (err) {
    addMessage(`Couldn't reach the server: ${err.message}`, "error");
  } finally {
    setThinking(false);
  }
});