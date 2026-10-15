const form = document.querySelector('#search-form');
const input = document.querySelector('#document-input');
const feedback = document.querySelector('#feedback');
const results = document.querySelector('#results');
const submitButton = form.querySelector('button[type="submit"]');
const documentToggle = document.querySelector('#toggle-document');
const resourcesMenu = document.querySelector('#resources-menu');
const resourcesToggle = document.querySelector('#resources-toggle');
const resourcesPanel = document.querySelector('#resources-panel');
let memberDocument = '';
let isDocumentVisible = false;

const text = (selector, value) => {
  const node = document.querySelector(selector);
  if (node) node.textContent = value ?? '—';
};

function initials(name) {
  return (name || 'FESC')
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase();
}

function humanizeStatus(status) {
  const labels = { ACTIVE: 'Activa', INACTIVE: 'Inactiva', SUSPENDED: 'Suspendida' };
  return labels[status] || status || 'Sin información';
}

function humanizeRelationship(relationship) {
  const labels = {
    SPOUSE: 'Cónyuge', CHILD: 'Hijo/a', FATHER: 'Padre', MOTHER: 'Madre',
  };
  return labels[relationship] || relationship || 'Beneficiario';
}

function formatUpdatedAt(date = new Date()) {
  return `Actualizado a las ${new Intl.DateTimeFormat('es-CO', {
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)}`;
}

function setFeedback(message, isError = false) {
  feedback.textContent = message;
  feedback.classList.toggle('is-error', isError);
  feedback.hidden = !message;
}

function renderBeneficiaries(items) {
  const list = document.querySelector('#beneficiary-list');
  list.replaceChildren();
  const beneficiaries = Array.isArray(items) ? items : [];
  text('#beneficiary-count', String(beneficiaries.length));
  text('#beneficiary-pill', String(beneficiaries.length).padStart(2, '0'));

  if (!beneficiaries.length) {
    const empty = document.createElement('li');
    empty.className = 'empty-beneficiaries';
    empty.innerHTML = '<span class="empty-icon" aria-hidden="true">♡</span><span><strong>Sin beneficiarios registrados</strong><small>Cuando se registren, aparecerán aquí.</small></span>';
    list.append(empty);
    return;
  }

  for (const person of beneficiaries) {
    const item = document.createElement('li');
    item.className = 'beneficiary-item';
    const avatar = document.createElement('span');
    avatar.className = 'beneficiary-avatar';
    avatar.textContent = initials(person.fullName);
    const copy = document.createElement('span');
    copy.className = 'beneficiary-copy';
    const name = document.createElement('strong');
    name.textContent = person.fullName || 'Nombre no disponible';
    const relation = document.createElement('small');
    relation.textContent = humanizeRelationship(person.relationship);
    copy.append(name, relation);
    const documentNumber = document.createElement('span');
    documentNumber.className = 'beneficiary-document';
    documentNumber.textContent = person.document ? `•••${String(person.document).slice(-4)}` : '';
    item.append(avatar, copy, documentNumber);
    list.append(item);
  }
}

function renderMember(payload) {
  const member = payload.member || {};
  const company = payload.company || member.company || {};
  const memberName = member.fullName || 'Afiliado';
  const status = humanizeStatus(member.status);
  const activeMembers = Number.isFinite(Number(company.activeMembers))
    ? String(company.activeMembers)
    : '—';
  memberDocument = String(member.document || '');
  isDocumentVisible = false;

  text('#member-name', memberName);
  text('#member-document', `Documento ${maskDocument(memberDocument)}`);
  text('#member-id', maskDocument(memberDocument));
  documentToggle.disabled = !memberDocument;
  documentToggle.setAttribute('aria-pressed', 'false');
  documentToggle.textContent = 'Mostrar';
  documentToggle.setAttribute('aria-label', 'Mostrar número de documento completo');
  text('#member-status', status);
  text('#member-status-label', status);
  text('#member-company', company.name || 'Sin empresa registrada');
  text('#company-name', company.name || 'Sin empresa registrada');
  text('#company-name-short', company.name || 'Sin empresa');
  text('#company-id', `Código ${company.id || '—'}`);
  text('#company-members', activeMembers);
  text('#company-members-banner', activeMembers);
  text('#member-avatar', initials(memberName));
  text('#updated-at', formatUpdatedAt());
  document.querySelector('#member-status-badge').classList.toggle('is-inactive', member.status !== 'ACTIVE');
  renderBeneficiaries(payload.beneficiaries);
  results.classList.remove('is-loading');
  results.hidden = false;
}

function maskDocument(value) {
  if (!value) return '—';
  return value.length <= 4 ? '•'.repeat(value.length) : `••••••${value.slice(-4)}`;
}

