// DemoPort — data/*.json 을 읽어 각 섹션을 렌더링한다.
// JSON 을 fetch 하므로 file:// 이 아닌 로컬 서버(python -m http.server)로 열어야 한다.

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

// 요소 생성 헬퍼: 텍스트는 항상 textContent 로 넣어 HTML 주입을 막는다.
function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === "text") node.textContent = value;
    else if (key === "class") node.className = value;
    else node.setAttribute(key, value);
  }
  for (const child of [].concat(children)) {
    if (child) node.append(child);
  }
  return node;
}

async function loadJSON(name) {
  const res = await fetch(`data/${name}.json`);
  if (!res.ok) throw new Error(`${name}.json 로드 실패 (${res.status})`);
  return res.json();
}

// ===== Render =====
function renderProfile(profile) {
  $$("[data-bind]").forEach((node) => {
    node.textContent = profile[node.dataset.bind] ?? "";
  });

  $$('[data-list="focus"]').forEach((list) => {
    list.replaceChildren(...profile.focus.map((f) => el("li", { class: "tag", text: f })));
  });

  $('[data-list="about"]').replaceChildren(...profile.about.map((p) => el("p", { text: p })));

  $('[data-list="stats"]').replaceChildren(
    ...profile.stats.map((s) =>
      el("div", { class: "stat" }, [el("dt", { text: s.label }), el("dd", { text: s.value })])
    )
  );

  const mailto = `mailto:${profile.email}`;
  const emailLink = $("[data-bind-email]");
  emailLink.href = mailto;
  emailLink.textContent = profile.email;
  $("[data-bind-mailto]").href = mailto;

  // URL 이 비어 있는 링크는 표시하지 않는다.
  $("#footer-links").replaceChildren(
    ...profile.links
      .filter((l) => l.url)
      .map((l) => el("li", {}, el("a", { href: l.url, target: "_blank", rel: "noopener", text: l.label })))
  );

  setupCopyEmail(profile.email);
}

function renderSkills(skills) {
  $("#skills-grid").replaceChildren(
    ...skills.map((group) =>
      el("article", { class: "skill-card" }, [
        el("h3", { text: group.category }),
        el("ul", {}, group.items.map((item) => el("li", { text: item }))),
      ])
    )
  );
}

function renderProjects(projects) {
  const cards = projects.map((p) => {
    const links = [];
    if (p.links?.demo) links.push(el("a", { href: p.links.demo, target: "_blank", rel: "noopener", text: "Demo ↗" }));
    if (p.links?.github) links.push(el("a", { href: p.links.github, target: "_blank", rel: "noopener", text: "GitHub ↗" }));

    const card = el("article", { class: "project-card" }, [
      el("p", { class: "project-meta", text: `${p.period} · ${p.role}` }),
      el("h3", { text: p.title }),
      el("dl", { class: "project-psr" }, [
        el("dt", { text: "Problem" }), el("dd", { text: p.problem }),
        el("dt", { text: "Solution" }), el("dd", { text: p.solution }),
        el("dt", { text: "Result" }), el("dd", { text: p.result }),
      ]),
      el("ul", { class: "tag-list" }, p.tags.map((t) => el("li", { class: "tag", text: t }))),
      links.length ? el("div", { class: "project-links" }, links) : null,
    ]);
    card.dataset.tags = p.tags.join(",");
    return card;
  });
  $("#projects-grid").replaceChildren(...cards);

  // 필터 버튼: All + 프로젝트에 등장하는 태그
  const tags = ["All", ...new Set(projects.flatMap((p) => p.tags))];
  const buttons = tags.map((tag) =>
    el("button", { type: "button", "aria-pressed": String(tag === "All"), text: tag })
  );
  buttons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const tag = btn.textContent;
      buttons.forEach((b) => b.setAttribute("aria-pressed", String(b === btn)));
      cards.forEach((card) => {
        card.hidden = tag !== "All" && !card.dataset.tags.split(",").includes(tag);
      });
    });
  });
  $("#project-filter").replaceChildren(...buttons);
}

function renderExperience(items) {
  $("#timeline").replaceChildren(
    ...items.map((item) =>
      el("li", { class: "timeline-item" }, [
        el("p", { class: "timeline-period", text: item.period }),
        el("h3", { text: item.company }),
        el("p", { class: "timeline-role", text: item.role }),
        el("ul", {}, item.highlights.map((h) => el("li", { text: h }))),
      ])
    )
  );
}

// ===== Interactions =====
function setupCopyEmail(email) {
  const status = $("#copy-status");
  $("#copy-email").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(email);
      status.textContent = "이메일 주소를 복사했습니다.";
    } catch {
      status.textContent = email;
    }
    setTimeout(() => (status.textContent = ""), 2500);
  });
}

function setupTheme() {
  const root = document.documentElement;
  $(".theme-toggle").addEventListener("click", () => {
    const current = root.dataset.theme
      || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    const next = current === "dark" ? "light" : "dark";
    root.dataset.theme = next;
    try { localStorage.setItem("theme", next); } catch {}
  });
}

function setupNav() {
  const toggle = $(".nav-toggle");
  const menu = $("#nav-menu");
  const setOpen = (open) => {
    menu.classList.toggle("open", open);
    toggle.setAttribute("aria-expanded", String(open));
    toggle.setAttribute("aria-label", open ? "메뉴 닫기" : "메뉴 열기");
  };
  toggle.addEventListener("click", () => setOpen(!menu.classList.contains("open")));
  $$("a", menu).forEach((a) => a.addEventListener("click", () => setOpen(false)));

  // 현재 보고 있는 섹션을 메뉴에 표시
  const links = new Map($$("a", menu).map((a) => [a.getAttribute("href").slice(1), a]));
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        links.forEach((a) => a.classList.remove("active"));
        links.get(entry.target.id)?.classList.add("active");
      });
    },
    { rootMargin: "-45% 0px -50% 0px" }
  );
  $$("main section[id]").forEach((section) => observer.observe(section));
}

// ===== Init =====
async function init() {
  $("#year").textContent = new Date().getFullYear();
  setupTheme();
  setupNav();

  try {
    const [profile, skills, projects, experience] = await Promise.all(
      ["profile", "skills", "projects", "experience"].map(loadJSON)
    );
    renderProfile(profile);
    renderSkills(skills);
    renderProjects(projects);
    renderExperience(experience);
  } catch (err) {
    console.error(err);
    $("#main").prepend(
      el("p", {
        class: "container",
        style: "padding:16px;color:#b42318",
        text: "데이터를 불러오지 못했습니다. 로컬 서버(python -m http.server)로 열었는지 확인하세요.",
      })
    );
  }
}

init();
