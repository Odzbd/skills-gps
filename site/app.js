import { jobsFor, match, pairedWith, rankSkills, rolesFor } from "./rank.js";

const PAGE_SIZE = 20;
const MIN_ROLE_JOBS = 100;
const STORAGE_KEY = "skills-gps";

const $ = (id) => document.getElementById(id);
const percent = (x) => (x > 0 && x < 0.01 ? "<1%" : `${Math.round(x * 100)}%`);
const number = (x) => x.toLocaleString("en");

let data, names, groups, rolesShown;
const state = { role: null, group: "technical", search: "", owned: new Set(), open: null, shown: PAGE_SIZE };

start().catch(() => {
  $("status").textContent = "The data could not be loaded. Reload the page to try again.";
});

async function start() {
  const response = await fetch("data.json");
  if (!response.ok) throw new Error(response.status);
  data = await response.json();
  names = data.skills.map(([name]) => name);
  groups = [...new Set(data.skills.map(([, group]) => group))];
  rolesShown = findRoles();

  fillFilters();
  restore();
  listen();
  $("status").hidden = true;
  document.querySelector("main").hidden = false;
  $("stamp").textContent =
    `${number(data.jobSkills.length)} postings from ${number(data.companies)} employers, updated ${data.date}.`;
  render();
}

function findRoles() {
  const counts = data.roles.map(() => 0);
  for (const role of data.jobRole) counts[role]++;
  return data.roles
    .map((name, id) => ({ name, id, count: counts[id] }))
    .filter((r) => r.name !== "Other" && r.count >= MIN_ROLE_JOBS)
    .sort((a, b) => a.name.localeCompare(b.name));
}

function fillFilters() {
  $("role").append(
    new Option("All roles", ""),
    ...rolesShown.map((r) => new Option(`${r.name} (${number(r.count)})`, r.id)),
  );
  $("group").append(
    new Option("All except people skills", "technical"),
    new Option("All", ""),
    ...groups.map((g) => new Option(g, g)),
  );
}

// State lives in the URL, so any view can be shared; browser storage remembers the last one.

function restore() {
  const saved = location.hash.length > 1 ? location.hash.slice(1) : load();
  const params = new URLSearchParams(saved);
  const role = rolesShown.find((r) => r.name === params.get("role"));
  state.role = role ? role.id : null;
  state.owned = new Set(
    params.getAll("have").map((name) => names.indexOf(name)).filter((id) => id >= 0),
  );
  $("role").value = state.role ?? "";
  $("group").value = state.group;
}

function persist() {
  const params = new URLSearchParams();
  if (state.role !== null) params.set("role", data.roles[state.role]);
  for (const skill of state.owned) params.append("have", names[skill]);
  const text = params.toString();
  history.replaceState(null, "", text ? `#${text}` : location.pathname + location.search);
  try {
    localStorage.setItem(STORAGE_KEY, text);
  } catch { /* storage is optional */ }
}

function load() {
  try {
    return localStorage.getItem(STORAGE_KEY) ?? "";
  } catch {
    return "";
  }
}

function listen() {
  const change = (update) => (event) => {
    update(event.target.value);
    state.shown = PAGE_SIZE;
    state.open = null;
    render();
  };
  $("filters").addEventListener("submit", (event) => event.preventDefault());
  $("role").addEventListener("change", change((v) => (state.role = v === "" ? null : Number(v))));
  $("group").addEventListener("change", change((v) => (state.group = v)));
  $("search").addEventListener("input", change((v) => (state.search = v.trim().toLowerCase())));
  $("more").addEventListener("click", () => {
    state.shown += PAGE_SIZE;
    render();
  });
  addEventListener("hashchange", () => {
    restore();
    render();
  });
}

function toggleOwned(skill) {
  if (!state.owned.delete(skill)) state.owned.add(skill);
  state.open = null;
  render();
}

