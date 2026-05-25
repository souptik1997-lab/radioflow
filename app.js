const state = {
  me: null,
  users: [],
  patients: [],
  consultants: [],
  paymentModes: [],
  machines: ["Elekta", "Tomo"],
  selectedId: "",
  search: "",
  view: "all",
  dialog: null,
  message: "",
};

const can = () => true;
const canAddPatient = () => true;

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    ...options,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || "Request failed");
  return data;
}

async function loadState() {
  try {
    const data = await api("/api/state");
    Object.assign(state, data);
    state.selectedId ||= state.patients[0]?.id || "";
    renderApp();
  } catch (error) {
    document.getElementById("app").innerHTML = `<main class="auth-shell"><div class="auth-card"><h1>RT Patient Flow</h1><p>Could not load the backend.</p><div class="notice">${escapeHtml(error.message)}</div></div></main>`;
  }
}

function icon(name) {
  const icons = {
    plus: '<path d="M12 5v14M5 12h14"/>',
    settings: '<path d="M12 15.5A3.5 3.5 0 1 0 12 8a3.5 3.5 0 0 0 0 7.5Z"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1a2 2 0 0 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 0 1-4 0v-.1a1.7 1.7 0 0 0-1-1.5 1.7 1.7 0 0 0-1.9.3l-.1.1A2 2 0 0 1 4.2 17l.1-.1a1.7 1.7 0 0 0 .3-1.9 1.7 1.7 0 0 0-1.5-1H3a2 2 0 0 1 0-4h.1a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.9L4.2 7A2 2 0 0 1 7 4.2l.1.1a1.7 1.7 0 0 0 1.9.3 1.7 1.7 0 0 0 1-1.5V3a2 2 0 0 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.9-.3l.1-.1A2 2 0 0 1 19.8 7l-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.5 1h.1a2 2 0 0 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1Z"/>',
    search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    user: '<path d="M20 21a8 8 0 0 0-16 0"/><circle cx="12" cy="7" r="4"/>',
    check: '<path d="m5 12 4 4L19 6"/>',
    x: '<path d="M18 6 6 18M6 6l12 12"/>',
    alert: '<path d="M10.3 3.6 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.6a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4M12 17h.01"/>',
    trash: '<path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="M19 6l-1 15H6L5 6"/><path d="M10 11v6M14 11v6"/>',
    lock: '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
    logOut: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5"/><path d="M21 12H9"/>',
  };
  return `<svg aria-hidden="true" viewBox="0 0 24 24">${icons[name] || ""}</svg>`;
}

function statusFor(patient) {
  if (patient.cancelled) return { key: "cancelled", label: "Cancelled" };
  if (patient.pendingIssue?.trim()) return { key: "issue", label: "Issue" };
  if (patient.treatmentStarted) return { key: "started", label: "Started" };
  if (patient.simulationDone || patient.simulationDate) return { key: "simulated", label: "Simulated" };
  return { key: "new", label: "New" };
}

function consultantName(id) {
  return state.consultants.find((consultant) => consultant.id === id)?.name || "Unassigned";
}

function primaryConsultant() {
  return state.consultants.find((consultant) => consultant.primary) || state.consultants[0];
}

function filteredPatients() {
  return state.patients
    .map((patient) => ({ patient, score: scorePatient(patient, state.search) }))
    .filter(({ patient, score }) => score > 0 && (state.view === "all" || statusFor(patient).key === state.view))
    .sort((a, b) => state.search ? b.score - a.score : a.patient.name.localeCompare(b.patient.name))
    .map(({ patient }) => patient);
}

function scorePatient(patient, query) {
  if (!query) return 1;
  const q = query.toLowerCase().trim();
  const name = patient.name.toLowerCase();
  const lastSix = patient.id.slice(-6);
  if (lastSix.includes(q)) return 100 - lastSix.indexOf(q);
  if (patient.id.toLowerCase().includes(q)) return 80;
  if (name.includes(q)) return 70 - name.indexOf(q);
  let score = 0;
  let pos = 0;
  for (const char of q) {
    const index = name.indexOf(char, pos);
    if (index === -1) return 0;
    score += Math.max(1, 12 - (index - pos));
    pos = index + 1;
  }
  return score;
}

