<svelte:head>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous" />
  <link
    href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap"
    rel="stylesheet"
  />
</svelte:head>

<script>
  import { onMount, tick } from 'svelte';

  const REPORT_URL_PATTERN = /(\/reports\/[A-Za-z0-9_\-.]+\.pdf)/;

  const INITIAL_MESSAGES = [
    {
      sender: 'bot',
      text: 'Hi — I can look up employees, department headcounts, and leave balances. Try asking something like "how many departments are there?"',
    },
  ];

  let input = '';
  let isThinking = false;
  let messages = INITIAL_MESSAGES.map((message) => createMessage(message.text, message.sender));
  let messagesContainer;

  function escapeHtml(text) {
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  function renderMarkdown(text) {
    let html = escapeHtml(text);

    html = html.replace(/\[([^\]]+)\]\(([^)]*)\)/g, (_, label, url) => {
      const trimmedUrl = url.trim();
      if (!trimmedUrl) return label;
      return `<a href="${trimmedUrl}" target="_blank" rel="noopener noreferrer">${label}</a>`;
    });

    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    html = html.replace(/\n/g, '<br>');

    return html;
  }

  function getReportUrl(text, sender) {
    if (sender !== 'bot') return null;
    return text.match(REPORT_URL_PATTERN)?.[1] ?? null;
  }

  function createMessage(text, sender) {
    const reportUrl = getReportUrl(text, sender);
    const cleanText = reportUrl
      ? text.replace(reportUrl, '').replace(/\s{2,}/g, ' ').trim()
      : text;

    return {
      sender,
      text: cleanText,
      html: sender === 'user' ? escapeHtml(cleanText) : renderMarkdown(cleanText),
      reportUrl,
    };
  }

  async function scrollToBottom() {
    await tick();

    if (messagesContainer) {
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
  }

  async function pushMessage(text, sender) {
    messages = [...messages, createMessage(text, sender)];
    await scrollToBottom();
  }

  async function handleSubmit() {
    const text = input.trim();
    if (!text) return;

    await pushMessage(text, 'user');
    input = '';
    isThinking = true;
    await scrollToBottom();

    try {
      const response = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      });

      if (!response.ok) {
        await pushMessage(`Something went wrong on the server (${response.status}). Try again.`, 'error');
        return;
      }

      const data = await response.json();
      await pushMessage(data.assistant ?? "I didn't get a response back. Try rephrasing.", 'bot');
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      await pushMessage(`Couldn't reach the server: ${errorMessage}`, 'error');
    } finally {
      isThinking = false;
      await scrollToBottom();
    }
  }

  onMount(() => {
    void scrollToBottom();
  });
</script>

