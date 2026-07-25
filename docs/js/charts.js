function initHourlyChart() {
  const ctx = document.getElementById('hourlyChart').getContext('2d');
  const hours = Array.from({length: 24}, (_, i) => `${i}:00`);

  window.hourlyChartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: hours,
      datasets: [{
        label: 'Accesos',
        data: Array(24).fill(0),
        backgroundColor: 'rgba(0, 204, 102, 0.7)',
        borderColor: '#00cc66',
        borderWidth: 1
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: { color: '#e0e0e0' }
        }
      },
      scales: {
        x: {
          ticks: { color: '#e0e0e0', maxRotation: 45, autoSkip: true, maxTicksLimit: 12 },
          grid: { color: '#1a3a1a' }
        },
        y: {
          beginAtZero: true,
          ticks: { color: '#e0e0e0', stepSize: 1 },
          grid: { color: '#1a3a1a' }
        }
      }
    }
  });
}

function initMethodChart() {
  const ctx = document.getElementById('methodChart').getContext('2d');

  window.methodChartInstance = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['RFID', 'Facial', 'Manual'],
      datasets: [{
        data: [0, 0, 0],
        backgroundColor: ['#00cc66', '#00994d', '#336600'],
        borderColor: '#0d0d0d',
        borderWidth: 2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: '#e0e0e0', padding: 15 }
        }
      }
    }
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initHourlyChart();
  initMethodChart();
});
