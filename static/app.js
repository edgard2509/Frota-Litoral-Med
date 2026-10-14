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
const sidebar = document.querySelector("#sidebar");
const menuButton = document.querySelector("#mobile-menu");
const scrim = document.querySelector("#sidebar-scrim");

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

search.addEventListener("input", () => {
  const query = search.value.trim().toLocaleLowerCase("pt-BR");
  let visible = 0;
  rows.forEach((row) => {
    const matches = row.dataset.search.includes(query);
    row.hidden = !matches;
    if (matches) visible += 1;
  });
  emptyState.hidden = visible !== 0;
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

document.querySelector("#filter-button").addEventListener("click", () => {
  const inactive = rows.find((row) => row.querySelector(".status-inactive"));
  if (!inactive) return;
  const showOnlyActive = !inactive.hidden;
  rows.forEach((row) => {
    row.hidden = showOnlyActive && row === inactive;
  });
  emptyState.hidden = true;
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
