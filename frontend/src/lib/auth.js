import { writable } from 'svelte/store';

const STORAGE_KEY = 'pd_auth';

function loadStored() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export const auth = writable(loadStored()); // { token, role, username, companyName, employeeId } | null

auth.subscribe((value) => {
  if (value) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
  } else {
    localStorage.removeItem(STORAGE_KEY);
  }
});

export async function login(companyCode, username, password) {
  const response = await fetch('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ company_code: companyCode, username, password }),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? `Login failed (${response.status})`);
  }

  const data = await response.json();
  auth.set({
    token: data.access_token,
    role: data.role,
    username: data.username,
    companyName: data.company_name,
    employeeId: data.employee_id,
  });
  return data;
}

export function logout() {
  auth.set(null);
}

/** fetch() wrapper that attaches the bearer token and logs the user out on 401. */
export async function authFetch(url, options = {}) {
  let current;
  auth.subscribe((v) => (current = v))();

  const headers = { ...(options.headers ?? {}) };
  if (current?.token) headers.Authorization = `Bearer ${current.token}`;

  const response = await fetch(url, { ...options, headers });

  if (response.status === 401) {
    logout();
  }

  return response;
}

export async function register(companyCode, username, password) {
  const response = await fetch('/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ company_code: companyCode, username, password }),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? `Registration failed (${response.status})`);
  }

  const data = await response.json();
  auth.set({
    token: data.access_token,
    role: data.role,
    username: data.username,
    companyName: data.company_name,
    employeeId: data.employee_id,
  });
  return data;
}