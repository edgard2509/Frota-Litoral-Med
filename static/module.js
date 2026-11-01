const sidebar = document.querySelector("#sidebar");
const menuButton = document.querySelector("#mobile-menu");
const scrim = document.querySelector("#sidebar-scrim");
const search = document.querySelector("#record-search");
const rows = [...document.querySelectorAll("#record-rows tr")];
const emptyState = document.querySelector("#empty-state");
const counter = document.querySelector("#record-count");
const dialog = document.querySelector("#record-dialog");
const form = document.querySelector("#record-form");

function closeMenu() {
  sidebar.classList.remove("sidebar-open");
  menuButton.setAttribute("aria-expanded", "false");
}

menuButton.addEventListener("click", () => {
  const open = sidebar.classList.toggle("sidebar-open");
  menuButton.setAttribute("aria-expanded", String(open));
});
scrim.addEventListener("click", closeMenu);
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeMenu();
});

search.addEventListener("input", () => {
  const query = search.value.trim().toLocaleLowerCase("pt-BR");
  let visible = 0;
  rows.forEach((row) => {
    row.hidden = !row.textContent.toLocaleLowerCase("pt-BR").includes(query);
    if (!row.hidden) visible += 1;
  });
  counter.textContent = visible;
  if (rows.length) {
    emptyState.hidden = visible !== 0;
    emptyState.textContent = "Nenhum registro encontrado para esta busca.";
  }
});

document.querySelectorAll("form[data-confirm]").forEach((deleteForm) => {
  deleteForm.addEventListener("submit", (event) => {
    if (!window.confirm(deleteForm.dataset.confirm)) event.preventDefault();
  });
});

if (dialog) {
  const title = document.querySelector("#record-title");
  const open = (record, id) => {
    form.reset();
    form.querySelectorAll("option[data-extra]").forEach((o) => o.remove());
    Object.entries(record || {}).forEach(([name, value]) => {
      const input = form.elements[name];
      if (!input) return;
      if (input.tagName === "SELECT" && value && ![...input.options].some((o) => o.value === value)) {
        const extra = new Option(value, value);
        extra.dataset.extra = "1";
        input.add(extra);
      }
      input.value = value ?? "";
    });
    form.action = id ? dialog.dataset.updateAction.replace(/0$/, id) : dialog.dataset.createAction;
    title.textContent = `${id ? "Editar" : "Novo"} ${dialog.dataset.singular}`;
    dialog.showModal();
  };

  document.querySelector("#add-record")?.addEventListener("click", () => open());
  document.querySelector("#close-record-dialog").addEventListener("click", () => dialog.close());
  document.querySelector("#cancel-record-dialog").addEventListener("click", () => dialog.close());
  document.querySelectorAll("[data-edit]").forEach((button) => {
    button.addEventListener("click", () => {
      const row = button.closest("tr");
      open(JSON.parse(row.dataset.record), row.dataset.id);
    });
  });
}
