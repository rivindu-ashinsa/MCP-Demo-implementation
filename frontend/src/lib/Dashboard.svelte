<script>
  import { onMount } from 'svelte';
  import { auth, authFetch, logout } from './auth.js';
  import ChatPanel from './ChatPanel.svelte';

  let me = null;
  auth.subscribe((v) => (me = v));

  let view = 'overview'; // 'overview' | 'employees' | 'chat'
  let employees = [];
  let headcounts = {};
  let isLoading = true;
  let loadError = '';

  const isHr = () => me?.role === 'hr';

  async function loadData() {
    isLoading = true;
    loadError = '';
    try {
      const empRes = await authFetch('/api/employees');
      if (empRes.ok) {
        employees = await empRes.json();
      } else {
        const body = await empRes.json().catch(() => ({}));
        loadError = body.detail ?? `Couldn't load employee data (${empRes.status}).`;
      }

      if (isHr()) {
        const hcRes = await authFetch('/api/departments/headcounts');
        if (hcRes.ok) headcounts = await hcRes.json();
      }
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    } finally {
      isLoading = false;
    }
  }

  onMount(loadData);

  let showAddForm = false;
  let newName = '';
  let newDepartment = '';
  let newLeaveBalance = 0;
  let isCreating = false;
  let createError = '';
  let lastCreatedLogin = null;

  let editingId = null;
  let editValue = 0;
  let rowBusyId = null;
  let rowError = {};

  function startEdit(emp) {
    editingId = emp.id;
    editValue = emp.leave_balance;
    rowError = { ...rowError, [emp.id]: undefined };
  }

  function cancelEdit() {
    editingId = null;
  }

  async function saveEdit(emp) {
    rowBusyId = emp.id;
    rowError = { ...rowError, [emp.id]: undefined };

    try {
      const res = await authFetch(`/api/employees/${emp.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ leave_balance: Number(editValue) || 0 }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        rowError = { ...rowError, [emp.id]: body.detail ?? `Couldn't save (${res.status}).` };
        return;
      }

      editingId = null;
      await loadData();
    } catch (e) {
      rowError = { ...rowError, [emp.id]: e instanceof Error ? e.message : String(e) };
    } finally {
      rowBusyId = null;
    }
  }

  async function removeEmployee(emp) {
    if (!confirm(`Remove ${emp.name}? This also deletes their login. This can't be undone.`)) return;

    rowBusyId = emp.id;
    rowError = { ...rowError, [emp.id]: undefined };

    try {
      const res = await authFetch(`/api/employees/${emp.id}`, { method: 'DELETE' });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        rowError = { ...rowError, [emp.id]: body.detail ?? `Couldn't remove (${res.status}).` };
        return;
      }

      await loadData();
    } catch (e) {
      rowError = { ...rowError, [emp.id]: e instanceof Error ? e.message : String(e) };
    } finally {
      rowBusyId = null;
    }
  }

  async function submitNewEmployee() {
    const name = newName.trim();
    if (!name || isCreating) return;

    isCreating = true;
    createError = '';
    lastCreatedLogin = null;

    try {
      const res = await authFetch('/api/employees', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name,
          department: newDepartment.trim() || null,
          leave_balance: Number(newLeaveBalance) || 0,
        }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        createError = body.detail ?? `Couldn't add employee (${res.status}).`;
        return;
      }

      const created = await res.json();
      lastCreatedLogin = created.generated_login;
      newName = '';
      newDepartment = '';
      newLeaveBalance = 0;
      showAddForm = false;
      await loadData();
    } catch (e) {
      createError = e instanceof Error ? e.message : String(e);
    } finally {
      isCreating = false;
    }
  }

  $: totalEmployees = employees.length;
  $: avgLeave = employees.length
    ? Math.round((employees.reduce((sum, e) => sum + e.leave_balance, 0) / employees.length) * 10) / 10
    : 0;
  $: lowLeaveCount = employees.filter((e) => e.leave_balance <= 2).length;
</script>

