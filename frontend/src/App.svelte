<svelte:head>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous" />
  <link
    href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap"
    rel="stylesheet"
  />
</svelte:head>

<script>
  import { onMount, tick } from 'svelte';

  const REPORT_URL_PATTERN = /(\/reports\/[A-Za-z0-9_\-.]+\.pdf)/;

  const INITIAL_MESSAGES = [
    {
      sender: 'bot',
      text: "Morning. I keep the records for employees, departments, and leave — ask me anything, or pull a report from the folder on the left.",
    },
  ];

  const QUICK_ASKS = [
    { label: 'Department headcounts', query: 'How many people are in each department?' },
    { label: "Who's on leave", query: 'Who is currently on leave?' },
    { label: 'Find an employee', query: 'Look up an employee by name — tell me who to search for.' },
    { label: 'Leave balances', query: 'Show me leave balances across the team.' },
  ];

  let input = '';
  let isThinking = false;
  let entrySeq = 0;
  let messages = INITIAL_MESSAGES.map((m) => createMessage(m.text, m.sender));
  let messagesContainer;
  let textarea;

  let activeTab = 'chat'; // 'chat' | 'reports'
  let railOpen = false; // mobile slide-over

  let reports = []; // { id, subject, url, note, timestamp, source }
  let reportSubject = '';
  let reportContext = '';
  let isFiling = false;
  let fileError = '';

  function escapeHtml(text) {
    return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
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

  function formatTime(date) {
    return date.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
  }

  function createMessage(text, sender) {
    const reportUrl = getReportUrl(text, sender);
    const cleanText = reportUrl ? text.replace(reportUrl, '').replace(/\s{2,}/g, ' ').trim() : text;
    entrySeq += 1;

    return {
      id: entrySeq,
      no: String(entrySeq).padStart(3, '0'),
      sender,
      text: cleanText,
      html: sender === 'user' ? escapeHtml(cleanText) : renderMarkdown(cleanText),
      reportUrl,
      time: formatTime(new Date()),
      copied: false,
    };
  }

  function fileReport(reportUrl, sourceText, source) {
    if (!reportUrl) return;
    if (reports.some((r) => r.url === reportUrl)) return;
    const filename = reportUrl.split('/').pop() ?? 'report.pdf';
    reports = [
      {
        id: `${Date.now()}-${filename}`,
        subject: filename.replace(/\.pdf$/i, '').replace(/[_-]+/g, ' '),
        url: reportUrl,
        note: sourceText,
        timestamp: formatTime(new Date()),
        source,
      },
      ...reports,
    ];
  }

  async function scrollToBottom() {
    await tick();
    if (messagesContainer) messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  async function pushMessage(text, sender) {
    const msg = createMessage(text, sender);
    messages = [...messages, msg];
    if (msg.reportUrl) fileReport(msg.reportUrl, msg.text, 'chat');
    await scrollToBottom();
    return msg;
  }

  function resizeTextarea() {
    if (!textarea) return;
    textarea.style.height = 'auto';
    textarea.style.height = `${Math.min(textarea.scrollHeight, 140)}px`;
  }

  async function sendText(text) {
    const trimmed = text.trim();
    if (!trimmed || isThinking) return;

    await pushMessage(trimmed, 'user');
    input = '';
    await tick();
    resizeTextarea();
    isThinking = true;
    await scrollToBottom();

    try {
      const response = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: trimmed }),
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

  function handleSubmit() {
    void sendText(input);
  }

  function handleKeydown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSubmit();
    }
  }

  function askQuick(query) {
    void sendText(query);
  }

  function startNewSession() {
    messages = INITIAL_MESSAGES.map((m) => createMessage(m.text, m.sender));
    entrySeq = messages.length;
    void scrollToBottom();
  }

  async function copyMessage(msg) {
    try {
      await navigator.clipboard.writeText(msg.text);
      messages = messages.map((m) => (m.id === msg.id ? { ...m, copied: true } : m));
      setTimeout(() => {
        messages = messages.map((m) => (m.id === msg.id ? { ...m, copied: false } : m));
      }, 1600);
    } catch {
      // clipboard unavailable — silently ignore
    }
  }

  async function submitReportRequest() {
    const subject = reportSubject.trim();
    if (!subject || isFiling) return;

    isFiling = true;
    fileError = '';

    try {
      const response = await fetch('/summary', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ subject, context: reportContext.trim() || undefined }),
      });

      if (!response.ok) {
        fileError = `The desk couldn't file that (server said ${response.status}). Try again.`;
        return;
      }

      const data = await response.json();
      const summaryText = data.summary ?? '';
      const reportUrl = summaryText.match(REPORT_URL_PATTERN)?.[1] ?? null;

      if (reportUrl) {
        fileReport(reportUrl, summaryText.replace(reportUrl, '').trim() || `Report on ${subject}`, 'form');
        reportSubject = '';
        reportContext = '';
      } else {
        fileError = "That went through, but no PDF came back — here's what the desk said instead.";
        fileReport('', summaryText, 'form');
        reports = reports.slice(); // no-op, kept for clarity
        // Surface the raw text as a note-only entry so it isn't lost.
        reports = [
          {
            id: `${Date.now()}-note`,
            subject,
            url: '',
            note: summaryText,
            timestamp: formatTime(new Date()),
            source: 'form',
          },
          ...reports,
        ];
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      fileError = `Couldn't reach the server: ${errorMessage}`;
    } finally {
      isFiling = false;
    }
  }

  function switchTab(tab) {
    activeTab = tab;
    railOpen = false;
  }

  onMount(() => {
    void scrollToBottom();
  });
