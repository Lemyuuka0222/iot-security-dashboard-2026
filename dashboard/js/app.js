const API_URL = typeof BACKEND_URL !== 'undefined' ? BACKEND_URL : 'http://localhost:8000';

let logs = [];
let alerts = [];

function updateConnectionStatus(connected) {
    const status = document.getElementById('connectionStatus');
    if (connected) {
        status.textContent = 'Conectado';
        status.className = 'badge bg-success';
    } else {
        status.textContent = 'Desconectado';
        status.className = 'badge bg-warning';
    }
}

async function fetchLogs() {
    try {
        const response = await fetch(`${API_URL}/api/logs`);
        logs = await response.json();
        updateConnectionStatus(true);
        renderLogs();
        updateStats();
        updateHourlyChart(logs);
        updateMethodChart(logs);
    } catch (err) {
        console.warn('Error al obtener logs:', err);
        updateConnectionStatus(false);
    }
}

async function fetchAlerts() {
    try {
        const response = await fetch(`${API_URL}/api/alerts`);
        alerts = await response.json();
        renderAlerts();
    } catch (err) {
        console.warn('Error al obtener alertas:', err);
    }
}

async function fetchDoorStatus() {
    try {
        const response = await fetch(`${API_URL}/api/door`);
        const data = await response.json();
        updateDoorStatus(data.state);
    } catch (err) {
        console.warn('Error al obtener estado de puerta:', err);
    }
}

async function sendCommand(command) {
    try {
        const response = await fetch(`${API_URL}/api/door/${command}`, { method: 'POST' });
        const data = await response.json();
        if (data.success) {
            updateDoorStatus(data.state);
        }
    } catch (err) {
        console.error('Error al enviar comando:', err);
    }
}

function updateDoorStatus(state) {
    const icon = document.querySelector('#doorStatus .bi');
    const text = document.getElementById('doorStateText');

    if (state === 'open') {
        icon.className = 'bi bi-door-open-fill display-1 text-success';
        text.textContent = 'Abierta';
        text.className = 'text-success';
    } else {
        icon.className = 'bi bi-door-closed-fill display-1 text-secondary';
        text.textContent = 'Cerrada';
        text.className = 'text-secondary';
    }
}

function renderLogs() {
    const tbody = document.getElementById('logsBody');
    if (!logs.length) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-3">No hay registros</td></tr>';
        return;
    }

    tbody.innerHTML = logs.slice().reverse().map(log => {
        const time = new Date(log.timestamp).toLocaleTimeString('es-MX');
        const helmetIcon = log.helmet ? '<i class="bi bi-shield-check text-success"></i>' : '<i class="bi bi-shield-exclamation text-danger"></i>';
        const statusClass = log.status === 'authorized' ? 'text-success' : 'text-danger';
        const statusText = log.status === 'authorized' ? 'Autorizado' : 'Denegado';
        const methodLabels = { rfid: 'RFID', facial: 'Facial', manual: 'Manual' };
        const typeLabels = { entry: 'Entrada', exit: 'Salida' };

        return `<tr>
            <td>${time}</td>
            <td><strong>${log.person}</strong></td>
            <td>${typeLabels[log.type] || log.type}</td>
            <td><span class="badge bg-info">${methodLabels[log.method] || log.method}</span></td>
            <td>${helmetIcon}</td>
            <td class="${statusClass} fw-bold">${statusText}</td>
        </tr>`;
    }).join('');
}

function renderAlerts() {
    const container = document.getElementById('alertsList');
    if (!alerts.length) {
        container.innerHTML = '<div class="text-muted text-center py-4">No hay alertas</div>';
        return;
    }

    container.innerHTML = alerts.map(alert => `
        <div class="alert-item">
            <div class="d-flex justify-content-between">
                <strong><i class="bi bi-exclamation-triangle me-1"></i>${alert.type}</strong>
                <small class="text-muted">${new Date(alert.timestamp).toLocaleTimeString('es-MX')}</small>
            </div>
            <p class="mb-0 mt-1">${alert.message}</p>
        </div>
    `).join('');
}

function updateStats() {
    const today = new Date().toDateString();
    const todayLogs = logs.filter(l => new Date(l.timestamp).toDateString() === today);
    const total = todayLogs.filter(l => l.type === 'entry').length;
    const authorized = todayLogs.filter(l => l.status === 'authorized').length;
    const denied = todayLogs.filter(l => l.status === 'denied').length;
    const noHelmet = todayLogs.filter(l => !l.helmet).length;

    document.getElementById('totalToday').textContent = total;
    document.getElementById('totalAuthorized').textContent = authorized;
    document.getElementById('totalDenied').textContent = denied;
    document.getElementById('totalNoHelmet').textContent = noHelmet;
}

function refreshLogs() {
    fetchLogs();
    fetchAlerts();
}

// Polling every 3 seconds
setInterval(() => {
    fetchLogs();
    fetchAlerts();
    fetchDoorStatus();
}, 3000);

document.addEventListener('DOMContentLoaded', () => {
    fetchLogs();
    fetchAlerts();
    fetchDoorStatus();
});