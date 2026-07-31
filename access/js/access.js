const STATE_URL = '/api/access/state';
const NAME_URL = '/api/access/name';

let lastPhase = '';

function $(id) { return document.getElementById(id); }

function setClock() {
    const now = new Date();
    $('clock').textContent = now.toLocaleTimeString('es-MX');
    $('date').textContent = now.toLocaleDateString('es-MX', {
        weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'
    });
}

function showView(id) {
    ['viewIdle', 'viewScanning', 'viewRegisterFace', 'viewRegisterRfid', 'viewVerifyRfid', 'viewResult']
        .forEach(v => $(v).classList.add('hidden'));
    $(id).classList.remove('hidden');
}

function setPill(text, kind) {
    const pill = $('statusPill');
    pill.textContent = text;
    pill.className = 'pill' + (kind ? ' ' + kind : '');
}

function highlightLegend(phase) {
    $('cardLogin').classList.toggle('active', phase === 'scanning_face' || phase === 'verify_rfid');
    $('cardRegister').classList.toggle('active', phase === 'register_face' || phase === 'register_rfid');
    $('cardCancel').classList.toggle('active', phase === 'scanning_face' || phase === 'register_face' || phase === 'register_rfid' || phase === 'verify_rfid');
}

function renderRecent(recent) {
    const ul = $('recentList');
    if (!recent || !recent.length) {
        ul.innerHTML = '<li style="color:var(--text-dim)">Sin actividad reciente</li>';
        return;
    }
    const methodLabels = { rfid: 'RFID', facial: 'FACIAL', manual: 'MANUAL', dual: 'DOBLE' };
    ul.innerHTML = recent.map(r => `
        <li>
            <span>
                <span class="r-name">${r.person}</span>
                <span class="r-method"> · ${methodLabels[r.method] || r.method}</span>
            </span>
            <span>
                <span class="r-status ${r.status === 'authorized' ? 'ok' : 'bad'}">${r.status === 'authorized' ? 'OK' : 'DENEGADO'}</span>
                <span class="r-time"> ${r.time}</span>
            </span>
        </li>`).join('');
}

function renderResult(r) {
    $('resultName').textContent = r.user?.name || 'Desconocido';
    $('resultRole').textContent = r.user?.role || '---';

    const banner = $('resultBanner');
    const icon = $('resultIcon');
    const photo = $('resultPhoto');

    if (r.photo) {
        photo.src = r.photo;
        photo.classList.remove('hidden');
        icon.classList.add('hidden');
    } else {
        icon.className = 'bi big-icon ' + (r.authorized ? 'bi-check-circle-fill' : 'bi-x-circle-fill');
        icon.style.color = r.authorized ? 'var(--green)' : 'var(--red)';
        icon.classList.remove('hidden');
        photo.classList.add('hidden');
    }

    if (r.registered) {
        banner.className = 'result-banner ok';
        banner.textContent = 'REGISTRADO';
    } else if (r.authorized) {
        banner.className = 'result-banner ok';
        banner.textContent = 'ACCESO CONCEDIDO';
    } else {
        banner.className = 'result-banner bad';
        banner.textContent = 'ACCESO DENEGADO';
    }

    $('resultMsg').textContent = r.message || '';
    $('resultUid').textContent = r.uid ? 'UID: ' + r.uid : '';
}

function renderRegisterRfid(state) {
    if (state.register && state.register.name) {
        $('nameInput').value = state.register.name;
        $('nameSave').textContent = 'Guardado ✓';
    } else {
        $('nameSave').textContent = 'Guardar';
    }
}

function render(state) {
    setClock();
    setPill(state.pill || 'SISTEMA LISTO', state.pillKind);
    highlightLegend(state.phase);
    renderRecent(state.recent);
    if (state.phase !== lastPhase) {
        lastPhase = state.phase;
        if (state.phase === 'idle') showView('viewIdle');
        else if (state.phase === 'scanning_face') showView('viewScanning');
        else if (state.phase === 'register_face') showView('viewRegisterFace');
        else if (state.phase === 'register_rfid') showView('viewRegisterRfid');
        else if (state.phase === 'verify_rfid') showView('viewVerifyRfid');
        else if (state.phase === 'result') showView('viewResult');
    }
    if (state.phase === 'result') renderResult(state.result || {});
    if (state.phase === 'register_rfid') renderRegisterRfid(state);
    if (state.phase === 'verify_rfid' && state.verify) {
        $('verifyName').innerHTML = state.verify.name
            ? `Persona detectada: <strong>${state.verify.name}</strong>`
            : 'Confirmando identidad...';
    }
}

async function poll() {
    try {
        const res = await fetch(STATE_URL);
        if (!res.ok) throw new Error(res.status);
        const state = await res.json();
        render(state);
    } catch (err) {
        setPill('SERVIDOR NO DISPONIBLE', 'error');
    }
}

$('nameSave').addEventListener('click', async () => {
    const name = $('nameInput').value.trim();
    try {
        const res = await fetch(NAME_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });
        const data = await res.json();
        if (data.ok) $('nameSave').textContent = 'Guardado ✓';
    } catch (err) {
        $('nameSave').textContent = 'Error';
    }
});

setClock();
poll();
setInterval(poll, 700);
setInterval(setClock, 1000);