function renderLogin() {
  const params = new URLSearchParams(location.search);
  const resetToken = params.get("reset");
  document.getElementById("app").innerHTML = `
    <main class="auth-shell">
      <form class="auth-card" id="${resetToken ? "reset-form" : "login-form"}">
        <div class="auth-mark">${icon("lock")}</div>
        <h1>RT Patient Flow</h1>
        <p>${resetToken ? "Set a new password for your account." : "Sign in with your department login."}</p>
        ${state.message ? `<div class="notice">${escapeHtml(state.message)}</div>` : ""}
        ${resetToken ? `
          <input type="hidden" name="token" value="${escapeAttr(resetToken)}" />
          ${field("New password", `<input name="newPassword" type="password" minlength="8" required />`)}
          <button class="button primary wide-button">Reset password</button>
        ` : `
          ${field("Login ID", `<input name="loginId" autocomplete="username" required />`)}
          ${field("Password", `<input name="password" type="password" autocomplete="current-password" required />`)}
          <button class="button primary wide-button">Login</button>
          <button type="button" class="link-button" data-action="show-recover">Forgot password?</button>
        `}
      </form>
    </main>
    ${state.dialog === "recover" ? recoverDialog() : ""}
  `;
  bindAuth();
}

function renderApp() {
  const patients = filteredPatients();
  const selected = state.patients.find((patient) => patient.id === state.selectedId) || patients[0] || state.patients[0];
  if (selected) state.selectedId = selected.id;

  document.getElementById("app").innerHTML = `
    <header class="topbar">
      <div>
        <h1>RT Patient Flow</h1>
        <p>Radiation department patient tracker</p>
      </div>
      <div class="top-actions">
        ${canAddPatient() ? `<button class="button primary" data-action="open-add">${icon("plus")} Add Patient</button>` : ""}
        <button class="icon-button" title="Settings" data-action="open-settings">${icon("settings")}</button>
      </div>
    </header>
    <main class="shell">
      <section class="worklist">
        <div class="search-row">
          <div class="search-box">${icon("search")}<input id="search" value="${escapeAttr(state.search)}" placeholder="Search name or last 6 digits of ID" /></div>
          <select id="status-filter">${option("all", "All patients", state.view)}${option("issue", "Pending issue", state.view)}${option("started", "Started", state.view)}${option("simulated", "Simulated", state.view)}${option("cancelled", "Cancelled", state.view)}</select>
        </div>
        <div class="status-strip">
          ${statChip("All", state.patients.length, "all")}
          ${statChip("Issues", state.patients.filter((p) => statusFor(p).key === "issue").length, "issue")}
          ${statChip("Started", state.patients.filter((p) => statusFor(p).key === "started").length, "started")}
          ${statChip("Simulated", state.patients.filter((p) => statusFor(p).key === "simulated").length, "simulated")}
          ${statChip("Cancelled", state.patients.filter((p) => statusFor(p).key === "cancelled").length, "cancelled")}
        </div>
        <div class="table-wrap"><table><thead><tr><th>Patient</th><th>ID</th><th>Consultant</th><th>Machine</th><th>Simulation</th><th>Plan</th><th>Status</th></tr></thead><tbody>${patients.map((patient) => patientRow(patient, selected?.id)).join("") || emptyRow()}</tbody></table></div>
      </section>
      <section class="details">${selected ? patientDetails(selected) : emptyDetails()}</section>
    </main>
    ${renderDialog()}
  `;
  bindApp();
}

function patientRow(patient, selectedId) {
  const status = statusFor(patient);
  return `
    <tr class="patient-row ${status.key} ${selectedId === patient.id ? "selected" : ""}" data-select="${escapeAttr(patient.id)}">
      <td><strong>${escapeHtml(patient.name)}</strong><span>${escapeHtml(patient.diagnosis || "Diagnosis not entered")}</span></td>
      <td>${escapeHtml(patient.id)}<span>${escapeHtml(patient.phone || "No phone")}</span></td>
      <td>${escapeHtml(consultantName(patient.consultantId))}</td>
      <td>${escapeHtml(patient.machine || "Elekta")}</td>
      <td>${dateText(patient.simulationDate)}${patient.simulationDone ? "<span>Done</span>" : ""}</td>
      <td>${patient.planningDone ? "Done" : "Pending"}</td>
      <td><span class="status ${status.key}">${status.label}</span></td>
    </tr>`;
}

