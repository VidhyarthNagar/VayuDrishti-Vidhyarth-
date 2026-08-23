/**
 * Big Data Analytics & Charts Controller using Chart.js
 */

class WeatherAnalyticsCharts {
  constructor() {
    this.timelineChart = null;
    this.eventsChart = null;
    this.statesChart = null;
    this.verificationChart = null;

    // Dark theme global styling for Chart.js
    if (window.Chart) {
      Chart.defaults.color = '#94a3b8';
      Chart.defaults.font.family = "'Outfit', sans-serif";
      Chart.defaults.scale.grid.color = 'rgba(255, 255, 255, 0.05)';
    }
  }

  initCharts() {
    this._initTimelineChart();
    this._initEventsChart();
    this._initStatesChart();
    this._initVerificationChart();
  }

  _initTimelineChart() {
    const ctx = document.getElementById('chart-timeline');
    if (!ctx) return;

    this.timelineChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: [],
        datasets: [
          {
            label: 'Total Ingested',
            data: [],
            borderColor: '#38bdf8',
            backgroundColor: 'rgba(56, 189, 248, 0.12)',
            fill: true,
            tension: 0.35,
            borderWidth: 2
          },
          {
            label: 'Verified Truth',
            data: [],
            borderColor: '#10b981',
            backgroundColor: 'transparent',
            tension: 0.35,
            borderWidth: 2
          },
          {
            label: 'Fake / Misinformation Blocked',
            data: [],
            borderColor: '#ef4444',
            backgroundColor: 'rgba(239, 68, 68, 0.15)',
            fill: true,
            tension: 0.35,
            borderWidth: 2
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'top', labels: { boxWidth: 12, font: { size: 11 } } },
          tooltip: { mode: 'index', intersect: false }
        },
        scales: {
          x: { grid: { display: false } },
          y: { beginAtZero: true }
        }
      }
    });
  }

  _initEventsChart() {
    const ctx = document.getElementById('chart-events');
    if (!ctx) return;

    this.eventsChart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['Rainfall', 'Flooding', 'Thunderstorm', 'Heatwave', 'Dense Fog', 'Dust Storm', 'Cyclone', 'Hailstorm'],
        datasets: [{
          data: [0, 0, 0, 0, 0, 0, 0, 0],
          backgroundColor: [
            '#3b82f6', '#06b6d4', '#8b5cf6', '#ef4444',
            '#94a3b8', '#d97706', '#ec4899', '#6366f1'
          ],
          borderColor: '#0d1527',
          borderWidth: 2
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'right', labels: { boxWidth: 10, font: { size: 10 } } }
        },
        cutout: '65%'
      }
    });
  }

  _initStatesChart() {
    const ctx = document.getElementById('chart-states');
    if (!ctx) return;

    this.statesChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: [],
        datasets: [
          {
            label: 'Total Incidents',
            data: [],
            backgroundColor: 'rgba(56, 189, 248, 0.7)',
            borderRadius: 4
          },
          {
            label: 'Severe Disasters',
            data: [],
            backgroundColor: 'rgba(239, 68, 68, 0.8)',
            borderRadius: 4
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: 'y',
        plugins: {
          legend: { position: 'top', labels: { boxWidth: 10, font: { size: 10 } } }
        },
        scales: {
          x: { beginAtZero: true },
          y: { grid: { display: false } }
        }
      }
    });
  }

  _initVerificationChart() {
    const ctx = document.getElementById('chart-verification');
    if (!ctx) return;

    this.verificationChart = new Chart(ctx, {
      type: 'polarArea',
      data: {
        labels: ['IMD Official', 'AI Verified', 'Citizen Verified', 'Under Review', 'Fake Misinformation'],
        datasets: [{
          data: [0, 0, 0, 0, 0],
          backgroundColor: [
            'rgba(16, 185, 129, 0.75)',
            'rgba(6, 182, 212, 0.75)',
            'rgba(139, 92, 246, 0.75)',
            'rgba(245, 158, 11, 0.75)',
            'rgba(239, 68, 68, 0.85)'
          ],
          borderColor: '#0d1527',
          borderWidth: 2
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'right', labels: { boxWidth: 10, font: { size: 10 } } }
        },
        scales: {
          r: { grid: { color: 'rgba(255,255,255,0.08)' }, ticks: { display: false } }
        }
      }
    });
  }

  updateData(analytics, timelineData) {
    // 1. Update Timeline
    if (this.timelineChart && timelineData && timelineData.timeline) {
      const labels = timelineData.timeline.map(t => {
        const d = new Date(t.hour_bucket);
        return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      });
      const totals = timelineData.timeline.map(t => t.count);
      const verified = timelineData.timeline.map(t => t.verified_count);
      const fakes = timelineData.timeline.map(t => t.fake_count);

      this.timelineChart.data.labels = labels;
      this.timelineChart.data.datasets[0].data = totals;
      this.timelineChart.data.datasets[1].data = verified;
      this.timelineChart.data.datasets[2].data = fakes;
      this.timelineChart.update();
    }

    // 2. Update Event Distribution
    if (this.eventsChart && analytics.event_distribution) {
      const cats = ['rainfall', 'flooding', 'thunderstorm', 'heatwave', 'fog', 'dust_storm', 'cyclone', 'hailstorm'];
      const data = cats.map(c => analytics.event_distribution[c] || 0);
      this.eventsChart.data.datasets[0].data = data;
      this.eventsChart.update();
    }

    // 3. Update State Vulnerability
    if (this.statesChart && analytics.state_breakdown) {
      const labels = analytics.state_breakdown.slice(0, 8).map(s => s.state);
      const totals = analytics.state_breakdown.slice(0, 8).map(s => s.count);
      const severe = analytics.state_breakdown.slice(0, 8).map(s => s.severe_count || 0);

      this.statesChart.data.labels = labels;
      this.statesChart.data.datasets[0].data = totals;
      this.statesChart.data.datasets[1].data = severe;
      this.statesChart.update();
    }

    // 4. Update Verification Breakdown
    if (this.verificationChart && analytics.status_distribution) {
      const stats = analytics.status_distribution;
      const data = [
        stats['verified_imd'] || 0,
        stats['verified_ai'] || 0,
        stats['citizen_corroborated'] || 0,
        stats['under_review'] || 0,
        stats['fake_misleading'] || 0
      ];
      this.verificationChart.data.datasets[0].data = data;
      this.verificationChart.update();
    }
  }
}

window.weatherAnalyticsCharts = new WeatherAnalyticsCharts();