<main id="app" aria-busy={isThinking}>
  <header id="app-header">
    <div id="brand">
      <span id="brand-mark">PD</span>
      <div id="brand-text">
        <h1>Personnel Desk</h1>
        <p>Ask about employees, departments, and leave records</p>
      </div>
    </div>
    <div id="status-line" class:thinking={isThinking} aria-hidden="true"></div>
  </header>

  <div id="messages" bind:this={messagesContainer} role="log" aria-live="polite">
    {#each messages as message}
      <div class={`msg ${message.sender}`}>
        <div class="msg-label">{message.sender === 'user' ? 'You' : 'Desk'}</div>
        <div class="msg-bubble">{@html message.html}</div>

        {#if message.reportUrl}
          <a class="report-chip" href={message.reportUrl} download={message.reportUrl.split('/').pop()}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 3v12m0 0l-4-4m4 4l4-4M5 21h14" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
            <span>Download report (PDF)</span>
          </a>
        {/if}
      </div>
    {/each}
  </div>

  <div id="typing-indicator" class:hidden={!isThinking} aria-hidden="true">
    <div class="msg-label">Desk</div>
    <div id="typing-dots"><span></span><span></span><span></span></div>
  </div>

  <form id="chat-form" on:submit|preventDefault={handleSubmit}>
    <input
      id="chat-input"
      bind:value={input}
      type="text"
      placeholder="Ask about an employee, department, or leave record…"
      autocomplete="off"
      aria-label="Type your question"
    />
    <button type="submit" aria-label="Send message">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M3 11.5L21 3L13.5 21L11 13L3 11.5Z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" />
      </svg>
    </button>
  </form>
</main>

<style>
  :global(*) {
    box-sizing: border-box;
  }

  :global(*::before),
  :global(*::after) {
    box-sizing: border-box;
  }

  @media (prefers-reduced-motion: reduce) {
    :global(*),
    :global(*::before),
    :global(*::after) {
      animation-duration: 0.01ms !important;
      transition-duration: 0.01ms !important;
    }
  }

  :global(body) {
    font-family: 'Inter', system-ui, sans-serif;
    background: var(--page);
    margin: 0;
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
    padding: 24px;
    color: var(--text-body);
  }

  :global(:root) {
    --ink: #1a1d29;
    --page: #f7f7f5;
    --panel: #ffffff;
    --accent: #4f6f52;
    --accent-soft: #e4ebe3;
    --border: #e8e6e0;
    --text-muted: #8b8578;
    --text-body: #2a2d34;
    --radius: 10px;
  }

  #app {
    width: 100%;
    max-width: 560px;
    height: min(720px, 88vh);
    background: var(--panel);
    border-radius: var(--radius);
    border: 1px solid var(--border);
    box-shadow: 0 1px 2px rgba(26, 29, 41, 0.04), 0 12px 32px rgba(26, 29, 41, 0.08);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  #app-header {
    padding: 18px 22px 0;
    background: var(--panel);
    border-bottom: 1px solid var(--border);
  }

  #brand {
    display: flex;
    align-items: center;
    gap: 14px;
    padding-bottom: 16px;
  }

  #brand-mark {
    width: 38px;
    height: 38px;
    border-radius: 8px;
    background: var(--ink);
    color: #fff;
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    font-weight: 500;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    letter-spacing: 0.02em;
  }

  #brand-text h1 {
    font-family: 'Fraunces', serif;
    font-size: 19px;
    font-weight: 600;
    margin: 0;
    color: var(--ink);
    letter-spacing: -0.01em;
  }

  #brand-text p {
    font-size: 12.5px;
    color: var(--text-muted);
    margin: 2px 0 0;
  }

  #status-line {
    height: 2px;
    background: var(--border);
    margin: 0 -22px;
    position: relative;
    overflow: hidden;
  }

  #status-line.thinking::after {
    content: '';
    position: absolute;
    inset: 0;
    width: 40%;
    background: var(--accent);
    animation: ledger-sweep 1.1s ease-in-out infinite;
  }

  @keyframes ledger-sweep {
    0% {
      transform: translateX(-100%);
    }

    100% {
      transform: translateX(250%);
    }
  }

  #messages {
    flex: 1;
    padding: 20px 22px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  #messages::-webkit-scrollbar {
    width: 8px;
  }

  #messages::-webkit-scrollbar-thumb {
    background: var(--border);
    border-radius: 4px;
  }

  .msg {
    display: flex;
    flex-direction: column;
    gap: 4px;
    max-width: 88%;
    animation: rise 0.25s ease;
  }

  @keyframes rise {
    from {
      opacity: 0;
      transform: translateY(4px);
    }

    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .msg.user {
    align-self: flex-end;
    align-items: flex-end;
  }

  .msg.bot,
  .msg.error {
    align-self: flex-start;
  }

  .msg-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10.5px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-muted);
    padding: 0 4px;
  }

  .msg-bubble {
    padding: 10px 14px;
    border-radius: 8px;
    font-size: 14.5px;
    line-height: 1.5;
    white-space: pre-wrap;
    word-wrap: break-word;
  }

  .msg.bot .msg-bubble {
    background: var(--page);
    border-left: 2px solid var(--accent);
    color: var(--text-body);
    border-radius: 4px 8px 8px 8px;
  }

  .msg.user .msg-bubble {
    background: var(--ink);
    color: #fff;
    border-radius: 8px 4px 8px 8px;
  }

  .msg.error .msg-bubble {
    background: #fbeaea;
    border-left: 2px solid #c24a4a;
    color: #8c2f2f;
  }

  .report-chip {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    margin-top: 2px;
    padding: 8px 14px;
    border-radius: 7px;
    background: var(--ink);
    color: #fff;
    font-size: 13px;
    font-weight: 500;
    text-decoration: none;
    transition: background 0.15s ease, transform 0.1s ease;
    width: fit-content;
  }

  .report-chip:hover {
    background: var(--accent);
  }

  .report-chip:active {
    transform: scale(0.97);
  }

  :global(.msg-bubble strong) {
    font-weight: 600;
    color: var(--ink);
  }

  :global(.msg.user .msg-bubble strong) {
    color: #fff;
  }

  :global(.msg-bubble em) {
    font-style: italic;
  }

  :global(.msg-bubble code) {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.9em;
    background: rgba(0, 0, 0, 0.06);
    padding: 1px 5px;
    border-radius: 4px;
  }

  :global(.msg.user .msg-bubble code) {
    background: rgba(255, 255, 255, 0.15);
  }

  :global(.msg-bubble a) {
    color: var(--accent);
    text-decoration: underline;
    text-decoration-color: var(--border);
  }

  :global(.msg-bubble a:hover) {
    text-decoration-color: var(--accent);
  }

  #typing-indicator {
    padding: 0 22px 14px;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  #typing-indicator.hidden {
    display: none;
  }

  #typing-dots {
    display: flex;
    gap: 4px;
    padding: 10px 14px;
    width: fit-content;
    background: var(--page);
    border-left: 2px solid var(--accent);
    border-radius: 4px 8px 8px 8px;
  }

  #typing-dots span {
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: var(--text-muted);
    animation: bounce 1.2s infinite ease-in-out;
  }

  #typing-dots span:nth-child(2) {
    animation-delay: 0.15s;
  }

  #typing-dots span:nth-child(3) {
    animation-delay: 0.3s;
  }

  @keyframes bounce {
    0%,
    80%,
    100% {
      transform: translateY(0);
      opacity: 0.4;
    }

    40% {
      transform: translateY(-3px);
      opacity: 1;
    }
  }

  #chat-form {
    display: flex;
    gap: 8px;
    padding: 14px 16px;
    border-top: 1px solid var(--border);
    background: var(--panel);
  }

  #chat-input {
    flex: 1;
    padding: 11px 14px;
    border: 1px solid var(--border);
    border-radius: 8px;
    outline: none;
    font-size: 14.5px;
    font-family: 'Inter', sans-serif;
    background: var(--page);
    color: var(--text-body);
    transition: border-color 0.15s ease, background 0.15s ease;
  }

  #chat-input::placeholder {
    color: var(--text-muted);
  }

  #chat-input:focus {
    border-color: var(--accent);
    background: var(--panel);
  }

  #chat-form button {
    width: 42px;
    height: 42px;
    flex-shrink: 0;
    border-radius: 8px;
    border: none;
    background: var(--ink);
    color: #fff;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background 0.15s ease, transform 0.1s ease;
  }

  #chat-form button:hover {
    background: var(--accent);
  }

  #chat-form button:active {
    transform: scale(0.94);
  }

  #chat-form button:focus-visible,
  #chat-input:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }

  @media (max-width: 480px) {
    :global(body) {
      padding: 0;
    }

    #app {
      height: 100vh;
      max-width: 100%;
      border-radius: 0;
      border: none;
    }
  }
</style>