function patientDetails(patient) {
  const status = statusFor(patient);
  return `
    <div class="detail-head">
      <div class="avatar">${icon(patient.pendingIssue ? "alert" : "user")}</div>
      <div><h2>${escapeHtml(patient.name)}</h2><p>${escapeHtml(patient.id)} - ${escapeHtml(patient.diagnosis || "Diagnosis not entered")}</p></div>
      <span class="status ${status.key}">${status.label}</span>
    </div>
    <div class="form-grid" data-patient-form="${escapeAttr(patient.id)}">
      ${detailInput("Patient name", "name", patient.name)}
      ${detailInput("Patient ID", "id", patient.id)}
      ${detailInput("Phone number", "phone", patient.phone)}
      ${detailInput("Diagnosis", "diagnosis", patient.diagnosis)}
      ${detailInput("Date of first visit", "firstVisit", patient.firstVisit, "date")}
      ${detailSelect("Consultant", "consultantId", patient.consultantId, state.consultants.map((c) => [c.id, c.name]))}
      ${detailInput("Date of simulation", "simulationDate", patient.simulationDate, "date")}
      ${detailSelect("Machine", "machine", patient.machine || "Elekta", state.machines.map((m) => [m, m]))}
      ${detailSelect("Payment mode", "paymentMode", patient.paymentMode, state.paymentModes.map((m) => [m, m]))}
      ${detailInput("Tentative Date of starting", "tentativeStart", patient.tentativeStart, "date")}
    </div>
    <div class="toggle-grid">
      ${toggle("Simulation done", patient.simulationDone, "simulationDone", patient.id)}
      ${toggle("Contouring done", patient.contouringDone, "contouringDone", patient.id)}
      ${toggle("Planning done", patient.planningDone, "planningDone", patient.id)}
      ${toggle("Treatment started", patient.treatmentStarted, "treatmentStarted", patient.id)}
    </div>
    <label class="field issue-box"><span>Any pending issue</span><textarea data-issue="${escapeAttr(patient.id)}" ${can("pendingIssue") ? "" : "disabled"}>${escapeHtml(patient.pendingIssue || "")}</textarea></label>
    <div class="issue-actions">
      <button class="button" data-action="save-issue" data-id="${escapeAttr(patient.id)}" ${can("pendingIssue") ? "" : "disabled"}>${icon("check")} Update issue</button>
      <button class="button quiet" data-action="resolve-issue" data-id="${escapeAttr(patient.id)}" ${can("pendingIssue") ? "" : "disabled"}>${icon("check")} Mark issue resolved</button>
    </div>
    <div class="cancel-box ${patient.cancelled ? "active" : ""}">
      <div><strong>Treatment cancellation</strong><p>${patient.cancelled ? "Treatment is marked cancelled." : "Use only if treatment could not be done."}</p></div>
      <button class="button danger" data-action="open-cancel" data-id="${escapeAttr(patient.id)}" ${can("cancelled") ? "" : "disabled"}>${icon("x")} ${patient.cancelled ? "Update note" : "Cancel treatment"}</button>
    </div>
    ${patient.cancelled ? `<p class="cancel-note">${escapeHtml(patient.cancellationNote || "No cancellation note entered.")}</p>` : ""}
  `;
}

function detailInput(label, key, value, type = "text") {
  const readonly = key === "id" || !can(key);
  return field(label, `<input data-field="${key}" value="${escapeAttr(value || "")}" type="${type}" ${readonly ? "readonly disabled" : ""} />`);
}

function detailSelect(label, key, value, options) {
  return field(label, `<select data-field="${key}" ${can(key) ? "" : "disabled"}>${options.map(([id, text]) => option(id, text, value)).join("")}</select>`);
}

function toggle(label, checked, fieldName, id) {
  return `<label class="toggle"><input type="checkbox" data-toggle="${fieldName}" data-id="${escapeAttr(id)}" ${checked ? "checked" : ""} ${can(fieldName) ? "" : "disabled"} /><span></span><strong>${label}</strong></label>`;
}

function renderDialog() {
  if (state.dialog === "add") return addPatientDialog();
  if (state.dialog === "settings") return settingsDialog();
  if (state.dialog === "password") return passwordDialog();
  if (state.dialog?.startsWith("cancel:")) return cancelDialog(state.dialog.split(":")[1]);
  return "";
}

function addPatientDialog() {
  return `<div class="modal-backdrop"><form class="modal" id="add-form"><div class="modal-head"><h2>Add new patient</h2><button type="button" class="icon-button" data-action="close-dialog">${icon("x")}</button></div>
    ${field("Patient ID", `<input name="id" required />`)}
    ${field("Patient name", `<input name="name" required />`)}
    ${field("Phone number", `<input name="phone" />`)}
    ${field("Diagnosis", `<input name="diagnosis" />`)}
    ${field("Date of first visit", `<input name="firstVisit" type="date" value="${today()}" />`)}
    ${field("Consultant", `<select name="consultantId">${state.consultants.map((c) => option(c.id, c.name, primaryConsultant()?.id)).join("")}</select>`)}
    ${field("Machine", `<select name="machine">${state.machines.map((m) => option(m, m, "Elekta")).join("")}</select>`)}
    ${field("Payment mode", `<select name="paymentMode">${state.paymentModes.map((m) => option(m, m, "Cash")).join("")}</select>`)}
    <div class="modal-actions"><button type="button" class="button quiet" data-action="close-dialog">Cancel</button><button class="button primary">${icon("plus")} Add patient</button></div>
  </form></div>`;
}