documentToggle.addEventListener('click', () => {
  if (!memberDocument) return;
  isDocumentVisible = !isDocumentVisible;
  const displayed = isDocumentVisible ? memberDocument : maskDocument(memberDocument);
  text('#member-id', displayed);
  text('#member-document', `Documento ${displayed}`);
  documentToggle.textContent = isDocumentVisible ? 'Ocultar' : 'Mostrar';
  documentToggle.setAttribute('aria-pressed', String(isDocumentVisible));
  documentToggle.setAttribute(
    'aria-label',
    `${isDocumentVisible ? 'Ocultar' : 'Mostrar'} número de documento completo`,
  );
});

async function searchMember(documentNumber) {
  const normalized = documentNumber.trim();
  if (!/^[0-9]{1,20}$/.test(normalized)) {
    setFeedback('Escribe un número de documento válido, solo con dígitos.', true);
    input.focus();
    return;
  }

  setFeedback('');
  results.classList.add('is-loading');
  results.hidden = true;
  memberDocument = '';
  isDocumentVisible = false;
  documentToggle.disabled = true;
  documentToggle.textContent = 'Mostrar';
  documentToggle.setAttribute('aria-pressed', 'false');
  documentToggle.setAttribute('aria-label', 'Mostrar número de documento completo');
  text('#member-document', 'Documento —');
  text('#member-id', '—');
  submitButton.disabled = true;
  submitButton.querySelector('span').textContent = 'Consultando…';
  text('#member-name', 'Buscando afiliado…');
  text('#member-status', 'Cargando…');
  text('#company-name-short', 'Cargando…');

  try {
    const response = await fetch(`/api/member/${encodeURIComponent(normalized)}`, {
      headers: { Accept: 'application/json' },
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(response.status === 404 ? 'No encontramos un afiliado con ese documento.' : (payload.message || 'No se pudo completar la consulta.'));
    }
    renderMember(payload);
  } catch (error) {
    setFeedback(error.message || 'Ocurrió un error al consultar el afiliado.', true);
  } finally {
    submitButton.disabled = false;
    submitButton.querySelector('span').textContent = 'Buscar afiliado';
    results.classList.remove('is-loading');
  }
}

form.addEventListener('submit', (event) => {
  event.preventDefault();
  searchMember(input.value);
});

document.querySelector('#demo-button').addEventListener('click', () => {
  input.value = '1019886173';
  searchMember(input.value);
});

document.querySelectorAll('.side-nav a[href^="#"]').forEach((link) => {
  link.addEventListener('click', () => {
    document.querySelectorAll('.side-nav .nav-link').forEach((item) => {
      item.classList.remove('active');
      item.removeAttribute('aria-current');
    });
    link.classList.add('active');
    link.setAttribute('aria-current', 'page');
  });
});

resourcesToggle.addEventListener('click', () => {
  const isExpanded = resourcesToggle.getAttribute('aria-expanded') === 'true';
  resourcesToggle.setAttribute('aria-expanded', String(!isExpanded));
  resourcesPanel.hidden = isExpanded;
});

resourcesPanel.addEventListener('click', (event) => {
  if (event.target.closest('a')) {
    resourcesToggle.setAttribute('aria-expanded', 'false');
    resourcesPanel.hidden = true;
  }
});

document.addEventListener('click', (event) => {
  if (!resourcesMenu.contains(event.target)) {
    resourcesToggle.setAttribute('aria-expanded', 'false');
    resourcesPanel.hidden = true;
  }
});

document.querySelectorAll('.account-pill').forEach((link) => {
  link.addEventListener('click', () => {
    document.querySelectorAll('.account-pill').forEach((pill) => {
      pill.classList.remove('is-active');
      pill.removeAttribute('aria-current');
    });
    link.classList.add('is-active');
    link.setAttribute('aria-current', 'page');
  });
});

document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && resourcesToggle.getAttribute('aria-expanded') === 'true') {
    resourcesToggle.setAttribute('aria-expanded', 'false');
    resourcesPanel.hidden = true;
    resourcesToggle.focus();
    return;
  }
  const target = event.target;
  const isTyping = target instanceof HTMLElement
    && (target.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName));
  if (event.key === '/' && !event.ctrlKey && !event.metaKey && !event.altKey && !isTyping) {
    event.preventDefault();
    input.focus();
    input.select();
  }
});

async function checkServices() {
  const status = document.querySelector('#system-status');
  try {
    const response = await fetch('/api/health', { headers: { Accept: 'application/json' } });
    const health = await response.json();
    status.classList.toggle('is-down', !response.ok || health.status !== 'UP');
    status.querySelector('span:last-child').textContent = response.ok && health.status === 'UP'
      ? 'Servicios en línea'
      : 'Servicio no disponible';
  } catch {
    status.classList.add('is-down');
    status.querySelector('span:last-child').textContent = 'Servicio no disponible';
  }
}

checkServices();
searchMember(input.value);