<div id="dash-shell">
  <aside id="dash-rail">
    <div id="dash-brand">
      <span id="brand-mark">PD</span>
      <div>
        <h1>Personnel Desk</h1>
        <p>{me?.companyName ?? ''}</p>
      </div>
    </div>

    <nav id="dash-nav">
      <button class:active={view === 'overview'} on:click={() => (view = 'overview')}>
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none"><path d="M4 13h6V4H4v9zM4 20h6v-4H4v4zM14 20h6v-9h-6v9zM14 4v4h6V4h-6z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/></svg>
        <span>Overview</span>
      </button>
      <button class:active={view === 'employees'} on:click={() => (view = 'employees')}>
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none"><path d="M17 20v-2a4 4 0 00-4-4H7a4 4 0 00-4 4v2M10 10a4 4 0 100-8 4 4 0 000 8zM23 20v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>
        <span>{isHr() ? 'Employees' : 'My record'}</span>
      </button>
      <button class:active={view === 'chat'} on:click={() => (view = 'chat')}>
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none"><path d="M4 5h16v11H8l-4 4V5z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/></svg>
        <span>Ask the desk</span>
      </button>
    </nav>

    <div id="dash-user">
      <div id="dash-user-info">
        <span id="dash-user-name">{me?.username}</span>
        <span id="dash-user-role">{isHr() ? 'HR manager' : 'Employee'}</span>
      </div>
      <button id="logout-btn" on:click={logout} aria-label="Log out">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none"><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
      </button>
    </div>
  </aside>

  <main id="dash-main">
    <header id="dash-header">
      <h2>
        {#if view === 'overview'}Overview
        {:else if view === 'employees'}{isHr() ? 'Employees' : 'My record'}
        {:else}Ask the desk{/if}
      </h2>
      <span id="dash-date">{new Date().toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</span>
    </header>

    {#if loadError}
      <div class="banner-error">{loadError}</div>
    {/if}

    {#if view === 'overview'}
      <div id="stat-cards">
        <div class="stat-card">
          <span class="stat-label">{isHr() ? 'Total employees' : 'Your leave balance'}</span>
          <span class="stat-value">{isHr() ? totalEmployees : (employees[0]?.leave_balance ?? '—')}</span>
        </div>
        {#if isHr()}
          <div class="stat-card">
            <span class="stat-label">Average leave balance</span>
            <span class="stat-value">{avgLeave}</span>
          </div>
          <div class="stat-card" class:warn={lowLeaveCount > 0}>
            <span class="stat-label">Running low (≤2 days)</span>
            <span class="stat-value">{lowLeaveCount}</span>
          </div>
        {/if}
      </div>

      {#if isHr() && Object.keys(headcounts).length}
        <div class="panel">
          <h3>Department headcounts</h3>
          <div id="headcount-bars">
            {#each Object.entries(headcounts) as [dept, count]}
              <div class="hc-row">
                <span class="hc-label">{dept}</span>
                <div class="hc-track">
                  <div class="hc-fill" style={`width: ${Math.min(100, (count / totalEmployees) * 100)}%`}></div>
                </div>
                <span class="hc-count">{count}</span>
              </div>
            {/each}
          </div>
        </div>
      {/if}

      {#if !isHr() && employees.length}
        <div class="panel">
          <h3>Your details</h3>
          <dl class="detail-grid">
            <dt>Name</dt><dd>{employees[0].name}</dd>
            <dt>Department</dt><dd>{employees[0].department}</dd>
            <dt>Leave balance</dt><dd>{employees[0].leave_balance} days</dd>
          </dl>
        </div>
      {/if}
    {:else if view === 'employees'}
      {#if isLoading}
        <p class="muted">Loading…</p>
      {:else if isHr()}
        {#if lastCreatedLogin}
          <div class="banner-success">
            Added — login created: <strong>{lastCreatedLogin.username}</strong> / <strong>{lastCreatedLogin.password}</strong>. Pass these along to the new hire.
          </div>
        {/if}

        <div class="panel">
          <div class="panel-header-row">
            <h3>All employees</h3>
            <button class="add-btn" on:click={() => (showAddForm = !showAddForm)}>
              {showAddForm ? 'Cancel' : '+ Add employee'}
            </button>
          </div>

          {#if showAddForm}
            <form id="add-employee-form" on:submit|preventDefault={submitNewEmployee}>
              <label>
                <span>Name</span>
                <input type="text" bind:value={newName} placeholder="Full name" required />
              </label>
              <label>
                <span>Department</span>
                <input type="text" bind:value={newDepartment} placeholder="e.g. Engineering" />
              </label>
              <label>
                <span>Starting leave balance</span>
                <input type="number" min="0" bind:value={newLeaveBalance} />
              </label>
              <button type="submit" disabled={isCreating || !newName.trim()}>
                {isCreating ? 'Adding…' : 'Add employee'}
              </button>
              {#if createError}
                <p class="form-error">{createError}</p>
              {/if}
            </form>
          {/if}

          <table id="employee-table">
            <thead>
              <tr><th>Name</th><th>Department</th><th>Leave balance</th><th></th></tr>
            </thead>
            <tbody>
              {#each employees as emp (emp.id)}
                <tr>
                  <td>{emp.name}</td>
                  <td><span class="dept-pill">{emp.department}</span></td>
                  <td>
                    {#if editingId === emp.id}
                      <input class="edit-balance-input" type="number" min="0" bind:value={editValue} />
                    {:else}
                      <span class="leave-pill" class:low={emp.leave_balance <= 2}>{emp.leave_balance} days</span>
                    {/if}
                  </td>
                  <td class="row-actions">
                    {#if editingId === emp.id}
                      <button class="row-btn save" on:click={() => saveEdit(emp)} disabled={rowBusyId === emp.id}>
                        {rowBusyId === emp.id ? 'Saving…' : 'Save'}
                      </button>
                      <button class="row-btn" on:click={cancelEdit}>Cancel</button>
                    {:else}
                      <button class="row-btn" on:click={() => startEdit(emp)}>Edit</button>
                      <button class="row-btn danger" on:click={() => removeEmployee(emp)} disabled={rowBusyId === emp.id}>
                        {rowBusyId === emp.id ? 'Removing…' : 'Delete'}
                      </button>
                    {/if}
                  </td>
                </tr>
                {#if rowError[emp.id]}
                  <tr class="row-error-line">
                    <td colspan="4">{rowError[emp.id]}</td>
                  </tr>
                {/if}
              {/each}
            </tbody>
          </table>
        </div>
      {:else if employees.length}
        <div class="panel">
          <dl class="detail-grid">
            <dt>Name</dt><dd>{employees[0].name}</dd>
            <dt>Department</dt><dd>{employees[0].department}</dd>
            <dt>Leave balance</dt><dd>{employees[0].leave_balance} days</dd>
          </dl>
        </div>
      {/if}
    {:else}
      <div id="chat-wrap">
        <ChatPanel />
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

  :global(body) {
    margin: 0;
    font-family: 'Inter', system-ui, sans-serif;
    background: var(--page-bg);
  }

  :global(:root) {
    --navy: #1b2a4a;
    --navy-light: #26314f;
    --page-bg: #f4f6f9;
    --panel: #ffffff;
    --accent: #2f6fed;
    --green: #22a06b;
    --amber: #f0a63a;
    --danger: #e5484d;
    --border: #e3e7ee;
    --text-body: #1f2937;
    --text-muted: #6b7280;
  }

  #dash-shell {
    display: flex;
    min-height: 100vh;
  }

  #dash-rail {
    width: 232px;
    flex-shrink: 0;
    background: var(--navy);
    color: #cfd7e6;
    display: flex;
    flex-direction: column;
    padding: 18px 14px;
  }

  #dash-brand {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 4px 6px 20px;
  }

  #brand-mark {
    width: 34px;
    height: 34px;
    border-radius: 8px;
    background: var(--accent);
    color: #fff;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  #dash-brand h1 {
    font-size: 14.5px;
    font-weight: 700;
    color: #fff;
    margin: 0;
  }

  #dash-brand p {
    font-size: 11px;
    margin: 2px 0 0;
    color: #93a1c2;
  }

  #dash-nav {
    display: flex;
    flex-direction: column;
    gap: 3px;
  }

  #dash-nav button {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 12px;
    border: none;
    background: transparent;
    border-radius: 8px;
    color: #a9b4cc;
    font-size: 13.5px;
    font-weight: 500;
    cursor: pointer;
    text-align: left;
  }

  #dash-nav button:hover {
    background: var(--navy-light);
    color: #fff;
  }

  #dash-nav button.active {
    background: var(--navy-light);
    color: #fff;
    box-shadow: 3px 0 0 var(--accent) inset;
  }

  #dash-user {
    margin-top: auto;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 10px 4px;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
  }

  #dash-user-info {
    display: flex;
    flex-direction: column;
  }

  #dash-user-name {
    font-size: 13px;
    color: #fff;
    font-weight: 600;
  }

  #dash-user-role {
    font-size: 11px;
    color: #93a1c2;
  }

  #logout-btn {
    background: transparent;
    border: none;
    color: #93a1c2;
    cursor: pointer;
    padding: 6px;
    border-radius: 6px;
  }

  #logout-btn:hover {
    color: #fff;
    background: var(--navy-light);
  }

  #dash-main {
    flex: 1;
    padding: 26px 32px;
    overflow-y: auto;
    min-width: 0;
  }

  #dash-header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    margin-bottom: 20px;
  }

  #dash-header h2 {
    font-size: 22px;
    font-weight: 700;
    margin: 0;
    color: var(--text-body);
  }

  #dash-date {
    font-size: 12.5px;
    color: var(--text-muted);
  }

  .banner-error {
    padding: 11px 14px;
    border-radius: 8px;
    background: #fbeaea;
    border-left: 3px solid var(--danger);
    color: #8c2f2f;
    font-size: 13px;
    margin-bottom: 18px;
  }

  #stat-cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 14px;
    margin-bottom: 22px;
  }

  .stat-card {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 16px 18px;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .stat-card.warn {
    border-color: var(--amber);
  }

  .stat-label {
    font-size: 12px;
    color: var(--text-muted);
    font-weight: 500;
  }

  .stat-value {
    font-size: 26px;
    font-weight: 700;
    color: var(--text-body);
  }

  .panel {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 18px 20px;
    margin-bottom: 18px;
  }

  .panel h3 {
    font-size: 14px;
    font-weight: 700;
    margin: 0 0 14px;
    color: var(--text-body);
  }

  .panel-header-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 14px;
  }

  .panel-header-row h3 {
    margin: 0;
  }

  .add-btn {
    padding: 7px 13px;
    border-radius: 7px;
    border: none;
    background: var(--accent);
    color: #fff;
    font-size: 12.5px;
    font-weight: 600;
    cursor: pointer;
  }

  .add-btn:hover {
    background: #2559c9;
  }

  #add-employee-form {
    display: grid;
    grid-template-columns: 1fr 1fr 140px auto;
    gap: 10px;
    align-items: end;
    padding: 14px;
    margin-bottom: 16px;
    background: var(--page-bg);
    border-radius: 9px;
    border: 1px solid var(--border);
  }

  #add-employee-form label {
    display: flex;
    flex-direction: column;
    gap: 5px;
    font-size: 11.5px;
    color: var(--text-muted);
    font-weight: 600;
  }

  #add-employee-form input {
    font-family: inherit;
    font-size: 13px;
    padding: 8px 10px;
    border-radius: 6px;
    border: 1px solid var(--border);
    background: var(--panel);
    outline: none;
  }

  #add-employee-form input:focus {
    border-color: var(--accent);
  }

  #add-employee-form button[type='submit'] {
    padding: 9px 14px;
    border-radius: 7px;
    border: none;
    background: var(--navy);
    color: #fff;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    height: fit-content;
  }

  #add-employee-form button[type='submit']:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }

  .form-error {
    grid-column: 1 / -1;
    margin: 0;
    font-size: 12px;
    color: var(--danger);
  }

  .banner-success {
    padding: 11px 14px;
    border-radius: 8px;
    background: #e6f4ee;
    border-left: 3px solid var(--green);
    color: #1c6b47;
    font-size: 13px;
    margin-bottom: 18px;
  }

  #headcount-bars {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .hc-row {
    display: grid;
    grid-template-columns: 100px 1fr 30px;
    align-items: center;
    gap: 10px;
  }

  .hc-label {
    font-size: 12.5px;
    color: var(--text-body);
  }

  .hc-track {
    height: 8px;
    border-radius: 4px;
    background: var(--page-bg);
    overflow: hidden;
  }

  .hc-fill {
    height: 100%;
    background: var(--accent);
    border-radius: 4px;
  }

  .hc-count {
    font-size: 12px;
    color: var(--text-muted);
    text-align: right;
  }

  .detail-grid {
    display: grid;
    grid-template-columns: 140px 1fr;
    row-gap: 10px;
    margin: 0;
  }

  .detail-grid dt {
    font-size: 12.5px;
    color: var(--text-muted);
    font-weight: 500;
  }

  .detail-grid dd {
    margin: 0;
    font-size: 14px;
    color: var(--text-body);
    font-weight: 600;
  }

  #employee-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13.5px;
  }

  #employee-table th {
    text-align: left;
    font-size: 11.5px;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: var(--text-muted);
    padding: 0 10px 10px;
    border-bottom: 1px solid var(--border);
  }

  #employee-table td {
    padding: 12px 10px;
    border-bottom: 1px solid var(--border);
    color: var(--text-body);
  }

  #employee-table tr:last-child td {
    border-bottom: none;
  }

  .dept-pill {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    background: var(--page-bg);
    font-size: 12px;
    color: var(--text-body);
  }

  .leave-pill {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    background: #e6f4ee;
    color: var(--green);
    font-size: 12px;
    font-weight: 600;
  }

  .leave-pill.low {
    background: #fdeee0;
    color: var(--amber);
  }

  .edit-balance-input {
    width: 70px;
    padding: 5px 8px;
    border-radius: 6px;
    border: 1px solid var(--accent);
    font-family: inherit;
    font-size: 12.5px;
    outline: none;
  }

  .row-actions {
    display: flex;
    gap: 6px;
    justify-content: flex-end;
    white-space: nowrap;
  }

  .row-btn {
    padding: 5px 10px;
    border-radius: 6px;
    border: 1px solid var(--border);
    background: var(--panel);
    color: var(--text-body);
    font-size: 11.5px;
    font-weight: 600;
    cursor: pointer;
  }

  .row-btn:hover:not(:disabled) {
    border-color: var(--accent);
    color: var(--accent);
  }

  .row-btn.save {
    background: var(--accent);
    border-color: var(--accent);
    color: #fff;
  }

  .row-btn.danger:hover:not(:disabled) {
    border-color: var(--danger);
    color: var(--danger);
  }

  .row-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .row-error-line td {
    padding: 4px 10px 10px;
    border-bottom: 1px solid var(--border);
    font-size: 11.5px;
    color: var(--danger);
  }

  .muted {
    color: var(--text-muted);
    font-size: 13.5px;
  }

  #chat-wrap {
    height: calc(100vh - 140px);
  }

  @media (max-width: 780px) {
    #dash-shell {
      flex-direction: column;
    }

    #dash-rail {
      width: 100%;
      flex-direction: row;
      align-items: center;
      gap: 14px;
      padding: 12px 16px;
    }

    #dash-brand p {
      display: none;
    }

    #dash-nav {
      flex-direction: row;
    }

    #dash-nav button span {
      display: none;
    }

    #dash-user {
      margin-top: 0;
      margin-left: auto;
      border-top: none;
      padding: 0;
    }

    #dash-main {
      padding: 20px 16px;
    }

    #chat-wrap {
      height: calc(100vh - 220px);
    }

    #add-employee-form {
      grid-template-columns: 1fr;
    }
  }
</style>