function settingsDialog() {
  return `<div class="modal-backdrop"><div class="modal wide"><div class="modal-head"><h2>Settings</h2><button class="icon-button" data-action="close-dialog">${icon("x")}</button></div>
    <div class="settings-grid">
      ${adminSettings()}
    </div>
  </div></div>`;
}

function adminSettings() {
  return `
    <section><h3>Consultants</h3><div class="add-line"><input id="new-consultant" placeholder="Add consultant" /><button class="button" data-action="add-consultant">${icon("plus")} Add</button></div><div class="settings-list">${state.consultants.map((c) => `<div class="settings-item"><span>${escapeHtml(c.name)}</span><button class="mini ${c.primary ? "active" : ""}" data-action="primary-consultant" data-id="${escapeAttr(c.id)}">${c.primary ? "Primary" : "Set primary"}</button><button class="icon-button danger-icon" data-action="delete-consultant" data-id="${escapeAttr(c.id)}" ${state.consultants.length === 1 ? "disabled" : ""}>${icon("trash")}</button></div>`).join("")}</div></section>
    <section><h3>Payment modes</h3><div class="add-line"><input id="new-payment" placeholder="Add payment mode" /><button class="button" data-action="add-payment">${icon("plus")} Add</button></div><div class="settings-list">${state.paymentModes.map((m) => `<div class="settings-item"><span>${escapeHtml(m)}</span><button class="icon-button danger-icon" data-action="delete-payment" data-mode="${escapeAttr(m)}" ${state.paymentModes.length === 1 ? "disabled" : ""}>${icon("trash")}</button></div>`).join("")}</div></section>`;
}

function passwordDialog() {
  return `<div class="modal-backdrop"><form class="modal" id="password-form"><div class="modal-head"><h2>Change password</h2><button type="button" class="icon-button" data-action="close-dialog">${icon("x")}</button></div>${field("Current password", `<input name="currentPassword" type="password" required />`)}${field("New password", `<input name="newPassword" type="password" minlength="8" required />`)}<div class="modal-actions"><button type="button" class="button quiet" data-action="close-dialog">Cancel</button><button class="button primary">Save password</button></div></form></div>`;
}

function cancelDialog(id) {
  const patient = state.patients.find((item) => item.id === id);
  return `<div class="modal-backdrop"><form class="modal" id="cancel-form" data-id="${escapeAttr(id)}"><div class="modal-head"><h2>Cancel treatment</h2><button type="button" class="icon-button" data-action="close-dialog">${icon("x")}</button></div><p class="modal-copy">Enter why treatment could not be done.</p><label class="field"><span>Cancellation note</span><textarea name="cancellationNote" required>${escapeHtml(patient?.cancellationNote || "")}</textarea></label><div class="modal-actions"><button type="button" class="button quiet" data-action="close-dialog">Back</button><button class="button danger">${icon("x")} Save cancellation</button></div></form></div>`;
}

function recoverDialog() {
  return `<div class="modal-backdrop"><form class="modal" id="recover-form"><div class="modal-head"><h2>Password recovery</h2><button type="button" class="icon-button" data-action="close-dialog">${icon("x")}</button></div>${field("Email", `<input name="email" type="email" required />`)}<div class="modal-actions"><button class="button primary">Send recovery email</button></div></form></div>`;
}

function bindAuth() {
  document.querySelectorAll("[data-action]").forEach((el) => el.addEventListener("click", handleAction));
  document.getElementById("login-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    await run(() => api("/api/login", { method: "POST", body: Object.fromEntries(new FormData(event.currentTarget)) }).then(loadState));
  });
  document.getElementById("recover-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    await run(() => api("/api/recover", { method: "POST", body: Object.fromEntries(new FormData(event.currentTarget)) }).then((data) => { state.message = data.message; state.dialog = null; renderLogin(); }));
  });
  document.getElementById("reset-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    await run(() => api("/api/reset-password", { method: "POST", body: Object.fromEntries(new FormData(event.currentTarget)) }).then(() => { history.replaceState({}, "", location.pathname); state.message = "Password reset. Please log in."; renderLogin(); }));
  });
}