function render() {
  persist();
  const jobs = visibleJobs();
  const ranked = rankSkills(jobs, state.owned).filter((s) => !state.owned.has(s.skill) && inGroup(s.skill));
  ranked.forEach((s, i) => (s.rank = i + 1));
  const found = ranked.filter((s) => names[s.skill].toLowerCase().includes(state.search));

  renderSummary(jobs, ranked[0]);
  $("measure").textContent = state.owned.size
    ? "Priority: average of demand in this role and demand in jobs that use your skills."
    : "Demand: share of postings that ask for the skill.";
  $("owned").replaceChildren(...[...state.owned].map(ownedItem));
  const scale = ranked[0]?.priority ?? 1;
  $("skills").replaceChildren(...found.slice(0, state.shown).map((s) => skillItem(s, scale, jobs)));
  $("more").hidden = found.length <= state.shown;
  $("empty").hidden = found.length > 0;
}

/** Hidden people skills must not count against the match score. */
function visibleJobs() {
  const jobs = jobsFor(data, state.role);
  if (state.group === "" || state.group === "People") return jobs;
  return jobs.map((job) => ({ ...job, skills: job.skills.filter((s) => !isPeople(s)) }));
}

const isPeople = (skill) => data.skills[skill][1] === "People";

function inGroup(skill) {
  const group = data.skills[skill][1];
  if (state.group === "technical") return !isPeople(skill);
  return state.group === "" || group === state.group;
}

function renderSummary(jobs, top) {
  const role = state.role === null ? "all roles" : data.roles[state.role].toLowerCase();
  const scope = `${number(jobs.length)} postings (${role})`;
  if (!top) {
    $("summary").textContent = scope;
    return;
  }
  const next = element("strong", "", names[top.skill]);
  const lead = state.owned.size
    ? `You have ${percent(match(jobs, state.owned))} of the skills the average job lists, across ${scope}. Learn next: `
    : `Across ${scope}, the most wanted skill is `;
  $("summary").replaceChildren(lead, next, ".");
}

function ownedItem(skill) {
  const button = element("button", "", `${names[skill]} ×`);
  button.type = "button";
  button.setAttribute("aria-label", `Remove ${names[skill]}`);
  button.addEventListener("click", () => toggleOwned(skill));
  return element("li", "", button);
}

function skillItem(stat, scale, jobs) {
  const isOpen = state.open === stat.skill;

  const open = element("button", "open", element("span", "name", names[stat.skill]));
  open.type = "button";
  open.setAttribute("aria-expanded", isOpen);
  open.addEventListener("click", () => {
    state.open = isOpen ? null : stat.skill;
    render();
    $("skills").querySelector(`[data-skill="${stat.skill}"] .open`)?.focus();
  });

  const have = element("button", "", "I have this");
  have.type = "button";
  have.setAttribute("aria-label", `I have ${names[stat.skill]}`);
  have.addEventListener("click", () => toggleOwned(stat.skill));

  const tilted = state.owned.size ? `Demand ${percent(stat.demand)}, ` : "";
  const meta = `${tilted}${number(stat.employers)} ${stat.employers === 1 ? "employer" : "employers"}`;
  const body = element("div", "", open, bar(stat.priority, scale), element("span", "meta", meta));
  const row = element("div", "row", element("span", "rank", stat.rank), body, have);

  const item = element("li", "", row);
  item.dataset.skill = stat.skill;
  item.title = `${state.owned.size ? "Priority" : "Demand"} ${percent(stat.priority)}`;
  if (isOpen) item.append(detail(stat.skill, jobs));
  return item;
}

function detail(skill, jobs) {
  const roles = rolesFor(data, skill, rolesShown.map((r) => r.id), 6);
  const pairs = pairedWith(jobs, skill, 6);
  const roleList = roles.map((r) =>
    element("li", "", data.roles[r.role], bar(r.demand, roles[0].demand)),
  );
  const pairList = pairs.map((p) => element("li", "", `${names[p.skill]}: in ${percent(p.demand)} of these jobs`));
  return element(
    "div", "detail",
    element("div", "", element("h3", "", "Roles that ask for it most"), element("ul", "", ...roleList)),
    element("div", "", element("h3", "", "Often listed with it"), element("ul", "", ...pairList)),
  );
}

function bar(value, scale) {
  const fill = element("span", "bar");
  fill.style.width = `${(100 * value) / scale}%`;
  return element("span", "track", element("span", "", fill), element("span", "value", percent(value)));
}

function element(tag, className, ...children) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  node.append(...children);
  return node;
}
