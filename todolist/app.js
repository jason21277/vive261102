"use strict";

// ---------- Storage ----------

const STORAGE_KEY = "todayTodo.v1.todos";
const PREFS_KEY = "todayTodo.v1.prefs";
const RETENTION_DAYS = 30;
let storageAvailable = true;

function load() {
  let raw;
  try {
    raw = localStorage.getItem(STORAGE_KEY);
  } catch {
    storageAvailable = false;
    return [];
  }
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    // 손상된 데이터는 백업으로 옮기고 빈 목록으로 시작
    try {
      localStorage.setItem(STORAGE_KEY + ".backup", raw);
    } catch {}
    return [];
  }
}

function loadPrefs() {
  const defaults = { filter: "all", dismissedCarryOver: null };
  try {
    const parsed = JSON.parse(localStorage.getItem(PREFS_KEY));
    return { ...defaults, ...(parsed && typeof parsed === "object" ? parsed : {}) };
  } catch {
    return defaults;
  }
}

function save() {
  if (!storageAvailable) return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state.todos));
    localStorage.setItem(PREFS_KEY, JSON.stringify(state.prefs));
  } catch {
    storageAvailable = false;
    render();
  }
}

// ---------- Utils ----------

function todayKey(d = new Date()) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function daysAgoKey(n) {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return todayKey(d);
}

const WEEKDAYS = ["일", "월", "화", "수", "목", "금", "토"];

function formatDate(d = new Date()) {
  return `${d.getFullYear()}년 ${d.getMonth() + 1}월 ${d.getDate()}일 (${WEEKDAYS[d.getDay()]})`;
}

function newId() {
  if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
  return Date.now().toString(36) + Math.random().toString(36).slice(2);
}

const PRIORITIES = ["high", "mid", "low"];
const PRIORITY_LABEL = { high: "높음", mid: "보통", low: "낮음" };
const PRIORITY_RANK = { high: 0, mid: 1, low: 2 };

// 보관 기간이 지난 할일 정리
function pruneOld(todos) {
  const cutoff = daysAgoKey(RETENTION_DAYS);
  return todos.filter((t) => t.date >= cutoff);
}

// ---------- State ----------

const state = {
  todos: pruneOld(load()),
  prefs: loadPrefs(),
  today: todayKey(),
  editingId: null,
};

// ---------- Actions ----------

function addTodo(text, priority = "mid") {
  const trimmed = text.trim().slice(0, 100);
  if (!trimmed) return false;
  state.todos.push({
    id: newId(),
    text: trimmed,
    done: false,
    priority: PRIORITIES.includes(priority) ? priority : "mid",
    date: state.today,
    createdAt: Date.now(),
    completedAt: null,
    order: state.todos.length,
  });
  save();
  render();
  return true;
}

function toggleTodo(id) {
  const todo = state.todos.find((t) => t.id === id);
  if (!todo) return;
  todo.done = !todo.done;
  todo.completedAt = todo.done ? Date.now() : null;
  save();
  render();
}

function editTodo(id, text) {
  const todo = state.todos.find((t) => t.id === id);
  if (!todo) return;
  todo.text = text.trim().slice(0, 100);
  save();
}

function cyclePriority(id) {
  const todo = state.todos.find((t) => t.id === id);
  if (!todo) return;
  todo.priority = PRIORITIES[(PRIORITIES.indexOf(todo.priority) + 1) % PRIORITIES.length];
  save();
  render();
}

function deleteTodo(id) {
  state.todos = state.todos.filter((t) => t.id !== id);
  save();
  render();
}

function clearCompleted() {
  state.todos = state.todos.filter((t) => !(t.date === state.today && t.done));
  save();
  render();
}

function setFilter(filter) {
  state.prefs.filter = filter;
  save();
  render();
}

function carryOver() {
  const source = carryOverSource();
  if (source) {
    const now = Date.now();
    source.todos.forEach((t, i) => {
      state.todos.push({
        ...t,
        id: newId(),
        date: state.today,
        createdAt: now + i,
        completedAt: null,
        order: state.todos.length,
      });
    });
  }
  dismissCarryOver();
}

function dismissCarryOver() {
  state.prefs.dismissedCarryOver = state.today;
  save();
  render();
}

// ---------- Selectors ----------

function sortTodos(a, b) {
  return (
    Number(a.done) - Number(b.done) ||
    (PRIORITY_RANK[a.priority] ?? 1) - (PRIORITY_RANK[b.priority] ?? 1) ||
    a.createdAt - b.createdAt
  );
}

