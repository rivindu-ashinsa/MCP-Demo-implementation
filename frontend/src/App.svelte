<svelte:head>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous" />
  <link
    href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap"
    rel="stylesheet"
  />
</svelte:head>

<script>
  import { auth } from './lib/auth.js';
  import Login from './lib/Login.svelte';
  import Register from './lib/Register.svelte';
  import Dashboard from './lib/Dashboard.svelte';

  let session = null;
  auth.subscribe((v) => (session = v));

  let view = 'login'; // 'login' | 'register' — only relevant while logged out
</script>

{#if session?.token}
  <Dashboard />
{:else if view === 'register'}
  <Register onSwitchToLogin={() => (view = 'login')} />
{:else}
  <Login onSwitchToRegister={() => (view = 'register')} />
{/if}