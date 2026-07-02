<script>
  import { login } from './auth.js';

  let companyCode = '';
  let username = '';
  let password = '';
  let error = '';
  let isSubmitting = false;

  async function handleSubmit() {
    if (isSubmitting) return;
    error = '';
    isSubmitting = true;
    try {
      await login(companyCode.trim(), username.trim(), password);
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    } finally {
      isSubmitting = false;
    }
  }
</script>

<div id="login-screen">
  <div id="login-card">
    <div id="login-brand">
      <span id="brand-mark">PD</span>
      <div>
        <h1>Personnel Desk</h1>
        <p>Sign in to your company workspace</p>
      </div>
    </div>

    <form on:submit|preventDefault={handleSubmit}>
      <label>
        <span>Company code</span>
        <input type="text" bind:value={companyCode} placeholder="e.g. acme" autocomplete="organization" required />
      </label>

      <label>
        <span>Username</span>
        <input type="text" bind:value={username} placeholder="your username" autocomplete="username" required />
      </label>

      <label>
        <span>Password</span>
        <input type="password" bind:value={password} placeholder="••••••••" autocomplete="current-password" required />
      </label>

      {#if error}
        <p class="login-error">{error}</p>
      {/if}

      <button type="submit" disabled={isSubmitting}>
        {isSubmitting ? 'Signing in…' : 'Sign in'}
      </button>
    </form>

    <p id="login-hint">Don't know your company code or login? Ask your HR manager.</p>
  </div>
</div>

<style>
  :global(*),
  :global(*::before),
  :global(*::after) {
    box-sizing: border-box;
  }

  :global(body) {
    margin: 0;
    font-family: 'Inter', system-ui, sans-serif;
  }

  :global(:root) {
    --navy: #1b2a4a;
    --navy-light: #26314f;
    --page-bg: #f4f6f9;
    --panel: #ffffff;
    --accent: #2f6fed;
    --border: #e3e7ee;
    --text-body: #1f2937;
    --text-muted: #6b7280;
    --danger: #e5484d;
  }

  #login-screen {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(160deg, var(--navy) 0%, var(--navy) 42%, var(--page-bg) 42%);
    padding: 24px;
  }

  #login-card {
    width: 100%;
    max-width: 380px;
    background: var(--panel);
    border-radius: 14px;
    box-shadow: 0 24px 60px rgba(27, 42, 74, 0.25);
    padding: 32px 30px 26px;
  }

  #login-brand {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 26px;
  }

  #brand-mark {
    width: 40px;
    height: 40px;
    border-radius: 9px;
    background: var(--navy);
    color: #fff;
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    font-weight: 600;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  #login-brand h1 {
    font-size: 18px;
    font-weight: 700;
    margin: 0;
    color: var(--text-body);
  }

  #login-brand p {
    font-size: 12.5px;
    color: var(--text-muted);
    margin: 2px 0 0;
  }

  form {
    display: flex;
    flex-direction: column;
    gap: 15px;
  }

  label {
    display: flex;
    flex-direction: column;
    gap: 6px;
    font-size: 12.5px;
    font-weight: 600;
    color: var(--text-muted);
  }

  input {
    font-family: inherit;
    font-size: 14px;
    padding: 10px 12px;
    border-radius: 8px;
    border: 1px solid var(--border);
    background: var(--page-bg);
    color: var(--text-body);
    outline: none;
    transition: border-color 0.15s ease, background 0.15s ease;
  }

  input:focus {
    border-color: var(--accent);
    background: var(--panel);
  }

  .login-error {
    margin: 0;
    padding: 9px 11px;
    border-radius: 7px;
    background: #fbeaea;
    border-left: 3px solid var(--danger);
    color: #8c2f2f;
    font-size: 12.5px;
  }

  button[type='submit'] {
    margin-top: 4px;
    padding: 11px 14px;
    border-radius: 9px;
    border: none;
    background: var(--accent);
    color: #fff;
    font-size: 14.5px;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.15s ease, transform 0.1s ease;
  }

  button[type='submit']:hover:not(:disabled) {
    background: #2559c9;
  }

  button[type='submit']:active:not(:disabled) {
    transform: scale(0.98);
  }

  button[type='submit']:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  #login-hint {
    margin: 20px 0 0;
    text-align: center;
    font-size: 12px;
    color: var(--text-muted);
  }
</style>