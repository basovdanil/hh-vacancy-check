// hh-vacancy-check demo: snapshot table, id lookup and pasted-page parsing.
// The parsing rule mirrors vacancy_check.py: find the schema.org JobPosting block and
// compare validThrough with the current time.

const LABELS = {
  open: "OPEN",
  closed: "CLOSED",
  unknown: "UNKNOWN",
};

let snapshot = { items: [], generated_at: null };

function chip(status) {
  const kind = LABELS[status] ? status : "unknown";
  return `<span class="chip ${kind}">${LABELS[kind]}</span>`;
}

function dateOnly(value) {
  return value ? value.slice(0, 10) : "—";
}

function show(box, html) {
  box.innerHTML = html;
  box.classList.add("show");
}

function vacancyId(raw) {
  const match = String(raw).match(/(\d{6,})/);
  return match ? match[1] : null;
}

function renderSnapshot() {
  const rows = document.getElementById("rows");
  const note = document.getElementById("snapshot-note");
  if (!snapshot.items.length) {
    note.textContent = "Снимок не загрузился — используйте CLI или разбор исходника.";
    rows.innerHTML = "";
    return;
  }
  const when = snapshot.generated_at ? new Date(snapshot.generated_at).toLocaleString("ru-RU") : "—";
  note.textContent = `Собрано ${when}. Источник — публичная страница вакансии, поле validThrough.`;
  rows.innerHTML = snapshot.items.map((item) => `
    <tr>
      <td><a href="${item.url}" rel="noopener">${item.title || "без названия"}</a><br>
        <span style="color:#5B7186;font-size:13px">${item.employer || ""} · ${item.id}</span></td>
      <td>${dateOnly(item.valid_through)}</td>
      <td>${chip(item.status)}</td>
    </tr>`).join("");
}

function checkById() {
  const box = document.getElementById("verdict");
  const raw = document.getElementById("vid").value.trim();
  const id = vacancyId(raw);
  if (!id) {
    show(box, "<b>Не вижу id.</b> Вставьте номер вакансии или ссылку вида https://hh.ru/vacancy/139441388.");
    return;
  }
  const found = snapshot.items.find((item) => item.id === id);
  const command = `python vacancy_check.py ${id}`;
  if (found) {
    show(box, `${chip(found.status)} <b>${found.title || id}</b><br>
      Дедлайн: ${dateOnly(found.valid_through)}${found.note ? " · " + found.note : ""}<br>
      <a href="${found.url}" rel="noopener">открыть вакансию</a> · команда: <code>${command}</code>`);
    return;
  }
  show(box, `${id} нет в недельном снимке (в нём пять вакансий).<br>
    Проверить прямо сейчас: <code>${command}</code><br>
    <a href="https://hh.ru/vacancy/${id}" rel="noopener">открыть вакансию на hh.ru</a> ·
    вставьте исходник страницы ниже, чтобы разобрать без установки.`);
}

function parsePasted() {
  const box = document.getElementById("parsed");
  const html = document.getElementById("html").value;
  if (!html.trim()) {
    show(box, "<b>Пусто.</b> Откройте страницу вакансии, нажмите Ctrl+U, затем Ctrl+A и Ctrl+C.");
    return;
  }

  let posting = null;
  const blocks = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g) || [];
  for (const block of blocks) {
    const json = block.replace(/^<script[^>]*>/, "").replace(/<\/script>$/, "");
    try {
      const data = JSON.parse(json);
      if (data && data["@type"] === "JobPosting") {
        posting = data;
        break;
      }
    } catch (error) {
      // broken JSON-LD is simply skipped, same as in the CLI
    }
  }

  if (!posting) {
    show(box, `${chip("closed")} <b>Блока JobPosting нет.</b> Значит, hh снял вакансию с публикации:
      у закрытых карточек блок удаляется. Проверьте, что скопирован исходный код именно карточки
      вакансии, а не страница поиска.`);
    return;
  }

  if (!posting.validThrough) {
    show(box, `${chip("unknown")} <b>${posting.title || "вакансия"}</b><br>
      В блоке нет поля validThrough — статус не определить.`);
    return;
  }

  const deadline = new Date(posting.validThrough);
  const isOpen = deadline.getTime() > Date.now();
  const status = isOpen ? "open" : "closed";
  const employer = posting.hiringOrganization && posting.hiringOrganization.name;
  show(box, `${chip(status)} <b>${posting.title || "вакансия"}</b>${employer ? " · " + employer : ""}<br>
    Дедлайн: ${dateOnly(posting.validThrough)}${isOpen ? " (ещё не прошёл)" : " (прошёл)"}<br>
    Опубликовано: ${dateOnly(posting.datePosted)}`);
}

function boot() {
  document.getElementById("check").addEventListener("click", checkById);
  document.getElementById("parse").addEventListener("click", parsePasted);
  document.getElementById("clear").addEventListener("click", () => {
    document.getElementById("html").value = "";
    document.getElementById("parsed").classList.remove("show");
  });
  document.getElementById("vid").addEventListener("keydown", (event) => {
    if (event.key === "Enter") checkById();
  });

  fetch("data.json", { cache: "no-store" })
    .then((response) => (response.ok ? response.json() : Promise.reject(response.status)))
    .then((data) => {
      snapshot = data;
      renderSnapshot();
    })
    .catch(() => renderSnapshot());
}

document.addEventListener("DOMContentLoaded", boot);
