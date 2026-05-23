// Unified AI Portal — shared JS utilities

const API_BASE = 'https://lively-vibrancy-production-af74.up.railway.app';
const API = API_BASE;

function toggleAgent(slug) {
  const el = document.getElementById(`agent-${slug}`);
  if (el) el.classList.toggle('open');
}

function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('collapsed');
}

// Mark active nav item based on current path
function markActiveNav() {
  const path = window.location.pathname;
  document.querySelectorAll('[data-page]').forEach(el => el.classList.remove('active'));

  if (path.includes('/cur/chat')) {
    document.querySelector('[data-page="cur-chat"]')?.classList.add('active');
    openAgent('cur');
  } else if (path.includes('/cur/dashboard')) {
    document.querySelector('[data-page="cur-dashboard"]')?.classList.add('active');
    openAgent('cur');
  } else if (path.includes('/cur/reports')) {
    document.querySelector('[data-page="cur-reports"]')?.classList.add('active');
    openAgent('cur');
  } else if (path.includes('/cur/settings')) {
    document.querySelector('[data-page="cur-settings"]')?.classList.add('active');
    openAgent('cur');
  } else if (path.includes('/alerts/chat')) {
    document.querySelector('[data-page="alerts-chat"]')?.classList.add('active');
    openAgent('alerts');
  } else if (path.includes('/alerts/dashboard')) {
    document.querySelector('[data-page="alerts-dashboard"]')?.classList.add('active');
    openAgent('alerts');
  } else if (path.includes('/alerts/reports')) {
    document.querySelector('[data-page="alerts-reports"]')?.classList.add('active');
    openAgent('alerts');
  } else if (path.includes('/alerts/settings')) {
    document.querySelector('[data-page="alerts-settings"]')?.classList.add('active');
    openAgent('alerts');
  } else if (path.includes('/admin')) {
    document.querySelector('[data-page="admin"]')?.classList.add('active');
  } else {
    document.querySelector('[data-page="home"]')?.classList.add('active');
  }
}

function openAgent(slug) {
  const el = document.getElementById(`agent-${slug}`);
  if (el) el.classList.add('open');
}

// Toast notifications
function showToast(msg, type = 'default') {
  let toast = document.getElementById('toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'toast';
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.className = `show ${type}`;
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => { toast.className = ''; }, 3000);
}

// Format currency
function formatUSD(n) {
  if (n === null || n === undefined) return '$0.00';
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n);
}

// Format date
function formatDate(dt) {
  if (!dt) return '—';
  return new Date(dt).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
}

function formatDateTime(dt) {
  if (!dt) return '—';
  return new Date(dt).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function timeAgo(dt) {
  if (!dt) return '—';
  const diff = (Date.now() - new Date(dt)) / 1000;
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

// Priority badge
function priorityBadge(p) {
  const cls = { P1: 'badge-p1', P2: 'badge-p2', P3: 'badge-p3', P4: 'badge-p4' };
  return `<span class="badge ${cls[p] || 'badge-p4'}">${p}</span>`;
}

// Noise/genuine badge
function classificationBadge(isNoise) {
  return isNoise
    ? '<span class="badge badge-noise">Noise</span>'
    : '<span class="badge badge-genuine">Genuine</span>';
}

// Status badge
function statusBadge(s) {
  const cls = { open: 'badge-open', closed: 'badge-closed', ready: 'badge-ready', acknowledged: 'badge-genuine' };
  return `<span class="badge ${cls[s] || 'badge-closed'}">${s}</span>`;
}

// Chart colours
const CHART_COLORS = [
  '#4F8EF7', '#DC3545', '#22c55e', '#f97316', '#a855f7',
  '#06b6d4', '#eab308', '#ec4899', '#14b8a6', '#f43f5e',
];

// Generic loading spinner HTML
function spinnerHTML() {
  return `<div class="loading"><div class="loading-spinner"></div></div>`;
}

function emptyHTML(icon, title, sub) {
  return `<div class="empty-state"><div class="empty-icon">${icon}</div><div class="empty-title">${title}</div><div class="empty-sub">${sub}</div></div>`;
}

// Render inline chart from chat chart_data
function renderChatChart(containerId, chartData) {
  const canvas = document.createElement('canvas');
  canvas.style.maxHeight = '200px';
  const container = document.getElementById(containerId);
  if (!container) return;
  container.innerHTML = '';
  container.appendChild(canvas);
  new Chart(canvas, {
    type: chartData.type || 'bar',
    data: {
      labels: chartData.labels || [],
      datasets: (chartData.datasets || []).map((ds, i) => ({
        ...ds,
        backgroundColor: ds.backgroundColor || CHART_COLORS[i % CHART_COLORS.length],
        borderColor: ds.borderColor || CHART_COLORS[i % CHART_COLORS.length],
        borderWidth: 2,
        tension: 0.4,
        fill: false,
      })),
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: true } },
    },
  });
}

// Init
document.addEventListener('DOMContentLoaded', () => {
  markActiveNav();
  const toggleBtn = document.getElementById('sidebarToggle');
  if (toggleBtn) toggleBtn.addEventListener('click', toggleSidebar);
});
