/**
 * Citizen Weather Watcher Crowdsourcing Controller
 */

class CitizenPortal {
  constructor() {
    this.lat = 19.0760;
    this.lon = 72.8777;
    this.previewTimer = null;
    this.init();
  }

  init() {
    this.bindEvents();
    this.initGeoPicker();
  }

  initGeoPicker() {
    const geoBtn = document.getElementById('btn-get-location');
    if (geoBtn) {
      geoBtn.addEventListener('click', () => {
        if (navigator.geolocation) {
          geoBtn.innerText = '🛰️ Detecting GPS...';
          navigator.geolocation.getCurrentPosition(
            (pos) => {
              this.lat = pos.coords.latitude;
              this.lon = pos.coords.longitude;
              document.getElementById('input-lat').value = this.lat.toFixed(4);
              document.getElementById('input-lon').value = this.lon.toFixed(4);
              geoBtn.innerText = '✓ GPS Locked';
              geoBtn.classList.add('btn-success');
              this.showToast('GPS coordinates accurately locked.');
            },
            (err) => {
              geoBtn.innerText = '📍 Detect GPS Location';
              this.showToast('Could not fetch exact GPS. You can enter coordinates manually.');
            }
          );
        }
      });
    }
  }

  bindEvents() {
    // Media Upload / Mock Camera Preview
    const mediaInput = document.getElementById('citizen-media-input');
    const mediaPreview = document.getElementById('citizen-media-preview');
    if (mediaInput && mediaPreview) {
      mediaInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
          const reader = new FileReader();
          reader.onload = (ev) => {
            mediaPreview.src = ev.target.result;
            mediaPreview.style.display = 'block';
          };
          reader.readAsDataURL(file);
        }
      });
    }

    // City Selection Auto Coordinates
    const citySelect = document.getElementById('citizen-city');
    if (citySelect) {
      citySelect.addEventListener('change', (e) => {
        const selected = e.target.options[e.target.selectedIndex];
        if (selected && selected.dataset.lat && selected.dataset.lon) {
          this.lat = parseFloat(selected.dataset.lat);
          this.lon = parseFloat(selected.dataset.lon);
          document.getElementById('input-lat').value = this.lat.toFixed(4);
          document.getElementById('input-lon').value = this.lon.toFixed(4);
          document.getElementById('citizen-state').value = selected.dataset.state || 'Maharashtra';
          this.triggerPreview();
        }
      });
    }

    // Real-Time AI Preview debouncer on text description
    const textInput = document.getElementById('citizen-text');
    if (textInput) {
      textInput.addEventListener('input', () => {
        clearTimeout(this.previewTimer);
        this.previewTimer = setTimeout(() => this.triggerPreview(), 400);
      });
    }

    // Form Submission
    const form = document.getElementById('citizen-report-form');
    if (form) {
      form.addEventListener('submit', (e) => this.handleSubmit(e));
    }
  }

  async triggerPreview() {
    const text = document.getElementById('citizen-text').value.trim();
    const city = document.getElementById('citizen-city').value;
    const state = document.getElementById('citizen-state').value;

    if (text.length < 5) return;

    try {
      const res = await fetch('/api/citizen/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, city, state })
      });
      const data = await res.json();
      this.renderPreviewResult(data);
    } catch (e) {
      console.error('AI preview error:', e);
    }
  }

  renderPreviewResult(data) {
    const previewContainer = document.getElementById('ai-preview-box');
    if (!previewContainer) return;

    previewContainer.style.display = 'block';
    const isFakeRisk = data.fake_risk_level.includes('High Risk');

    previewContainer.innerHTML = `
      <div style="background: rgba(13, 21, 39, 0.85); border: 1px solid ${isFakeRisk ? 'var(--accent-red)' : 'var(--accent-cyan)'}; border-radius: 8px; padding: 1rem;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
          <span style="font-weight: 700; font-size: 0.85rem; color: ${isFakeRisk ? 'var(--accent-red)' : 'var(--accent-cyan)'};">
            🤖 Real-Time AI Pre-Validation
          </span>
          <span class="card-status-badge ${isFakeRisk ? 'badge-fake' : 'badge-ai'}">
            ${data.predicted_event_type.toUpperCase()}
          </span>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; font-size: 0.8rem; margin-bottom: 0.5rem;">
          <div>AI Confidence: <strong>${data.ai_confidence_pct}%</strong></div>
          <div>Severity: <strong>${data.estimated_severity}</strong></div>
          <div>Trust Risk: <strong style="color: ${isFakeRisk ? '#f87171' : '#34d399'}">${data.fake_risk_level}</strong></div>
          <div>Radar Consistency: <strong>${data.radar_consistency ? '✓ Aligned' : '✗ Discrepancy'}</strong></div>
        </div>
        <p style="font-size: 0.75rem; color: var(--text-muted);">${data.diagnostic_notes ? data.diagnostic_notes.join(' | ') : ''}</p>
      </div>
    `;
  }

  async handleSubmit(e) {
    e.preventDefault();
    const btn = document.getElementById('btn-submit-report');
    btn.disabled = true;
    btn.innerText = 'Submitting & Ingesting...';

    const payload = {
      author_name: document.getElementById('citizen-name').value || 'Anonymous Citizen',
      text: document.getElementById('citizen-text').value,
      city: document.getElementById('citizen-city').value,
      state: document.getElementById('citizen-state').value,
      lat: parseFloat(document.getElementById('input-lat').value) || this.lat,
      lon: parseFloat(document.getElementById('input-lon').value) || this.lon,
      media_url: document.getElementById('citizen-media-url').value || (
        document.getElementById('citizen-media-preview').src.startsWith('data:') ? 
        document.getElementById('citizen-media-preview').src : 'https://images.unsplash.com/photo-1515694346937-94d85e41e6f0?w=800&auto=format&fit=crop&q=80'
      )
    };

    try {
      const res = await fetch('/api/citizen/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const result = await res.json();

      if (result.success) {
        this.showSuccessModal(result.report);
        document.getElementById('citizen-report-form').reset();
        document.getElementById('ai-preview-box').style.display = 'none';
        document.getElementById('citizen-media-preview').style.display = 'none';
      }
    } catch (err) {
      console.error('Submission failed:', err);
      this.showToast('Submission error. Please try again.');
    } finally {
      btn.disabled = false;
      btn.innerText = 'Submit Weather Report';
    }
  }

  showSuccessModal(report) {
    const modal = document.getElementById('citizen-success-modal');
    if (!modal) return;

    document.getElementById('success-report-id').innerText = report.id;
    document.getElementById('success-status').innerText = report.verification_status.toUpperCase();
    document.getElementById('success-category').innerText = `${report.event_type.toUpperCase()} (${report.severity})`;
    modal.classList.add('open');
  }

  closeSuccessModal() {
    const modal = document.getElementById('citizen-success-modal');
    if (modal) modal.classList.remove('open');
  }

  showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerHTML = `<span>🛰️</span> <span>${message}</span>`;
    document.getElementById('toast-container').appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.citizenPortal = new CitizenPortal();
});
