let hourlyChartInstance = null;
let methodChartInstance = null;

function initHourlyChart() {
    const ctx = document.getElementById('hourlyChart').getContext('2d');
    const hours = Array.from({length: 24}, (_, i) => `${i}:00`);

    hourlyChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: hours,
            datasets: [{
                label: 'Accesos',
                data: Array(24).fill(0),
                backgroundColor: 'rgba(0, 212, 255, 0.7)',
                borderColor: '#00d4ff',
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
                    ticks: {
                        color: '#e0e0e0',
                        maxRotation: 45,
                        autoSkip: true,
                        maxTicksLimit: 12
                    },
                    grid: { color: '#2a2a5e' }
                },
                y: {
                    beginAtZero: true,
                    ticks: {
                        color: '#e0e0e0',
                        stepSize: 1
                    },
                    grid: { color: '#2a2a5e' }
                }
            }
        }
    });
}

function initMethodChart() {
    const ctx = document.getElementById('methodChart').getContext('2d');

    methodChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['RFID', 'Facial', 'Manual'],
            datasets: [{
                data: [0, 0, 0],
                backgroundColor: ['#00d4ff', '#00e676', '#ffab00'],
                borderColor: '#1a1a3e',
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

function updateHourlyChart(logs) {
    if (!hourlyChartInstance) return;
    const hourly = Array(24).fill(0);
    const today = new Date().toDateString();

    logs.forEach(log => {
        const logDate = new Date(log.timestamp).toDateString();
        if (logDate === today) {
            const hour = new Date(log.timestamp).getHours();
            hourly[hour]++;
        }
    });

    hourlyChartInstance.data.datasets[0].data = hourly;
    hourlyChartInstance.update();
}

function updateMethodChart(logs) {
    if (!methodChartInstance) return;
    let rfid = 0, facial = 0, manual = 0;

    logs.forEach(log => {
        if (log.method === 'rfid') rfid++;
        else if (log.method === 'facial') facial++;
        else if (log.method === 'manual') manual++;
    });

    methodChartInstance.data.datasets[0].data = [rfid, facial, manual];
    methodChartInstance.update();
}

document.addEventListener('DOMContentLoaded', () => {
    initHourlyChart();
    initMethodChart();
});