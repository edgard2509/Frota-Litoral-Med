const pages = {
  "visao-geral": {
    title: "Visão geral",
    description: "Acompanhe os principais indicadores da frota.",
  },
  veiculos: { title: "Veículos", description: "Consulte os veículos da frota e sua disponibilidade." },
  movimentacoes: { title: "Movimentações", description: "Acompanhe as movimentações e solicitações da frota." },
  manutencoes: { title: "Manutenções", description: "Acompanhe os serviços e planos de manutenção." },
  licenciamentos: { title: "Licenciamentos", description: "Consulte documentos e prazos de licenciamento." },
  seguros: { title: "Seguros", description: "Consulte as apólices e vigências dos veículos." },
  sinistros: { title: "Sinistros", description: "Acompanhe ocorrências registradas na frota." },
  usuarios: { title: "Usuários", description: "Gerencie os acessos e as permissões do sistema." },
};

const title = document.querySelector("#page-title");
const description = document.querySelector("#page-description");
const breadcrumb = document.querySelector("#breadcrumb-current");
const search = document.querySelector("#user-search");
const rows = [...document.querySelectorAll("#user-rows tr")];
const emptyState = document.querySelector("#empty-state");
const userCount = document.querySelector("#user-count");
const userCountDetail = document.querySelector("#user-count-detail");
const visibleRange = document.querySelector("#visible-range");
const totalCount = document.querySelector("#total-count");
const pagination = document.querySelector("#user-pagination");
const pageNumbers = document.querySelector("#page-numbers");
const filterButton = document.querySelector("#filter-button");
const sidebar = document.querySelector("#sidebar");
const menuButton = document.querySelector("#mobile-menu");
const scrim = document.querySelector("#sidebar-scrim");
const pageSize = 5;
let currentPage = 1;
let activeOnly = false;

function showPage(pageName) {
  const page = pages[pageName] || pages.usuarios;
  title.textContent = page.title;
  description.textContent = page.description;
  breadcrumb.textContent = page.title;
  document.querySelectorAll(".nav-link").forEach((link) => {
    const active = link.dataset.page === pageName;
    link.classList.toggle("active", active);
    if (active) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  });
  const showUsers = pageName === "usuarios";
  document.querySelector("#users-panel").hidden = !showUsers;
  document.querySelector("#dashboard-details").hidden = showUsers;
  sidebar.classList.remove("sidebar-open");
  menuButton.setAttribute("aria-expanded", "false");
}

document.querySelectorAll("[data-page], .brand").forEach((link) => {
  link.addEventListener("click", (event) => {
    const pageName = link.dataset.page || link.getAttribute("href")?.slice(1) || "visao-geral";
    if (!pages[pageName]) return;
    event.preventDefault();
    history.replaceState(null, "", `#${pageName}`);
    showPage(pageName);
  });
});

function updateUserList() {
  const query = search.value.trim().toLocaleLowerCase("pt-BR");
  const filteredRows = rows.filter((row) => {
    const matchesSearch = `${row.dataset.search} ${row.textContent}`
      .toLocaleLowerCase("pt-BR")
      .includes(query);
    const matchesStatus = !activeOnly || !row.querySelector(".status-inactive");
    return matchesSearch && matchesStatus;
  });
  const pageCount = Math.ceil(filteredRows.length / pageSize);
  currentPage = Math.min(currentPage, pageCount || 1);
  const startIndex = (currentPage - 1) * pageSize;
  const visibleRows = new Set(filteredRows.slice(startIndex, startIndex + pageSize));

  rows.forEach((row) => {
    row.hidden = !visibleRows.has(row);
  });
  emptyState.hidden = filteredRows.length > 0;
  const countLabel = `${filteredRows.length} ${filteredRows.length === 1 ? "usuário" : "usuários"}`;
  userCount.textContent = countLabel;
  totalCount.textContent = countLabel;
  userCountDetail.textContent = activeOnly ? " · Acessos ativos" : " · Lista de acessos";
  visibleRange.textContent = filteredRows.length
    ? `${startIndex + 1}–${Math.min(startIndex + pageSize, filteredRows.length)}`
    : "0–0";

  pagination.querySelector('[data-page-action="previous"]').disabled = currentPage <= 1;
  pagination.querySelector('[data-page-action="next"]').disabled = currentPage >= pageCount;
  pageNumbers.replaceChildren();
  for (let page = 1; page <= pageCount; page += 1) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = String(page);
    button.setAttribute("aria-label", `Página ${page}`);
    if (page === currentPage) {
      button.classList.add("current-page");
      button.setAttribute("aria-current", "page");
    }
    button.addEventListener("click", () => {
      currentPage = page;
      updateUserList();
    });
    pageNumbers.append(button);
  }
}

search.addEventListener("input", () => {
  currentPage = 1;
  updateUserList();
});

menuButton.addEventListener("click", () => {
  const open = sidebar.classList.toggle("sidebar-open");
  menuButton.setAttribute("aria-expanded", String(open));
});

scrim.addEventListener("click", () => {
  sidebar.classList.remove("sidebar-open");
  menuButton.setAttribute("aria-expanded", "false");
});

document.querySelector("#add-user").addEventListener("click", () => {
  window.alert("A inclusão de usuários deve ser realizada pela administração do sistema.");
});

filterButton.addEventListener("click", () => {
  activeOnly = !activeOnly;
  currentPage = 1;
  filterButton.setAttribute("aria-pressed", String(activeOnly));
  updateUserList();
});

pagination.addEventListener("click", (event) => {
  const action = event.target.closest("[data-page-action]")?.dataset.pageAction;
  if (!action) return;
  currentPage += action === "next" ? 1 : -1;
  updateUserList();
});

document.addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
    event.preventDefault();
    search.focus();
  }
  if (event.key === "Escape") {
    sidebar.classList.remove("sidebar-open");
    menuButton.setAttribute("aria-expanded", "false");
  }
});

showPage(window.location.hash.slice(1) || "usuarios");
updateUserList();
