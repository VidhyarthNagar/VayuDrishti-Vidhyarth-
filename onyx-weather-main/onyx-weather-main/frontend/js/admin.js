/**
 * Admin Command Center & Moderation Controller
 * Secured with Role-Based Access Control (RBAC) & Session Verification
 */

class AdminPortal {
  constructor() {
    this.pendingReports = [];
    this.auditLogs = [];
    this.token = localStorage.getItem('vayu_admin_token') || sessionStorage.getItem('vayu_admin_token') || '';
    this.init();
  }

  getAuthHeaders() {
    const headers = { 'Content-Type': 'application/json' };
    if (this.token) {
      headers['X-Admin-Token'] = this.token;
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    return headers;
  }

  getSavedApiKeys() {
    try {
      return JSON.parse(localStorage.getItem('vayu_api_keys') || '{}');
    } catch (e) {
      return {};
    }
  }

  async init() {
    this.bindAuthEvents();
    const isAuthed = await this.checkSession();
    if (isAuthed) {
      this.showCommandView();
      await this.fetchModerationQueue();
      await this.fetchAuditLogs();
      await this.loadApiKeys();
      this.bindCommandEvents();
    } else {
      this.showAuthGate();
    }
  }

  async checkSession() {
    if (!this.token) return false;
    try {
      const res = await fetch('/api/admin/verify-session', {
        headers: this.getAuthHeaders()
      });
      if (res.status === 200) {
        return true;
      }
    } catch (e) {
      console.error('Session check failed:', e);
    }
    this.token = '';
    localStorage.removeItem('vayu_admin_token');
    sessionStorage.removeItem('vayu_admin_token');
    return false;
  }

  showAuthGate() {
    const gate = document.getElementById('admin-auth-gate');
    const view = document.getElementById('admin-command-view');
    const controls = document.getElementById('admin-session-controls');
    if (gate) gate.style.display = 'block';
    if (view) view.style.display = 'none';
    if (controls) controls.style.display = 'none';
  }

  showCommandView() {
    const gate = document.getElementById('admin-auth-gate');
    const view = document.getElementById('admin-command-view');
    const controls = document.getElementById('admin-session-controls');
    if (gate) gate.style.display = 'none';
    if (view) view.style.display = 'block';
    if (controls) controls.style.display = 'flex';
  }

  bindAuthEvents() {
    const loginForm = document.getElementById('form-admin-login');
    if (loginForm) {
      loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('login-username').value.trim();
        const password = document.getElementById('login-password').value.trim();
        const alertBox = document.getElementById('login-error-alert');
        const submitBtn = document.getElementById('btn-submit-login');

        if (submitBtn) {
          submitBtn.disabled = true;
          submitBtn.innerText = 'Verifying Passcode...';
        }
        if (alertBox) alertBox.style.display = 'none';

        try {
          const res = await fetch('/api/admin/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
          });
          const data = await res.json();

          if (res.ok && data.success) {
            this.token = data.token;
            localStorage.setItem('vayu_admin_token', data.token);
            sessionStorage.setItem('vayu_admin_token', data.token);
            this.showToast('✓ Authentication Successful. Command Access Granted.');
            this.showCommandView();
            await this.fetchModerationQueue();
            await this.fetchAuditLogs();
            await this.loadApiKeys();
            this.bindCommandEvents();
          } else {
            if (alertBox) {
              alertBox.innerText = data.detail || 'Access Denied: Invalid passcode.';
              alertBox.style.display = 'block';
            }
          }
        } catch (err) {
          if (alertBox) {
            alertBox.innerText = 'Authentication error. Please retry.';
            alertBox.style.display = 'block';
          }
        } finally {
          if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerText = '🛡️ Authorize & Enter Command Center';
          }
        }
      });
    }

    const logoutBtn = document.getElementById('btn-admin-logout');
    if (logoutBtn) {
      logoutBtn.addEventListener('click', () => {
        this.token = '';
        localStorage.removeItem('vayu_admin_token');
        sessionStorage.removeItem('vayu_admin_token');
        this.showToast('🔒 Operator logged out.');
        this.showAuthGate();
      });
    }
  }

  async fetchModerationQueue() {
    try {
      // Fetch flagged/under_review reports AND all citizen-submitted reports for admin oversight
      const [flaggedRes, citizenRes] = await Promise.all([
        fetch('/api/reports?status=under_review,fake_misleading&limit=50', { headers: this.getAuthHeaders() }),
        fetch('/api/reports?source=Citizen%20Report&status=citizen_corroborated,verified_ai,under_review,fake_misleading&limit=50', { headers: this.getAuthHeaders() })
      ]);
      const flaggedData = await flaggedRes.json();
      const citizenData = await citizenRes.json();

      // Merge and deduplicate by ID, flagged ones first
      const seen = new Set();
      const allReports = [];
      for (const r of [...(flaggedData.reports || []), ...(citizenData.reports || [])]) {
        if (!seen.has(r.id)) {
          seen.add(r.id);
          allReports.push(r);
        }
      }
      // Sort: highest fake probability first
      allReports.sort((a, b) => (b.fake_probability || 0) - (a.fake_probability || 0));
      this.pendingReports = allReports;
      this.renderQueue();
    } catch (e) {
      console.error('Error fetching queue:', e);
    }
  }

  async fetchAuditLogs() {
    try {
      const res = await fetch('/api/admin/moderation-logs?limit=25', {
        headers: this.getAuthHeaders()
      });
      if (res.status === 401) {
        this.showAuthGate();
        return;
      }
      const data = await res.json();
      this.auditLogs = data.logs || [];
      this.renderAuditLogs();
    } catch (e) {
      console.error('Error fetching audit logs:', e);
    }
  }

  async loadApiKeys() {
    // 1. Restore cached keys from localStorage immediately
    const cached = this.getSavedApiKeys();
    if (cached.OPENWEATHER_API_KEY) {
      document.getElementById('input-openweather-key').value = cached.OPENWEATHER_API_KEY;
      document.getElementById('text-openweather-status').innerText = 'Connected';
      document.getElementById('text-openweather-status').style.color = 'var(--accent-emerald)';
    }
    if (cached.NEWS_API_KEY) {
      document.getElementById('input-newsapi-key').value = cached.NEWS_API_KEY;
      document.getElementById('text-newsapi-status').innerText = 'Connected';
      document.getElementById('text-newsapi-status').style.color = 'var(--accent-emerald)';
    }
    if (cached.WEATHERAPI_KEY) {
      document.getElementById('input-weatherapi-key').value = cached.WEATHERAPI_KEY;
    }
    if (cached.GNEWS_API_KEY) {
      document.getElementById('input-gnews-key').value = cached.GNEWS_API_KEY;
    }

    // 2. Fetch configured keys from server
    try {
      const res = await fetch('/api/admin/api-keys', {
        headers: this.getAuthHeaders()
      });
      if (res.status === 401) return;
      const data = await res.json();
      if (data && data.keys) {
        if (data.keys.OPENWEATHER_API_KEY && data.keys.OPENWEATHER_API_KEY !== 'Not Set') {
          if (!document.getElementById('input-openweather-key').value) {
            document.getElementById('input-openweather-key').value = data.keys.OPENWEATHER_API_KEY;
          }
          document.getElementById('text-openweather-status').innerText = 'Connected';
          document.getElementById('text-openweather-status').style.color = 'var(--accent-emerald)';
        }
        if (data.keys.NEWS_API_KEY && data.keys.NEWS_API_KEY !== 'Not Set') {
          if (!document.getElementById('input-newsapi-key').value) {
            document.getElementById('input-newsapi-key').value = data.keys.NEWS_API_KEY;
          }
          document.getElementById('text-newsapi-status').innerText = 'Connected';
          document.getElementById('text-newsapi-status').style.color = 'var(--accent-emerald)';
        }
      }
    } catch (e) {
      console.error('Error loading API keys from server:', e);
    }
  }

  async syncLiveApis() {
    const btn = document.getElementById('btn-sync-live-apis');
    if (btn) {
      btn.disabled = true;
      btn.innerText = '🌐 Fetching Live Internet Streams...';
    }

    const payload = this.getSavedApiKeys();

    try {
      const res = await fetch('/api/admin/sync-live-apis', {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (data.success) {
        const bd = data.breakdown || {};
        let parts = [];
        if (bd.google_news_rss) parts.push(`${bd.google_news_rss} Google News`);
        if (bd.open_meteo_aws) parts.push(`${bd.open_meteo_aws} AWS stations`);
        if (bd.imd_official_rss) parts.push(`${bd.imd_official_rss} IMD Official`);
        if (bd.skymet_rss) parts.push(`${bd.skymet_rss} Skymet`);
        if (bd.ndma_alerts) parts.push(`${bd.ndma_alerts} NDMA alerts`);
        if (bd.reddit_citizen_posts) parts.push(`${bd.reddit_citizen_posts} Reddit posts`);
        if (bd.nasa_eonet_satellites) parts.push(`${bd.nasa_eonet_satellites} NASA EONET`);
        if (bd.gdacs_disaster_alerts) parts.push(`${bd.gdacs_disaster_alerts} GDACS`);
        if (bd.newsapi_articles) parts.push(`${bd.newsapi_articles} NewsAPI`);
        if (bd.openweather_stations) parts.push(`${bd.openweather_stations} OpenWeather`);
        let details = `Ingested ${data.total_synced} real-time reports from ${parts.length} sources: ${parts.join(', ')}.`;

        this.showToast(`✓ Live Sync Complete! ${details}`);
        await this.fetchModerationQueue();
      }
    } catch (e) {
      console.error('Error syncing live APIs:', e);
      this.showToast('Error syncing live feeds.');
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerText = '🔄 Sync Live Internet Data Now';
      }
    }
  }

  renderQueue() {
    const container = document.getElementById('moderation-queue-list');
    if (!container) return;

    if (this.pendingReports.length === 0) {
      container.innerHTML = `
        <div style="text-align: center; padding: 3rem; color: var(--text-muted);">
          <span style="font-size: 2.5rem;">🎉</span>
          <h3 style="margin-top: 0.5rem; color: var(--text-primary);">Moderation Queue is Clean!</h3>
          <p>No suspicious or unverified reports pending administrative review.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = this.pendingReports.map(r => {
      const isFake = r.verification_status === 'fake_misleading';
      const isUnderReview = r.verification_status === 'under_review';
      const isCitizen = r.source === 'Citizen Report';
      const fakePct = Math.round((r.fake_probability || 0) * 100);
      const mlPct = r.ml_fake_probability !== undefined ? Math.round(r.ml_fake_probability * 100) : null;
      const borderColor = isFake ? 'var(--accent-red)' : isCitizen ? '#a855f7' : 'var(--accent-amber)';
      const statusLabel = isFake ? '🚨 FLAGGED FAKE' : isUnderReview ? '⚠️ Under Review' : isCitizen ? '👤 Citizen Report' : '📋 Review';
      const statusColor = isFake ? 'badge-fake' : isUnderReview ? 'badge-review' : 'badge-ai';

      return `
        <div class="glass-panel" style="padding: 1.25rem; margin-bottom: 1rem; border-left: 4px solid ${borderColor};">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.75rem;">
            <div>
              <span class="source-tag" style="${isCitizen ? 'background: rgba(168,85,247,0.15); border-color: #a855f7; color: #a855f7;' : ''}">${r.source}</span>
              <strong style="margin-left: 0.5rem; font-size: 0.95rem;">${r.author_handle || r.author_name}</strong>
              <span style="color: var(--text-muted); font-size: 0.75rem; margin-left: 0.5rem;">📍 ${r.city}, ${r.state} &bull; 🕒 ${new Date(r.timestamp).toLocaleTimeString()}</span>
            </div>
            <div style="display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap;">
              <span style="font-size: 0.75rem; color: ${fakePct > 60 ? '#f87171' : fakePct > 35 ? '#fbbf24' : '#4ade80'}; font-weight: 700;">
                🤖 Fake Score: ${fakePct}%${mlPct !== null ? ` (ML: ${mlPct}%)` : ''}
              </span>
              <span class="card-status-badge ${statusColor}">${statusLabel}</span>
            </div>
          </div>

          <p style="font-size: 0.9rem; margin-bottom: 0.75rem; line-height: 1.45; background: var(--bg-secondary); padding: 0.75rem; border-radius: 6px;">
            "${r.text}"
          </p>

          ${r.media_url ? `
            <div style="margin-bottom: 0.75rem;">
              <img src="${r.media_url}" style="height: 100px; border-radius: 6px; object-fit: cover;" alt="Report Media">
            </div>
          ` : ''}

          <div style="background: rgba(13, 21, 39, 0.6); padding: 0.65rem 0.85rem; border-radius: 6px; margin-bottom: 0.85rem; font-size: 0.8rem; border: 1px solid var(--border-glass);">
            <strong style="color: var(--accent-cyan);">AI Diagnostic Breakdown:</strong>
            <p style="color: var(--text-secondary); margin-top: 0.2rem;">${r.admin_notes || 'Automated NLP credibility evaluation pending.'}</p>
          </div>

          <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem;">
            <div style="font-size: 0.75rem; color: var(--text-muted);">Report ID: <code>${r.id}</code></div>
            <div style="display: flex; gap: 0.5rem;">
              <button class="btn btn-success" style="padding: 0.4rem 0.85rem; font-size: 0.78rem;" onclick="adminPortal.executeAction('${r.id}', 'approve')">
                ✓ Verify & Publish
              </button>
              <button class="btn btn-danger" style="padding: 0.4rem 0.85rem; font-size: 0.78rem;" onclick="adminPortal.executeAction('${r.id}', 'mark_fake')">
                ✗ Mark as Fake / Misinformation
              </button>
              <button class="btn btn-secondary" style="padding: 0.4rem 0.85rem; font-size: 0.78rem;" onclick="adminPortal.executeAction('${r.id}', 'merge_cluster')">
                🔗 Merge Duplicate
              </button>
            </div>
          </div>
        </div>
      `;
    }).join('');
  }

  renderAuditLogs() {
    const tbody = document.getElementById('audit-log-tbody');
    if (!tbody) return;

    tbody.innerHTML = this.auditLogs.map(l => `
      <tr>
        <td><code>${l.report_id}</code></td>
        <td><strong style="color: var(--accent-cyan);">${l.action.toUpperCase()}</strong></td>
        <td>${l.admin_user}</td>
        <td><span style="font-size: 0.75rem; color: var(--text-muted);">${l.previous_status} &rarr; ${l.new_status}</span></td>
        <td>${l.reason || 'Manual Action'}</td>
        <td>${new Date(l.timestamp).toLocaleTimeString()}</td>
      </tr>
    `).join('');
  }

  async executeAction(reportId, action) {
    try {
      const res = await fetch('/api/admin/moderate', {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify({
          report_id: reportId,
          action: action,
          admin_user: 'IMD_SuperAdmin',
          reason: `Action executed via Admin Command Workbench (${action})`
        })
      });
      if (res.status === 401) {
        this.showToast('Session expired. Please re-authenticate.');
        this.showAuthGate();
        return;
      }
      const data = await res.json();
      if (data.success) {
        this.showToast(`Action "${action.toUpperCase()}" applied to report ${reportId}`);
        await this.fetchModerationQueue();
        await this.fetchAuditLogs();
      }
    } catch (e) {
      console.error('Moderation action failed:', e);
    }
  }

  bindCommandEvents() {
    // Live API Sync Button
    const syncBtn = document.getElementById('btn-sync-live-apis');
    if (syncBtn) {
      syncBtn.onclick = () => this.syncLiveApis();
    }

    // API Keys Form
    const apiKeysForm = document.getElementById('form-api-keys');
    if (apiKeysForm) {
      apiKeysForm.onsubmit = async (e) => {
        e.preventDefault();
        const payload = {
          OPENWEATHER_API_KEY: document.getElementById('input-openweather-key').value.trim(),
          NEWS_API_KEY: document.getElementById('input-newsapi-key').value.trim(),
          WEATHERAPI_KEY: document.getElementById('input-weatherapi-key').value.trim(),
          GNEWS_API_KEY: document.getElementById('input-gnews-key').value.trim()
        };
        // Save to browser localStorage so keys are persistent across page refreshes
        localStorage.setItem('vayu_api_keys', JSON.stringify(payload));

        try {
          const res = await fetch('/api/admin/api-keys', {
            method: 'POST',
            headers: this.getAuthHeaders(),
            body: JSON.stringify(payload)
          });
          const data = await res.json();
          if (data.success) {
            this.showToast('💾 API Keys securely saved and active across browser sessions.');
            await this.loadApiKeys();
          }
        } catch (err) {
          console.error('Error saving API keys to server:', err);
          this.showToast('💾 API Keys saved locally in browser.');
        }
      };
    }

    // Change Password Form
    const passForm = document.getElementById('form-change-password');
    if (passForm) {
      passForm.onsubmit = async (e) => {
        e.preventDefault();
        const old_password = document.getElementById('input-current-passcode').value.trim();
        const new_password = document.getElementById('input-new-passcode').value.trim();
        try {
          const res = await fetch('/api/admin/change-password', {
            method: 'POST',
            headers: this.getAuthHeaders(),
            body: JSON.stringify({ old_password, new_password })
          });
          const data = await res.json();
          if (res.ok && data.success) {
            this.showToast('🔑 Admin security passcode updated.');
            passForm.reset();
          } else {
            this.showToast(data.detail || 'Password update failed.');
          }
        } catch (err) {
          console.error('Password change error:', err);
        }
      };
    }

    // CAP Alert Broadcast Form
    const alertForm = document.getElementById('form-cap-alert');
    if (alertForm) {
      alertForm.onsubmit = async (e) => {
        e.preventDefault();
        const payload = {
          title: document.getElementById('alert-title').value,
          event_type: document.getElementById('alert-event-type').value,
          severity: document.getElementById('alert-severity').value,
          state: document.getElementById('alert-state').value,
          districts: [document.getElementById('alert-district').value || 'All Coastal Districts'],
          instructions: document.getElementById('alert-instructions').value,
          valid_hours: parseInt(document.getElementById('alert-valid-hours').value) || 24
        };

        try {
          const res = await fetch('/api/admin/broadcast-alert', {
            method: 'POST',
            headers: this.getAuthHeaders(),
            body: JSON.stringify(payload)
          });
          const data = await res.json();
          if (data.success) {
            this.showToast(`🚨 CAP Emergency Warning Broadcast Issued: ${data.alert_id}`);
            alertForm.reset();
          }
        } catch (err) {
          console.error('Error broadcasting alert:', err);
        }
      };
    }

    // Disaster Scenario Trigger Buttons
    document.querySelectorAll('.btn-scenario').forEach(btn => {
      btn.onclick = async (e) => {
        const scenario = e.currentTarget.dataset.scenario;
        try {
          const res = await fetch('/api/admin/trigger-scenario', {
            method: 'POST',
            headers: this.getAuthHeaders(),
            body: JSON.stringify({ scenario: scenario })
          });
          const data = await res.json();
          if (data.success) {
            this.showToast(`⚡ Scenario "${scenario}" triggered (${data.generated_reports_count} reports injected).`);
            await this.fetchModerationQueue();
          }
        } catch (err) {
          console.error('Scenario trigger error:', err);
        }
      };
    });
  }

  showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerHTML = `<span>ℹ️</span> <span>${message}</span>`;
    document.getElementById('toast-container').appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.adminPortal = new AdminPortal();
});
