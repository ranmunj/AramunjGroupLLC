const tokenForm = document.querySelector("#tokenForm");
const adminToken = document.querySelector("#adminToken");
const authPanel = document.querySelector("#authPanel");
const dashboard = document.querySelector("#dashboard");
const authStatus = document.querySelector("#authStatus");
const syncStatus = document.querySelector("#syncStatus");
const leadList = document.querySelector("#leadList");
const leadDetail = document.querySelector("#leadDetail");
const refreshButton = document.querySelector("#refreshButton");
const lockButton = document.querySelector("#lockButton");
const searchInput = document.querySelector("#searchInput");
const totalCount = document.querySelector("#totalCount");
const latestDate = document.querySelector("#latestDate");
const storageType = document.querySelector("#storageType");

const tokenKey = "aramunjInquiryToken";
let leads = [];
let activeLeadId = null;

const escapeHtml = (value = "") =>
  String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

const formatDate = (value) => {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
};

const currentToken = () => sessionStorage.getItem(tokenKey) || "";

const filteredLeads = () => {
  const term = searchInput.value.trim().toLowerCase();
  if (!term) return leads;
  return leads.filter((lead) =>
    [
      lead.name,
      lead.company,
      lead.email,
      lead.phone,
      lead.country,
      lead.project_type,
      lead.message,
    ]
      .join(" ")
      .toLowerCase()
      .includes(term),
  );
};

const renderList = () => {
  const visible = filteredLeads();
  totalCount.textContent = String(leads.length);
  latestDate.textContent = leads[0] ? formatDate(leads[0].created_at) : "-";

  if (!visible.length) {
    leadList.innerHTML = '<p class="empty-state">No inquiries found.</p>';
    leadDetail.innerHTML = '<p class="empty-state">Select an inquiry to view details.</p>';
    return;
  }

  if (!activeLeadId || !visible.some((lead) => String(lead.id) === String(activeLeadId))) {
    activeLeadId = visible[0].id;
  }

  leadList.innerHTML = visible
    .map(
      (lead) => `
        <button class="lead-item ${String(lead.id) === String(activeLeadId) ? "is-active" : ""}" data-id="${escapeHtml(lead.id)}" type="button">
          <strong>${escapeHtml(lead.name || "Unnamed inquiry")}</strong>
          <span>${escapeHtml(lead.company || lead.organization || lead.email || "No organization")}</span>
          <span>${escapeHtml(lead.project_type || "General inquiry")}</span>
          <time>${escapeHtml(formatDate(lead.created_at))}</time>
        </button>
      `,
    )
    .join("");

  renderDetail(visible.find((lead) => String(lead.id) === String(activeLeadId)));
};

const detailPair = (label, value) => `
  <div>
    <span>${escapeHtml(label)}</span>
    <strong>${escapeHtml(value || "-")}</strong>
  </div>
`;

const renderDetail = (lead) => {
  if (!lead) {
    leadDetail.innerHTML = '<p class="empty-state">Select an inquiry to view details.</p>';
    return;
  }

  leadDetail.innerHTML = `
    <h1>${escapeHtml(lead.name || "Unnamed inquiry")}</h1>
    <p class="meta">${escapeHtml(formatDate(lead.created_at))}</p>
    <div class="detail-grid">
      ${detailPair("Company", lead.company)}
      ${detailPair("Organization", lead.organization)}
      ${detailPair("Email", lead.email)}
      ${detailPair("Phone", lead.phone)}
      ${detailPair("Country", lead.country)}
      ${detailPair("Project Type", lead.project_type)}
      ${detailPair("Budget", lead.budget)}
      ${detailPair("Source", lead.source)}
    </div>
    <div class="message-box">
      <span>Message</span>
      <p>${escapeHtml(lead.message)}</p>
    </div>
  `;
};

const loadLeads = async () => {
  const token = currentToken();
  if (!token) return;

  syncStatus.textContent = "Syncing inquiries...";
  const response = await fetch("/api/leads?limit=250", {
    headers: { Authorization: `Bearer ${token}` },
  });
  const result = await response.json();
  if (!response.ok) {
    throw new Error(result.error || "Unable to sync inquiries.");
  }

  leads = result.leads || [];
  storageType.textContent = result.storage || "-";
  renderList();
  syncStatus.textContent = `Last synced ${formatDate(new Date().toISOString())}`;
};

const openDashboard = async () => {
  authStatus.textContent = "";
  authPanel.hidden = true;
  dashboard.hidden = false;
  try {
    await loadLeads();
  } catch (error) {
    dashboard.hidden = true;
    authPanel.hidden = false;
    authStatus.textContent = error.message;
    sessionStorage.removeItem(tokenKey);
  }
};

tokenForm.addEventListener("submit", (event) => {
  event.preventDefault();
  sessionStorage.setItem(tokenKey, adminToken.value.trim());
  adminToken.value = "";
  openDashboard();
});

refreshButton.addEventListener("click", () => {
  loadLeads().catch((error) => {
    syncStatus.textContent = error.message;
  });
});

lockButton.addEventListener("click", () => {
  sessionStorage.removeItem(tokenKey);
  leads = [];
  activeLeadId = null;
  dashboard.hidden = true;
  authPanel.hidden = false;
});

searchInput.addEventListener("input", renderList);

leadList.addEventListener("click", (event) => {
  const button = event.target.closest(".lead-item");
  if (!button) return;
  activeLeadId = button.dataset.id;
  renderList();
});

if (currentToken()) {
  openDashboard();
}
