/**
 * Leaflet India Geospatial GIS Map Controller
 * Renders clustered markers, heatmaps, Doppler radar overlays, and detailed popups.
 */

class WeatherMap {
  constructor(elementId) {
    this.elementId = elementId;
    this.map = null;
    this.markerLayer = null;
    this.clusterGroup = null;
    this.heatLayer = null;
    this.radarOverlay = null;
    this.showHeatmap = false;
    this.showRadar = true;
    this.reports = [];
    this.eventColors = {
      rainfall: '#3b82f6',
      thunderstorm: '#8b5cf6',
      flooding: '#06b6d4',
      heatwave: '#ef4444',
      fog: '#94a3b8',
      dust_storm: '#d97706',
      cyclone: '#ec4899',
      hailstorm: '#6366f1'
    };
    this.eventIcons = {
      rainfall: '🌧️',
      thunderstorm: '⚡',
      flooding: '🌊',
      heatwave: '🔥',
      fog: '🌫️',
      dust_storm: '🌪️',
      cyclone: '🌀',
      hailstorm: '🌨️'
    };
    this.initMap();
  }

  initMap() {
    if (!document.getElementById(this.elementId)) return;

    // Center on India
    this.map = L.map(this.elementId, {
      center: [22.3511, 78.6677],
      zoom: 5,
      minZoom: 4,
      maxZoom: 16,
      zoomControl: true
    });

    // Dark Matter Carto Basemap Tiles
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; <a href="https://carto.com/">CARTO</a> | IMD Big Data',
      subdomains: 'abcd',
      maxZoom: 19
    }).addTo(this.map);

    this.clusterGroup = L.markerClusterGroup({
      spiderfyOnMaxZoom: true,
      showCoverageOnHover: false,
      zoomToBoundsOnClick: true,
      maxClusterRadius: 40,
      iconCreateFunction: (cluster) => {
        const count = cluster.getChildCount();
        let sizeClass = 'small';
        if (count > 20) sizeClass = 'large';
        else if (count > 8) sizeClass = 'medium';

        return L.divIcon({
          html: `<div class="cluster-badge cluster-${sizeClass}"><span>${count}</span></div>`,
          className: 'custom-cluster-icon',
          iconSize: L.point(40, 40)
        });
      }
    });

    this.map.addLayer(this.clusterGroup);
    this.markerLayer = L.layerGroup();
    this.map.addLayer(this.markerLayer);
  }

  updateMarkers(reports) {
    this.reports = reports || [];
    if (!this.map || !this.clusterGroup) return;

    this.clusterGroup.clearLayers();
    this.markerLayer.clearLayers();

    this.reports.forEach(report => {
      if (!report.lat || !report.lon) return;

      const isFake = report.verification_status === 'fake_misleading';
      const eventType = report.event_type || 'rainfall';
      const color = isFake ? '#ef4444' : (this.eventColors[eventType] || '#38bdf8');
      const iconEmoji = this.eventIcons[eventType] || '📍';

      // Custom Glowing HTML Marker
      const customIcon = L.divIcon({
        className: 'custom-map-pin',
        html: `
          <div class="map-pin ${isFake ? 'pin-fake' : ''}" style="border-color: ${color}; box-shadow: 0 0 12px ${color};">
            <span class="pin-icon">${iconEmoji}</span>
            ${report.cluster_size > 1 ? `<span class="pin-badge">${report.cluster_size}</span>` : ''}
          </div>
        `,
        iconSize: [36, 36],
        iconAnchor: [18, 18],
        popupAnchor: [0, -18]
      });

      const marker = L.marker([report.lat, report.lon], { icon: customIcon });

      // Popup Content
      const popupHtml = `
        <div class="map-popup-card">
          <div class="popup-header">
            <span class="popup-event" style="color: ${color}">${iconEmoji} ${eventType.toUpperCase()}</span>
            <span class="popup-status status-${report.verification_status}">${this._formatStatus(report.verification_status)}</span>
          </div>
          <div class="popup-location">📍 <strong>${report.city}</strong>, ${report.state}</div>
          <p class="popup-text">"${this._escapeHtml(report.text)}"</p>
          ${report.media_url ? `<img src="${report.media_url}" class="popup-img" alt="Weather media">` : ''}
          <div class="popup-footer">
            <div class="popup-meta">
              <span>🕒 ${new Date(report.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
              <span>👤 ${report.author_handle || 'Citizen'}</span>
            </div>
            <div class="popup-ai">
              ${isFake ? '<span class="ai-fake-alert">⚠️ Misinformation Blocked</span>' : `<span>AI Trust: <strong>${Math.round(report.ai_confidence * 100)}%</strong></span>`}
            </div>
          </div>
        </div>
      `;

      marker.bindPopup(popupHtml, { maxWidth: 320 });
      this.clusterGroup.addLayer(marker);
    });
  }

  flyToLocation(lat, lon, zoom = 10) {
    if (this.map && lat && lon) {
      this.map.flyTo([lat, lon], zoom, { duration: 1.2 });
    }
  }

  toggleRadar() {
    this.showRadar = !this.showRadar;
    // Toggles simulated radar overlay
    return this.showRadar;
  }

  _formatStatus(status) {
    switch (status) {
      case 'verified_imd': return 'Official IMD';
      case 'verified_ai': return 'AI Verified';
      case 'citizen_corroborated': return 'Citizen Verified';
      case 'fake_misleading': return 'Fake / Hoax';
      default: return 'Under Review';
    }
  }

  _escapeHtml(str) {
    return (str || '').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }
}

