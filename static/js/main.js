/* main.js — shared helpers used across pages: a thin fetch() wrapper that
   talks to the /api/* REST endpoints, and a small toast notifier. */

async function apiRequest(url, options = {}) {
  const opts = {
    method: options.method || "GET",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin", // send the session cookie
  };
  if (options.body) opts.body = JSON.stringify(options.body);

  const res = await fetch(url, opts);
  let data = null;
  try {
    data = await res.json();
  } catch (e) {
    data = null;
  }
  if (!res.ok) {
    const message = (data && data.error) || `Request failed (${res.status})`;
    throw new Error(message);
  }
  return data;
}

function showToast(message, type = "success") {
  const container = document.getElementById("toast-container");
  if (!container) return;
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}

function formatDateForInputMin() {
  const d = new Date();
  return d.toISOString().split("T")[0];
}