</script>

<div id="shell">
  <button
    id="rail-toggle"
    aria-label={railOpen ? 'Close menu' : 'Open menu'}
    aria-expanded={railOpen}
    on:click={() => (railOpen = !railOpen)}
  >
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      {#if railOpen}
        <path d="M6 6L18 18M6 18L18 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
      {:else}
        <path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
      {/if}
    </svg>
  </button>

  {#if railOpen}
    <div id="rail-backdrop" on:click={() => (railOpen = false)} aria-hidden="true"></div>
  {/if}

  <aside id="rail" class:open={railOpen}>
    <div id="rail-brand">
      <span id="brand-mark">PD</span>
      <div>
        <h1>Personnel&nbsp;Desk</h1>
        <p>Records &amp; correspondence</p>
      </div>
    </div>

    <nav id="rail-tabs" aria-label="Sections">
      <button class="tab" class:active={activeTab === 'chat'} on:click={() => switchTab('chat')}>
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M4 5h16v11H8l-4 4V5z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round" />
        </svg>
        <span>Chat</span>
      </button>
      <button class="tab" class:active={activeTab === 'reports'} on:click={() => switchTab('reports')}>
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M6 3h9l5 5v13H6V3z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round" />
          <path d="M15 3v5h5" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round" />
        </svg>
        <span>Reports</span>
        {#if reports.length}
          <span class="tab-count">{reports.length}</span>
        {/if}
      </button>
    </nav>

    {#if activeTab === 'chat'}
      <div class="rail-section">
        <div class="rail-heading">Quick asks</div>
        <div class="quick-list">
          {#each QUICK_ASKS as q}
            <button class="quick-chip" on:click={() => askQuick(q.query)} disabled={isThinking}>{q.label}</button>
          {/each}
        </div>
      </div>
      <div class="rail-section">
        <button class="new-session" on:click={startNewSession}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 5v14M5 12h14" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
          </svg>
          <span>New session</span>
        </button>
      </div>
    {:else}
      <div class="rail-section">
        <div class="rail-heading">File a report</div>
        <form id="report-form" on:submit|preventDefault={submitReportRequest}>
          <label>
            <span>Subject</span>
            <input type="text" bind:value={reportSubject} placeholder="e.g. Priya Nair" autocomplete="off" />
          </label>
          <label>
            <span>Context <em>(optional)</em></span>
            <textarea rows="2" bind:value={reportContext} placeholder="Anything specific to include…"></textarea>
          </label>
          <button type="submit" disabled={isFiling || !reportSubject.trim()}>
            {isFiling ? 'Filing…' : 'Generate report'}
          </button>
          {#if fileError}
            <p class="form-error">{fileError}</p>
          {/if}
        </form>
      </div>
    {/if}

    <div id="rail-status">
      <span class="status-dot" class:busy={isThinking || isFiling}></span>
      <span>{isThinking ? 'Consulting the records…' : isFiling ? 'Filing report…' : 'Desk is ready'}</span>
    </div>
  </aside>

  <main id="stage" aria-busy={isThinking}>
    {#if activeTab === 'chat'}
      <div id="messages" bind:this={messagesContainer} role="log" aria-live="polite">
        {#each messages as message (message.id)}
          <div class={`msg ${message.sender}`}>
            <div class="msg-meta">
              <span class="msg-no">No. {message.no}</span>
              <span class="msg-who">{message.sender === 'user' ? 'You' : message.sender === 'error' ? 'Desk' : 'Desk'}</span>
              <span class="msg-time">{message.time}</span>
            </div>
            <div class="msg-bubble">{@html message.html}</div>

            {#if message.reportUrl}
              <a class="report-chip" href={message.reportUrl} download={message.reportUrl.split('/').pop()}>
                <span class="stamp-ring">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M12 3v12m0 0l-4-4m4 4l4-4M5 21h14" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
                  </svg>
                </span>
                <span>Download report</span>
              </a>
            {/if}

            {#if message.sender === 'bot'}
              <button class="copy-btn" on:click={() => copyMessage(message)}>
                {message.copied ? 'Copied' : 'Copy'}
              </button>
            {/if}
          </div>
        {/each}

        {#if messages.length <= 1}
          <div id="empty-hint">
            <p>Nothing filed yet this session — try one of the quick asks on the left, or type your own question below.</p>
          </div>
        {/if}
      </div>

      {#if isThinking}
        <div id="typing-indicator" aria-hidden="true">
          <span class="msg-who">Desk</span>
          <div id="typing-dots"><span></span><span></span><span></span></div>
        </div>
      {/if}

      <form id="chat-form" on:submit|preventDefault={handleSubmit}>
        <textarea
          bind:this={textarea}
          bind:value={input}
          rows="1"
          placeholder="Ask about an employee, department, or leave record…"
          on:input={resizeTextarea}
          on:keydown={handleKeydown}
          aria-label="Type your question"
        ></textarea>
        <button type="submit" aria-label="Send message" disabled={!input.trim() || isThinking}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M3 11.5L21 3L13.5 21L11 13L3 11.5Z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" />
          </svg>
        </button>
      </form>
    {:else}
      <div id="reports-pane">
        <header id="reports-header">
          <h2>Report ledger</h2>
          <p>Every report generated this session, newest first. The desk forgets on refresh — download what you need.</p>
        </header>

        {#if reports.length === 0}
          <div id="reports-empty">
            <div class="stamp-ring big">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M6 3h9l5 5v13H6V3z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" />
              </svg>
            </div>
            <p>No reports filed yet. Use the form on the left, or ask the desk for one in chat.</p>
          </div>
        {:else}
          <ul id="reports-list">
            {#each reports as report (report.id)}
              <li class="report-card">
                <div class="report-card-top">
                  <span class="report-subject">{report.subject}</span>
                  <span class="report-source">{report.source === 'chat' ? 'via chat' : 'via form'}</span>
                </div>
                {#if report.note}
                  <p class="report-note">{report.note}</p>
                {/if}
                <div class="report-card-bottom">
                  <span class="report-time">{report.timestamp}</span>
                  {#if report.url}
                    <a class="report-chip small" href={report.url} download={report.url.split('/').pop()}>
                      <span class="stamp-ring">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                          <path d="M12 3v12m0 0l-4-4m4 4l4-4M5 21h14" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
                        </svg>
                      </span>
                      <span>PDF</span>
                    </a>
                  {/if}
                </div>
              </li>
            {/each}
          </ul>
        {/if}
      </div>
    {/if}
  </main>
</div>

<style>
  :global(*),
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
    --page: #f3f0e7;
    --panel: #fffdf9;
    --rail-bg: #ece6d8;
    --accent: #4f6f52;
    --accent-soft: #e2e9de;
    --stamp: #b5542b;
    --stamp-soft: #f3e2d6;
    --border: #ddd5c2;
    --text-muted: #8a8270;
    --text-body: #26241d;
    --radius: 10px;
  }

  #shell {
    width: 100%;
    max-width: 920px;
    height: min(760px, 90vh);
    background: var(--panel);
    border-radius: var(--radius);
    border: 1px solid var(--border);
    box-shadow: 0 1px 2px rgba(26, 29, 41, 0.05), 0 20px 44px rgba(26, 29, 41, 0.12);
    display: flex;
    overflow: hidden;
    position: relative;
  }

  /* ---------- Rail ---------- */

  #rail {
    width: 240px;
    flex-shrink: 0;
    background: var(--rail-bg);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    padding: 20px 16px;
    gap: 18px;
    overflow-y: auto;
  }

  #rail-brand {
    display: flex;
    align-items: center;
    gap: 12px;
    padding-bottom: 4px;
  }

  #brand-mark {
    width: 36px;
    height: 36px;
    border-radius: 8px;
    background: var(--ink);
    color: #fff;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12.5px;
    font-weight: 500;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    letter-spacing: 0.02em;
  }

  #rail-brand h1 {
    font-family: 'Fraunces', serif;
    font-size: 16.5px;
    font-weight: 600;
    margin: 0;
    color: var(--ink);
    letter-spacing: -0.01em;
    line-height: 1.15;
  }

  #rail-brand p {
    font-size: 11px;
    color: var(--text-muted);
    margin: 3px 0 0;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: 0.01em;
  }

  #rail-tabs {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .tab {
    display: flex;
    align-items: center;
    gap: 9px;
    padding: 10px 12px 10px 14px;
    border: 1px solid transparent;
    background: transparent;
    border-radius: 8px 8px 0 0;
    font-family: 'Inter', sans-serif;
    font-size: 13.5px;
    font-weight: 500;
    color: var(--text-muted);
    cursor: pointer;
    text-align: left;
    position: relative;
    transition: color 0.15s ease, background 0.15s ease;
  }

  .tab:hover {
    color: var(--ink);
  }

  .tab.active {
    background: var(--panel);
    color: var(--ink);
    border-color: var(--border);
    border-bottom-color: var(--panel);
    box-shadow: 0 -1px 0 var(--accent) inset;
  }

  .tab-count {
    margin-left: auto;
    background: var(--stamp);
    color: #fff;
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    padding: 1px 6px;
    border-radius: 20px;
    line-height: 1.5;
  }

  .rail-section {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .rail-heading {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10.5px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-muted);
  }

  .quick-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .quick-chip {
    text-align: left;
    padding: 9px 11px;
    border-radius: 7px;
    border: 1px solid var(--border);
    background: var(--panel);
    font-size: 13px;
    color: var(--text-body);
    cursor: pointer;
    transition: border-color 0.15s ease, transform 0.1s ease;
  }

  .quick-chip:hover:not(:disabled) {
    border-color: var(--accent);
  }

  .quick-chip:active:not(:disabled) {
    transform: scale(0.98);
  }

  .quick-chip:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .new-session {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 9px 11px;
    border-radius: 7px;
    border: 1px dashed var(--border);
    background: transparent;
    color: var(--text-muted);
    font-size: 13px;
    cursor: pointer;
    transition: border-color 0.15s ease, color 0.15s ease;
  }

  .new-session:hover {
    border-color: var(--accent);
    color: var(--accent);
  }

  #report-form {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  #report-form label {
    display: flex;
    flex-direction: column;
    gap: 5px;
    font-size: 12px;
    color: var(--text-muted);
  }

  #report-form label em {
    font-style: normal;
    opacity: 0.75;
  }

  #report-form input,
  #report-form textarea {
    font-family: 'Inter', sans-serif;
    font-size: 13px;
    padding: 8px 10px;
    border-radius: 6px;
    border: 1px solid var(--border);
    background: var(--panel);
    color: var(--text-body);
    resize: vertical;
    outline: none;
  }

  #report-form input:focus,
  #report-form textarea:focus {
    border-color: var(--accent);
  }

  #report-form button[type='submit'] {
    padding: 9px 12px;
    border-radius: 7px;
    border: none;
    background: var(--ink);
    color: #fff;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.15s ease;
  }

  #report-form button[type='submit']:hover:not(:disabled) {
    background: var(--accent);
  }

  #report-form button[type='submit']:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }

  .form-error {
    margin: 0;
    font-size: 12px;
    color: #8c2f2f;
  }

  #rail-status {
    margin-top: auto;
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 11.5px;
    color: var(--text-muted);
    font-family: 'JetBrains Mono', monospace;
    padding-top: 10px;
    border-top: 1px solid var(--border);
  }

  .status-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--accent);
    flex-shrink: 0;
  }

  .status-dot.busy {
    background: var(--stamp);
    animation: pulse 1s ease-in-out infinite;
  }

  @keyframes pulse {
    0%,
    100% {
      opacity: 1;
    }

    50% {
      opacity: 0.35;
    }
  }

  #rail-toggle {
    display: none;
  }

  #rail-backdrop {
    display: none;
  }

  /* ---------- Stage / chat ---------- */

  #stage {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  #messages {
    flex: 1;
    padding: 22px 24px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 18px;
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
    gap: 5px;
    max-width: 86%;
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

  .msg-meta {
    display: flex;
    align-items: baseline;
    gap: 8px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    letter-spacing: 0.03em;
    color: var(--text-muted);
    padding: 0 4px;
  }

  .msg-no {
    opacity: 0.7;
  }

  .msg-who {
    text-transform: uppercase;
  }

  .msg-bubble {
    padding: 10px 14px;
    border-radius: 8px;
    font-size: 14.5px;
    line-height: 1.55;
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

  .copy-btn {
    align-self: flex-start;
    margin-left: 4px;
    border: none;
    background: transparent;
    color: var(--text-muted);
    font-family: 'JetBrains Mono', monospace;
    font-size: 10.5px;
    letter-spacing: 0.04em;
    cursor: pointer;
    padding: 2px 4px;
    text-transform: uppercase;
    transition: color 0.15s ease;
  }

  .copy-btn:hover {
    color: var(--accent);
  }

  #empty-hint {
    margin-top: 4px;
    padding: 14px 16px;
    border: 1px dashed var(--border);
    border-radius: 8px;
    color: var(--text-muted);
    font-size: 13px;
    background: var(--page);
  }

  #empty-hint p {
    margin: 0;
  }

  .report-chip {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    margin: 2px 0 0 4px;
    padding: 7px 13px 7px 9px;
    border-radius: 20px;
    background: var(--stamp-soft);
    border: 1px dashed var(--stamp);
    color: var(--stamp);
    font-size: 12.5px;
    font-weight: 600;
    text-decoration: none;
    transition: background 0.15s ease, transform 0.1s ease;
    width: fit-content;
  }

  .report-chip.small {
    padding: 5px 11px 5px 7px;
    font-size: 12px;
  }

  .report-chip:hover {
    background: var(--stamp);
    color: #fff;
  }

  .report-chip:active {
    transform: scale(0.97);
  }

  .stamp-ring {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    border: 1.5px solid currentColor;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .stamp-ring.big {
    width: 40px;
    height: 40px;
    color: var(--text-muted);
    margin: 0 auto 10px;
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
    padding: 0 24px 12px;
    display: flex;
    flex-direction: column;
    gap: 5px;
  }

  #typing-indicator .msg-who {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    text-transform: uppercase;
    color: var(--text-muted);
    padding: 0 4px;
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
    align-items: flex-end;
    gap: 8px;
    padding: 14px 16px;
    border-top: 1px solid var(--border);
    background: var(--panel);
  }

  #chat-form textarea {
    flex: 1;
    padding: 11px 14px;
    border: 1px solid var(--border);
    border-radius: 10px;
    outline: none;
    font-size: 14.5px;
    font-family: 'Inter', sans-serif;
    background: var(--page);
    color: var(--text-body);
    resize: none;
    max-height: 140px;
    line-height: 1.4;
    transition: border-color 0.15s ease, background 0.15s ease;
  }

  #chat-form textarea::placeholder {
    color: var(--text-muted);
  }

  #chat-form textarea:focus {
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

  #chat-form button:hover:not(:disabled) {
    background: var(--accent);
  }

  #chat-form button:active:not(:disabled) {
    transform: scale(0.94);
  }

  #chat-form button:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  #chat-form button:focus-visible,
  #chat-form textarea:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }

  /* ---------- Reports pane ---------- */

  #reports-pane {
    flex: 1;
    display: flex;
    flex-direction: column;
    padding: 24px 26px;
    overflow-y: auto;
  }

  #reports-header h2 {
    font-family: 'Fraunces', serif;
    font-size: 20px;
    font-weight: 600;
    margin: 0 0 4px;
    color: var(--ink);
  }

  #reports-header p {
    font-size: 13px;
    color: var(--text-muted);
    margin: 0 0 20px;
    max-width: 42ch;
  }

  #reports-empty {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    color: var(--text-muted);
    font-size: 13.5px;
    padding: 30px 20px;
  }

  #reports-empty p {
    max-width: 32ch;
    margin: 0;
  }

  #reports-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .report-card {
    border: 1px solid var(--border);
    border-radius: 9px;
    padding: 12px 14px;
    background: var(--page);
  }

  .report-card-top {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 8px;
  }

  .report-subject {
    font-weight: 600;
    font-size: 13.5px;
    color: var(--ink);
    text-transform: capitalize;
  }

  .report-source {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    text-transform: uppercase;
    color: var(--text-muted);
    flex-shrink: 0;
  }

  .report-note {
    margin: 6px 0 0;
    font-size: 12.5px;
    color: var(--text-muted);
    line-height: 1.5;
  }

  .report-card-bottom {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-top: 10px;
  }

  .report-time {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10.5px;
    color: var(--text-muted);
  }

  /* ---------- Responsive ---------- */

  @media (max-width: 720px) {
    :global(body) {
      padding: 0;
    }

    #shell {
      height: 100vh;
      max-width: 100%;
      border-radius: 0;
      border: none;
    }

    #rail-toggle {
      display: flex;
      position: absolute;
      top: 14px;
      left: 14px;
      z-index: 20;
      width: 34px;
      height: 34px;
      border-radius: 8px;
      border: 1px solid var(--border);
      background: var(--panel);
      align-items: center;
      justify-content: center;
      color: var(--ink);
      cursor: pointer;
    }

    #rail {
      position: absolute;
      inset: 0 auto 0 0;
      width: 78%;
      max-width: 300px;
      z-index: 15;
      transform: translateX(-100%);
      transition: transform 0.2s ease;
      box-shadow: 12px 0 30px rgba(0, 0, 0, 0.15);
    }

    #rail.open {
      transform: translateX(0);
    }

    #rail-backdrop {
      display: block;
      position: absolute;
      inset: 0;
      background: rgba(26, 29, 41, 0.35);
      z-index: 14;
    }

    #messages {
      padding-top: 56px;
    }

    #reports-pane {
      padding-top: 56px;
    }
  }
</style>