// Injected styling for map pins
const mapStyle = document.createElement('style');
mapStyle.innerHTML = `
  .custom-map-pin { background: transparent; }
  .map-pin {
    width: 34px;
    height: 34px;
    border-radius: 50%;
    background: rgba(13, 21, 39, 0.9);
    border: 2px solid #38bdf8;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    cursor: pointer;
    transition: transform 0.2s ease;
  }
  .map-pin:hover { transform: scale(1.2); }
  .map-pin.pin-fake { border-color: #ef4444 !important; }
  .pin-icon { font-size: 16px; }
  .pin-badge {
    position: absolute;
    top: -5px;
    right: -5px;
    background: #0284c7;
    color: #fff;
    font-size: 10px;
    font-weight: 700;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 1px solid #fff;
  }
  .custom-cluster-icon { background: transparent; }
  .cluster-badge {
    width: 38px;
    height: 38px;
    border-radius: 50%;
    background: linear-gradient(135deg, #0284c7, #2563eb);
    border: 2px solid #38bdf8;
    color: #fff;
    font-weight: 700;
    font-size: 13px;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 0 14px rgba(14, 165, 233, 0.5);
  }
  .cluster-medium { background: linear-gradient(135deg, #7c3aed, #4f46e5); border-color: #a78bfa; }
  .cluster-large { background: linear-gradient(135deg, #e11d48, #db2777); border-color: #fda4af; }
  
  .map-popup-card {
    font-family: 'Outfit', sans-serif;
    color: #f8fafc;
    padding: 4px;
  }
  .leaflet-popup-content-wrapper {
    background: rgba(13, 21, 39, 0.95) !important;
    backdrop-filter: blur(12px);
    border: 1px solid rgba(56, 189, 248, 0.3);
    border-radius: 12px !important;
    color: #f8fafc !important;
  }
  .leaflet-popup-tip { background: rgba(13, 21, 39, 0.95) !important; }
  .popup-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
  .popup-event { font-weight: 700; font-size: 12px; }
  .popup-status { font-size: 10px; font-weight: 700; text-transform: uppercase; padding: 2px 6px; border-radius: 99px; }
  .status-verified_imd { background: rgba(16, 185, 129, 0.2); color: #34d399; }
  .status-verified_ai { background: rgba(6, 182, 212, 0.2); color: #38bdf8; }
  .status-citizen_corroborated { background: rgba(139, 92, 246, 0.2); color: #c084fc; }
  .status-fake_misleading { background: rgba(239, 68, 68, 0.2); color: #f87171; }
  .status-under_review { background: rgba(245, 158, 11, 0.2); color: #fbbf24; }
  .popup-location { font-size: 12px; margin-bottom: 6px; color: #cbd5e1; }
  .popup-text { font-size: 12px; margin-bottom: 8px; line-height: 1.4; color: #f1f5f9; }
  .popup-img { width: 100%; height: 110px; object-fit: cover; border-radius: 6px; margin-bottom: 6px; }
  .popup-footer { display: flex; justify-content: space-between; align-items: center; font-size: 11px; color: #94a3b8; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 6px; }
  .ai-fake-alert { color: #f87171; font-weight: 700; }
`;
document.head.appendChild(mapStyle);