function bindApp() {
  document.getElementById("search")?.addEventListener("input", (event) => { state.search = event.target.value; renderApp(); });
  document.getElementById("status-filter")?.addEventListener("change", (event) => { state.view = event.target.value; renderApp(); });
  document.querySelectorAll("[data-view]").forEach((button) => button.addEventListener("click", () => { state.view = button.dataset.view; renderApp(); }));
  document.querySelectorAll("[data-select]").forEach((row) => row.addEventListener("click", () => { state.selectedId = row.dataset.select; renderApp(); }));
  document.querySelectorAll("[data-field]").forEach((input) => input.addEventListener("change", () => updatePatient(input.closest("[data-patient-form]").dataset.patientForm, { [input.dataset.field]: input.value })));
  document.querySelectorAll("[data-toggle]").forEach((input) => input.addEventListener("change", () => updatePatient(input.dataset.id, { [input.dataset.toggle]: input.checked })));
  document.querySelectorAll("[data-action]").forEach((el) => el.addEventListener("click", handleAction));
  document.getElementById("add-form")?.addEventListener("submit", (event) => submitForm(event, "/api/patients"));
  document.getElementById("password-form")?.addEventListener("submit", (event) => submitForm(event, "/api/change-password"));
  document.getElementById("cancel-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    await updatePatient(form.dataset.id, { cancelled: true, treatmentStarted: false, cancellationNote: new FormData(form).get("cancellationNote") });
    state.dialog = null;
  });
}

async function handleAction(event) {
  const action = event.currentTarget.dataset.action;
  const id = event.currentTarget.dataset.id;
  if (action === "show-recover") state.dialog = "recover";
  if (action === "open-add") state.dialog = "add";
  if (action === "open-settings") state.dialog = "settings";
  if (action === "open-password") state.dialog = "password";
  if (action === "close-dialog") state.dialog = null;
  if (action === "open-cancel") state.dialog = `cancel:${id}`;
  if (action === "save-issue") await updatePatient(id, { pendingIssue: document.querySelector(`[data-issue="${CSS.escape(id)}"]`)?.value || "", cancelled: false });
  if (action === "resolve-issue") await updatePatient(id, { pendingIssue: "" });
  if (action === "add-consultant") await postAndReload("/api/consultants", { name: document.getElementById("new-consultant").value });
  if (action === "primary-consultant") await run(() => api(`/api/consultants/${encodeURIComponent(id)}`, { method: "PATCH", body: { primary: true } }).then(loadState));
  if (action === "delete-consultant") await run(() => api(`/api/consultants/${encodeURIComponent(id)}`, { method: "DELETE" }).then(loadState));
  if (action === "add-payment") await postAndReload("/api/payment-modes", { name: document.getElementById("new-payment").value });
  if (action === "delete-payment") await run(() => api(`/api/payment-modes/${encodeURIComponent(event.currentTarget.dataset.mode)}`, { method: "DELETE" }).then(loadState));
  if (!["save-issue", "resolve-issue", "add-consultant", "primary-consultant", "delete-consultant", "add-payment", "delete-payment"].includes(action)) {
    renderApp();
  }
}

async function updatePatient(id, patch) {
  await run(() => api(`/api/patients/${encodeURIComponent(id)}`, { method: "PATCH", body: patch }).then(loadState));
}

async function submitForm(event, path) {
  event.preventDefault();
  await run(() => api(path, { method: "POST", body: Object.fromEntries(new FormData(event.currentTarget)) }).then(() => { state.dialog = null; return loadState(); }));
}

async function postAndReload(path, body) {
  await run(() => api(path, { method: "POST", body }).then(loadState));
}

async function run(task) {
  try {
    state.message = "";
    await task();
  } catch (error) {
    alert(error.message);
  }
}

function field(label, input) { return `<label class="field"><span>${label}</span>${input}</label>`; }
function option(value, label, selected) { return `<option value="${escapeAttr(value)}" ${value === selected ? "selected" : ""}>${escapeHtml(label)}</option>`; }
function statChip(label, count, key) { return `<button class="stat-chip ${state.view === key ? "active" : ""}" data-view="${key}"><span>${label}</span><strong>${count}</strong></button>`; }
function emptyRow() { return `<tr><td colspan="7" class="empty">No matching patients found.</td></tr>`; }
function emptyDetails() { return `<div class="empty-panel">Add a patient to begin.</div>`; }
function dateText(value) { return value ? new Date(`${value}T00:00:00`).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) : "Not set"; }
function today() { return new Date().toISOString().slice(0, 10); }
function escapeHtml(value = "") { return String(value).replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char])); }
function escapeAttr(value = "") { return escapeHtml(value); }

loadState();
