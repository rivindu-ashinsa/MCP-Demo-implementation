<script>
	import { tick, onMount } from 'svelte';
	import { authFetch } from './auth.js';

	const REPORT_URL_PATTERN = /(\/reports\/[A-Za-z0-9_\-.]+\.pdf)/;

	let messages = [
		{
			sender: 'bot',
			text: 'Hi — I can look up employees, department headcounts, and leave balances. Try asking something like "how many departments are there?"',
		},
	];
	let messageText = '';
	let isThinking = false;
	let inputRef;
	let messagesRef;

	onMount(() => {
		inputRef?.focus();
	});

	function escapeHtml(value) {
		return value
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

	function pushMessage(sender, text) {
		messages = [...messages, { sender, text }];
	}

	async function scrollToBottom() {
		await tick();
		if (messagesRef) {
			messagesRef.scrollTop = messagesRef.scrollHeight;
		}
	}

	async function handleSubmit() {
		const text = messageText.trim();
		if (!text || isThinking) return;

		pushMessage('user', text);
		messageText = '';
		isThinking = true;
		await scrollToBottom();

		try {
			const response = await authFetch('/chat', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ message: text }),
			});

			if (!response.ok) {
				const body = await response.json().catch(() => ({}));
				pushMessage('error', body.detail ?? `Something went wrong on the server (${response.status}). Try again.`);
				return;
			}

			const data = await response.json();
			pushMessage('bot', data.assistant ?? "I didn't get a response back. Try rephrasing.");
		} catch (error) {
			pushMessage('error', error instanceof Error ? error.message : String(error));
		} finally {
			isThinking = false;
			await scrollToBottom();
			inputRef?.focus();
		}
	}

	function getReportUrl(text) {
		const match = text.match(REPORT_URL_PATTERN);
		return match?.[1] ?? null;
	}
</script>