function todayTodos() {
  return state.todos.filter((t) => t.date === state.today).sort(sortTodos);
}

function visibleTodos() {
  const list = todayTodos();
  if (state.prefs.filter === "active") return list.filter((t) => !t.done);
  if (state.prefs.filter === "done") return list.filter((t) => t.done);
  return list;
}

function progress() {
  const list = todayTodos();
  const done = list.filter((t) => t.done).length;
  const total = list.length;
  return { done, total, percent: total ? Math.round((done / total) * 100) : 0 };
}

// 가장 최근 과거 날짜의 미완료 항목
function carryOverSource() {
  const past = state.todos.filter((t) => t.date < state.today && !t.done);
  if (!past.length) return null;
  const date = past.reduce((max, t) => (t.date > max ? t.date : max), past[0].date);
  return { date, todos: past.filter((t) => t.date === date).sort(sortTodos) };
}

// ---------- View ----------

const el = {
  date: document.getElementById("today-date"),
  notice: document.getElementById("storage-notice"),
  progress: document.getElementById("progress"),
  progressBar: document.getElementById("progress-bar"),
  progressFill: document.getElementById("progress-fill"),
  progressText: document.getElementById("progress-text"),
  banner: document.getElementById("carry-banner"),
  bannerText: document.getElementById("carry-text"),
  bannerImport: document.getElementById("carry-import"),
  bannerDismiss: document.getElementById("carry-dismiss"),
  form: document.getElementById("todo-form"),
  input: document.getElementById("todo-input"),
  prio: document.getElementById("prio-select"),
  filters: document.getElementById("filters"),
  list: document.getElementById("todo-list"),
  empty: document.getElementById("empty-state"),
  footer: document.getElementById("footer"),
  remaining: document.getElementById("remaining"),
  clearDone: document.getElementById("clear-done"),
};

const EMPTY_MESSAGE = {
  all: "오늘 할 일을 추가해보세요",
  active: "남은 할일이 없어요. 다 끝냈어요!",
  done: "완료한 할일이 아직 없어요",
};

function renderItem(todo) {
  const li = document.createElement("li");
  li.className = "todo-item" + (todo.done ? " done" : "");
  li.dataset.id = todo.id;

  const check = document.createElement("input");
  check.type = "checkbox";
  check.className = "todo-check";
  check.checked = todo.done;
  check.setAttribute("aria-label", `${todo.text} 완료`);

  const prio = document.createElement("button");
  prio.type = "button";
  prio.className = `prio-dot prio-${todo.priority}`;
  prio.title = `우선순위 ${PRIORITY_LABEL[todo.priority]} (클릭해서 변경)`;
  prio.setAttribute("aria-label", `우선순위 ${PRIORITY_LABEL[todo.priority]}, 눌러서 변경`);

  let text;
  if (todo.id === state.editingId) {
    text = document.createElement("input");
    text.type = "text";
    text.className = "edit-input";
    text.maxLength = 100;
    text.value = todo.text;
    text.setAttribute("aria-label", "할일 수정");
  } else {
    text = document.createElement("span");
    text.className = "todo-text";
    text.tabIndex = 0;
    text.textContent = todo.text;
    text.title = "더블클릭하거나 Enter로 수정";
  }

  const del = document.createElement("button");
  del.type = "button";
  del.className = "delete-btn";
  del.textContent = "×";
  del.setAttribute("aria-label", `${todo.text} 삭제`);

  li.append(check, prio, text, del);
  return li;
}

function render() {
  el.date.textContent = formatDate();
  el.notice.hidden = storageAvailable;

  const source = state.prefs.dismissedCarryOver === state.today ? null : carryOverSource();
  el.banner.hidden = !source;
  if (source) {
    const [, m, d] = source.date.split("-").map(Number);
    const when = source.date === daysAgoKey(1) ? "어제" : `${m}월 ${d}일에`;
    el.bannerText.textContent = `${when} 못 끝낸 할일 ${source.todos.length}개가 있어요`;
  }

  const filter = state.prefs.filter;
  for (const btn of el.filters.querySelectorAll(".filter-btn")) {
    btn.setAttribute("aria-pressed", String(btn.dataset.filter === filter));
  }

  const all = todayTodos();
  const list = visibleTodos();
  el.list.replaceChildren(...list.map(renderItem));
  el.empty.hidden = list.length > 0;
  el.empty.textContent = all.length === 0 ? EMPTY_MESSAGE.all : EMPTY_MESSAGE[filter];

  const p = progress();
  el.progress.hidden = p.total === 0;
  el.progressFill.style.width = p.percent + "%";
  el.progressBar.setAttribute("aria-valuenow", String(p.percent));
  el.progressText.textContent = `${p.done} / ${p.total} 완료 (${p.percent}%)`;

  el.footer.hidden = p.total === 0;
  el.remaining.textContent = `남은 할일 ${p.total - p.done}개`;
  el.clearDone.disabled = p.done === 0;

  if (state.editingId) {
    const input = el.list.querySelector(".edit-input");
    if (input) {
      input.focus();
      input.setSelectionRange(input.value.length, input.value.length);
    }
  }
}

