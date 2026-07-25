firebase.initializeApp(firebaseConfig);
const db = firebase.firestore();

let allLogs = [];
let allAlerts = [];

function updateConnectionStatus(connected) {
  const el = document.getElementById('connectionStatus');
  if (connected) {
    el.textContent = 'Conectado';
    el.className = 'badge';
    el.style.background = '#004400';
    el.style.color = '#00cc66';
    el.style.border = '1px solid #00cc66';
  } else {
    el.textContent = 'Desconectado';
    el.className = 'badge';
    el.style.background = '#2a0000';
    el.style.color = '#ff6666';
    el.style.border = '1px solid #cc3333';
  }
}

function renderLogs() {
  const tbody = document.getElementById('logsBody');
  if (!allLogs.length) {
    tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-3">No hay registros</td></tr>';
    return;
  }

  const sorted = [...allLogs].sort((a, b) => b.timestamp?.toDate() - a.timestamp?.toDate());
  tbody.innerHTML = sorted.slice(0, 50).map(log => {
    const ts = log.timestamp?.toDate() || new Date();
    const time = ts.toLocaleTimeString('es-MX');
    const helmetIcon = log.helmet ? '<i class="bi bi-shield-check text-success"></i>' : '<i class="bi bi-shield-exclamation text-danger"></i>';
    const statusClass = log.status === 'authorized' ? 'text-success' : 'text-danger';
    const statusText = log.status === 'authorized' ? 'Autorizado' : 'Denegado';
    const methodLabels = { rfid: 'RFID', facial: 'Facial', manual: 'Manual' };
    const typeLabels = { entry: 'Entrada', exit: 'Salida' };
    return `<tr>
      <td>${time}</td>
      <td><strong>${log.person}</strong></td>
      <td>${typeLabels[log.type] || log.type}</td>
      <td><span class="badge" style="background:#003300;color:#00cc66;border:1px solid #00cc66;">${methodLabels[log.method] || log.method}</span></td>
      <td>${helmetIcon}</td>
      <td class="${statusClass} fw-bold">${statusText}</td>
    </tr>`;
  }).join('');
}

function renderAlerts() {
  const container = document.getElementById('alertsList');
  if (!allAlerts.length) {
    container.innerHTML = '<div class="text-muted text-center py-4">No hay alertas</div>';
    return;
  }

  const sorted = [...allAlerts].sort((a, b) => b.timestamp?.toDate() - a.timestamp?.toDate());
  container.innerHTML = sorted.slice(0, 10).map(a => `
    <div class="alert-item">
      <div class="d-flex justify-content-between">
        <strong><i class="bi bi-exclamation-triangle me-1"></i>${a.type}</strong>
        <small class="text-muted">${(a.timestamp?.toDate() || new Date()).toLocaleTimeString('es-MX')}</small>
      </div>
      <p class="mb-0 mt-1">${a.message}</p>
    </div>
  `).join('');
}

function updateStats() {
  const today = new Date().toDateString();
  const todayLogs = allLogs.filter(l => {
    const d = l.timestamp?.toDate();
    return d && d.toDateString() === today;
  });
  const total = todayLogs.filter(l => l.type === 'entry').length;
  const authorized = todayLogs.filter(l => l.status === 'authorized').length;
  const denied = todayLogs.filter(l => l.status === 'denied').length;
  const noHelmet = todayLogs.filter(l => !l.helmet).length;

  document.getElementById('totalToday').textContent = total;
  document.getElementById('totalAuthorized').textContent = authorized;
  document.getElementById('totalDenied').textContent = denied;
  document.getElementById('totalNoHelmet').textContent = noHelmet;
}

function updateHourlyChart() {
  if (!window.hourlyChartInstance) return;
  const hourly = Array(24).fill(0);
  const today = new Date().toDateString();
  allLogs.forEach(log => {
    const d = log.timestamp?.toDate();
    if (d && d.toDateString() === today) {
      hourly[d.getHours()]++;
    }
  });
  window.hourlyChartInstance.data.datasets[0].data = hourly;
  window.hourlyChartInstance.update();
}

function updateMethodChart() {
  if (!window.methodChartInstance) return;
  let rfid = 0, facial = 0, manual = 0;
  allLogs.forEach(log => {
    if (log.method === 'rfid') rfid++;
    else if (log.method === 'facial') facial++;
    else if (log.method === 'manual') manual++;
  });
  window.methodChartInstance.data.datasets[0].data = [rfid, facial, manual];
  window.methodChartInstance.update();
}

function updateDoorStatus(state) {
  const icon = document.querySelector('#doorStatus .bi');
  const text = document.getElementById('doorStateText');
  if (state === 'open') {
    icon.className = 'bi bi-door-open-fill display-1';
    icon.style.color = '#00cc66';
    text.textContent = 'Abierta';
    text.className = '';
    text.style.color = '#00cc66';
  } else {
    icon.className = 'bi bi-door-closed-fill display-1';
    icon.style.color = '#004d00';
    text.textContent = 'Cerrada';
    text.className = '';
    text.style.color = '#004d00';
  }
}

async function sendCommand(command) {
  try {
    await db.collection('controls').doc('door').set({ state: command, updatedAt: firebase.firestore.FieldValue.serverTimestamp() });
    if (command === 'open') updateDoorStatus('open');
    else updateDoorStatus('closed');
  } catch (err) {
    console.error('Error:', err);
  }
}

function refreshLogs() {}

document.addEventListener('DOMContentLoaded', () => {
  db.collection('logs').orderBy('timestamp', 'desc').limit(100).onSnapshot(snapshot => {
    allLogs = [];
    snapshot.forEach(doc => allLogs.push({ id: doc.id, ...doc.data() }));
    updateConnectionStatus(true);
    renderLogs();
    updateStats();
    updateHourlyChart();
    updateMethodChart();
  }, err => {
    console.warn('Firebase error:', err);
    updateConnectionStatus(false);
  });

  db.collection('alerts').orderBy('timestamp', 'desc').limit(20).onSnapshot(snapshot => {
    allAlerts = [];
    snapshot.forEach(doc => allAlerts.push({ id: doc.id, ...doc.data() }));
    renderAlerts();
  });

  db.collection('controls').doc('door').onSnapshot(doc => {
    if (doc.exists) updateDoorStatus(doc.data().state);
  });
});