<div class="chat-panel">
	<header class="chat-header">
		<div class="chat-brand">
			<span class="chat-mark">PD</span>
			<div>
				<h3>Ask the desk</h3>
				<p>Employees, departments, leave balances, and reports</p>
			</div>
		</div>
		<div class:thinking={isThinking} class="chat-status" aria-hidden="true"></div>
	</header>

	<div class="chat-messages" bind:this={messagesRef} role="log" aria-live="polite">
		{#each messages as message, index (index)}
			{@const reportUrl = message.sender === 'bot' ? getReportUrl(message.text) : null}
			<div class:bot={message.sender === 'bot'} class:error={message.sender === 'error'} class:user={message.sender === 'user'} class="chat-message">
				<div class="chat-label">{message.sender === 'user' ? 'You' : 'Desk'}</div>
				<div class="chat-bubble" class:report={Boolean(reportUrl)}>
					{#if message.sender === 'user'}
						{@html escapeHtml(message.text).replace(/\n/g, '<br>')}
					{:else if reportUrl}
						{@html renderMarkdown(message.text.replace(reportUrl, '').replace(/\s{2,}/g, ' ').trim())}
					{:else}
						{@html renderMarkdown(message.text)}
					{/if}
				</div>

				{#if reportUrl}
					<a class="report-chip" href={reportUrl} download={reportUrl.split('/').pop()}>
						<svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
							<path d="M12 3v12m0 0l-4-4m4 4l4-4M5 21h14" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
						</svg>
						<span>Download report (PDF)</span>
					</a>
				{/if}
			</div>
		{/each}

		{#if isThinking}
			<div class="chat-message bot">
				<div class="chat-label">Desk</div>
				<div class="typing-indicator" aria-hidden="true">
					<span></span><span></span><span></span>
				</div>
			</div>
		{/if}
	</div>

	<form class="chat-form" on:submit|preventDefault={handleSubmit}>
		<input
			bind:this={inputRef}
			bind:value={messageText}
			type="text"
			placeholder="Ask about an employee, department, leave record, or report…"
			autocomplete="off"
			aria-label="Type your question"
		/>
		<button type="submit" disabled={isThinking || !messageText.trim()} aria-label="Send message">
			<svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
				<path d="M3 11.5L21 3L13.5 21L11 13L3 11.5Z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" />
			</svg>
		</button>
	</form>
</div>

<style>
	:global(*) {
		box-sizing: border-box;
	}

	.chat-panel {
		width: min(100%, 720px);
		height: min(76vh, 720px);
		margin: 0 auto;
		background: var(--panel, #fff);
		border: 1px solid var(--border, #e3e7ee);
		border-radius: 16px;
		box-shadow: 0 18px 48px rgba(27, 42, 74, 0.08);
		display: flex;
		flex-direction: column;
		overflow: hidden;
	}

	.chat-header {
		padding: 18px 22px 0;
		border-bottom: 1px solid var(--border, #e3e7ee);
		background: var(--panel, #fff);
	}

	.chat-brand {
		display: flex;
		align-items: center;
		gap: 14px;
		padding-bottom: 16px;
	}

	.chat-mark {
		width: 38px;
		height: 38px;
		border-radius: 8px;
		background: var(--navy, #1b2a4a);
		color: #fff;
		font-family: 'JetBrains Mono', monospace;
		font-size: 13px;
		font-weight: 600;
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
	}

	.chat-brand h3 {
		margin: 0;
		font-size: 18px;
		font-weight: 700;
		color: var(--text-body, #1f2937);
	}

	.chat-brand p {
		margin: 2px 0 0;
		font-size: 12.5px;
		color: var(--text-muted, #6b7280);
	}

	.chat-status {
		height: 2px;
		background: var(--border, #e3e7ee);
		margin: 0 -22px;
		position: relative;
		overflow: hidden;
	}

	.chat-status.thinking::after {
		content: '';
		position: absolute;
		inset: 0;
		width: 40%;
		background: var(--accent, #2f6fed);
		animation: sweep 1.1s ease-in-out infinite;
	}

	@keyframes sweep {
		0% {
			transform: translateX(-100%);
		}
		100% {
			transform: translateX(250%);
		}
	}

	.chat-messages {
		flex: 1;
		min-height: 0;
		padding: 20px 22px;
		display: flex;
		flex-direction: column;
		gap: 16px;
		overflow-y: auto;
	}

	.chat-message {
		display: flex;
		flex-direction: column;
		gap: 4px;
		max-width: 88%;
	}

	.chat-message.user {
		align-self: flex-end;
		align-items: flex-end;
	}

	.chat-message.bot,
	.chat-message.error {
		align-self: flex-start;
	}

	.chat-label {
		font-family: 'JetBrains Mono', monospace;
		font-size: 10.5px;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--text-muted, #6b7280);
		padding: 0 4px;
	}

	.chat-bubble {
		padding: 10px 14px;
		border-radius: 8px;
		font-size: 14.5px;
		line-height: 1.5;
		white-space: pre-wrap;
		word-wrap: break-word;
		color: var(--text-body, #1f2937);
	}

	.chat-message.bot .chat-bubble {
		background: color-mix(in srgb, var(--page-bg, #f4f6f9) 86%, white);
		border-left: 2px solid var(--accent, #2f6fed);
		border-radius: 4px 8px 8px 8px;
	}

	.chat-message.user .chat-bubble {
		background: var(--navy, #1b2a4a);
		color: #fff;
		border-radius: 8px 4px 8px 8px;
	}

	.chat-message.error .chat-bubble {
		background: #fbeaea;
		border-left: 2px solid var(--danger, #e5484d);
		color: #8c2f2f;
	}

	.chat-bubble :global(strong) {
		font-weight: 700;
	}

	.chat-bubble :global(code) {
		font-family: 'JetBrains Mono', monospace;
		font-size: 0.9em;
		background: rgba(0, 0, 0, 0.06);
		padding: 1px 5px;
		border-radius: 4px;
	}

	.chat-bubble :global(a) {
		color: var(--accent, #2f6fed);
		text-decoration: underline;
		text-decoration-color: var(--border, #e3e7ee);
	}

	.chat-bubble :global(a:hover) {
		text-decoration-color: var(--accent, #2f6fed);
	}

	.report-chip {
		display: inline-flex;
		align-items: center;
		gap: 7px;
		margin-top: 2px;
		padding: 8px 14px;
		border-radius: 7px;
		background: var(--navy, #1b2a4a);
		color: #fff;
		font-size: 13px;
		font-weight: 500;
		text-decoration: none;
		transition: background 0.15s ease, transform 0.1s ease;
		width: fit-content;
	}

	.report-chip:hover {
		background: var(--accent, #2f6fed);
	}

	.report-chip:active {
		transform: scale(0.97);
	}

	.typing-indicator {
		padding: 10px 14px;
		width: fit-content;
		background: color-mix(in srgb, var(--page-bg, #f4f6f9) 86%, white);
		border-left: 2px solid var(--accent, #2f6fed);
		border-radius: 4px 8px 8px 8px;
		display: flex;
		gap: 4px;
	}

	.typing-indicator span {
		width: 5px;
		height: 5px;
		border-radius: 50%;
		background: var(--text-muted, #6b7280);
		animation: bounce 1.2s infinite ease-in-out;
	}

	.typing-indicator span:nth-child(2) {
		animation-delay: 0.15s;
	}

	.typing-indicator span:nth-child(3) {
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

	.chat-form {
		display: flex;
		gap: 8px;
		padding: 14px 16px;
		border-top: 1px solid var(--border, #e3e7ee);
		background: var(--panel, #fff);
	}

	.chat-form input {
		flex: 1;
		padding: 11px 14px;
		border: 1px solid var(--border, #e3e7ee);
		border-radius: 8px;
		outline: none;
		font-size: 14.5px;
		font-family: inherit;
		background: var(--page-bg, #f4f6f9);
		color: var(--text-body, #1f2937);
		transition: border-color 0.15s ease, background 0.15s ease;
	}

	.chat-form input:focus {
		border-color: var(--accent, #2f6fed);
		background: var(--panel, #fff);
	}

	.chat-form input::placeholder {
		color: var(--text-muted, #6b7280);
	}

	.chat-form button {
		width: 42px;
		height: 42px;
		flex-shrink: 0;
		border-radius: 8px;
		border: none;
		background: var(--navy, #1b2a4a);
		color: #fff;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: background 0.15s ease, transform 0.1s ease;
	}

	.chat-form button:hover:not(:disabled) {
		background: var(--accent, #2f6fed);
	}

	.chat-form button:active:not(:disabled) {
		transform: scale(0.94);
	}

	.chat-form button:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.chat-form button:focus-visible,
	.chat-form input:focus-visible {
		outline: 2px solid var(--accent, #2f6fed);
		outline-offset: 2px;
	}

	@media (max-width: 700px) {
		.chat-panel {
			height: auto;
			min-height: calc(100vh - 28px);
			border-radius: 14px;
		}

		.chat-message {
			max-width: 100%;
		}
	}
</style>