// ---------- Editing ----------

function startEdit(id) {
  state.editingId = id;
  render();
}

function finishEdit(commit) {
  const id = state.editingId;
  if (!id) return;
  const input = el.list.querySelector(".edit-input");
  state.editingId = null;

  if (commit && input) {
    const value = input.value.trim();
    if (!value) {
      if (confirm("내용이 비어 있어요. 이 할일을 삭제할까요?")) {
        deleteTodo(id);
        return;
      }
    } else {
      editTodo(id, value);
    }
  }
  render();
  const span = el.list.querySelector(`[data-id="${CSS.escape(id)}"] .todo-text`);
  if (span) span.focus();
}

// ---------- Events ----------

el.form.addEventListener("submit", (e) => {
  e.preventDefault();
  if (addTodo(el.input.value, el.prio.value)) el.input.value = "";
  el.input.focus();
});

el.filters.addEventListener("click", (e) => {
  const btn = e.target.closest(".filter-btn");
  if (btn) setFilter(btn.dataset.filter);
});

el.bannerImport.addEventListener("click", carryOver);
el.bannerDismiss.addEventListener("click", dismissCarryOver);

el.clearDone.addEventListener("click", () => {
  const count = progress().done;
  if (count && confirm(`완료한 할일 ${count}개를 지울까요?`)) clearCompleted();
});

// 목록은 이벤트 위임으로 한 번만 등록
el.list.addEventListener("change", (e) => {
  if (!e.target.classList.contains("todo-check")) return;
  toggleTodo(e.target.closest(".todo-item").dataset.id);
});

el.list.addEventListener("click", (e) => {
  const item = e.target.closest(".todo-item");
  if (!item) return;
  if (e.target.closest(".delete-btn")) {
    deleteTodo(item.dataset.id);
    el.input.focus();
  } else if (e.target.closest(".prio-dot")) {
    cyclePriority(item.dataset.id);
    el.list.querySelector(`[data-id="${CSS.escape(item.dataset.id)}"] .prio-dot`)?.focus();
  }
});

el.list.addEventListener("dblclick", (e) => {
  const text = e.target.closest(".todo-text");
  if (text) startEdit(text.closest(".todo-item").dataset.id);
});

el.list.addEventListener("keydown", (e) => {
  if (e.target.classList.contains("edit-input")) {
    if (e.key === "Enter" && !e.isComposing) {
      e.preventDefault();
      finishEdit(true);
    } else if (e.key === "Escape") {
      e.preventDefault();
      finishEdit(false);
    }
    return;
  }
  const item = e.target.closest(".todo-item");
  if (!item) return;
  if (e.key === "Enter" && e.target.classList.contains("todo-text")) {
    e.preventDefault();
    startEdit(item.dataset.id);
  } else if (e.key === "Delete") {
    e.preventDefault();
    deleteTodo(item.dataset.id);
    el.input.focus();
  }
});

// 편집 중 다른 곳을 누르면 저장
el.list.addEventListener("focusout", (e) => {
  if (e.target.classList.contains("edit-input") && state.editingId) finishEdit(true);
});

// 다른 탭에서 바뀐 내용 반영
window.addEventListener("storage", (e) => {
  if (e.key !== STORAGE_KEY && e.key !== PREFS_KEY) return;
  state.todos = load();
  state.prefs = loadPrefs();
  render();
});

// 탭을 열어둔 채 자정이 지나면 날짜 갱신
function checkDateChange() {
  const now = todayKey();
  if (now === state.today) return;
  state.today = now;
  state.editingId = null;
  render();
}
setInterval(checkDateChange, 60 * 1000);
document.addEventListener("visibilitychange", () => {
  if (!document.hidden) checkDateChange();
});

render();
