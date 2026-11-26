"use strict";

// The page asks the exe for things with `ask`, and the exe answers by calling `window.setup.show`.

const element = (id) => document.getElementById(id);
const ask = (message) => window.ipc.postMessage(JSON.stringify(message));

const choices = element("choices");
const agentsView = element("agents-view");
const progress = element("progress");
const steps = element("steps");
const switches = {
  lan: element("lan"),
  desktopShortcut: element("desktop-shortcut"),
  startMenuShortcut: element("start-menu-shortcut"),
  startAtSignIn: element("start-at-sign-in"),
};
const skill = element("skill");
const agentList = element("agent-list");
const method = element("method");

const HINTS = {
  symlink: "One copy in the shared folder, which each agent's own folder links to.",
  copy: "A copy of its own in each agent's folder.",
  none: "Nothing to link: every agent chosen reads the shared folder.",
};

// An update shows the same steps, with nothing to choose before them and nothing to go back to.
let updating = false;
// What the install button says once there is nothing more to choose.
let installWord = "Install";
// Whether the skill is installed already, so its agents are the ones to tick.
let skillInstalled = false;
// What the skills CLI listed, once it has.
let listed = null;

function setStep(state) {
  const step = steps.lastElementChild;
  // A step that ended with a note didn't do all it set out to, so it gets no check.
  const noted = state === "done" && step?.querySelector(".note");
  if (step) step.className = `step is-${noted ? "noted" : state}`;
}

function showEnd(title, lead, buttons) {
  element("progress-title").textContent = title;
  element("progress-lead").textContent = lead;
  element("progress-lead").hidden = !lead;
  for (const id of ["close", "back", "open"]) element(id).hidden = !buttons.includes(id);
  if (buttons.length) element(buttons.at(-1)).focus();
}

function nameInstall() {
  element("install").textContent = skill.checked ? "Next" : installWord;
}

/** A folder under the user's own, as `~` and the rest. */
function shortFolder(folder) {
  const home = listed.home;
  return folder.toLowerCase().startsWith(home.toLowerCase()) ? `~${folder.slice(home.length)}` : folder;
}

function agentRow(name, folder, tag) {
  const row = element("agent").content.firstElementChild.cloneNode(true);
  row.querySelector(".name").textContent = name;
  row.querySelector(".path").textContent = shortFolder(folder);
  row.querySelector(".tag").textContent = tag;
  row.dataset.name = name.toLowerCase();
  return row;
}

function showAgents() {
  const installed = new Set(listed.installed);
  const byName = (one, other) => one.name.localeCompare(other.name, undefined, { sensitivity: "base" });
  const first = (agent) => (installed.has(agent.id) || agent.detected ? 0 : 1);
  const sharing = listed.agents.filter((agent) => agent.shares).sort((one, other) => first(one) - first(other));
  const own = listed.agents
    .filter((agent) => !agent.shares)
    .sort((one, other) => first(one) - first(other) || byName(one, other));

  const shared = agentRow("Universal", listed.shared, "Always");
  shared.classList.add("locked");
  const box = shared.querySelector("input");
  box.checked = true;
  box.disabled = true;
  const named = sharing.slice(0, 5).map((agent) => agent.name);
  const also = shared.querySelector(".also");
  also.textContent = `${named.join(", ")}, and ${sharing.length - named.length} more`;
  also.hidden = false;
  shared.dataset.name = ["universal", ...sharing.map((agent) => agent.name.toLowerCase())].join(" ");

  const rows = own.map((agent) => {
    const tag = installed.has(agent.id) ? "Installed" : agent.detected ? "Found" : "";
    const row = agentRow(agent.name, agent.folder, tag);
    const input = row.querySelector("input");
    input.value = agent.id;
    input.checked = skillInstalled ? installed.has(agent.id) : agent.detected;
    return row;
  });
  const divider = document.createElement("div");
  divider.className = "divider";
  const none = document.createElement("p");
  none.className = "none";
  none.textContent = "No agent has that name.";
  none.hidden = true;
  agentList.replaceChildren(shared, divider, ...rows, none);

  element("filter").value = "";
  element("agents-loading").hidden = true;
  element("agents-chosen").hidden = false;
  showMethod();
}

function chosenAgents() {
  return [...agentList.querySelectorAll("input:checked:not(:disabled)")].map((input) => input.value);
}

function chosenMode() {
  return method.querySelector('[aria-pressed="true"]').dataset.mode;
}

function showMethod() {
  const linking = chosenAgents().length > 0;
  method.classList.toggle("disabled", !linking);
  element("method-hint").textContent = linking ? HINTS[chosenMode()] : HINTS.none;
}

function setMode(mode) {
  for (const button of method.querySelectorAll("button")) {
    button.setAttribute("aria-pressed", String(button.dataset.mode === mode));
  }
  showMethod();
}

function filterAgents() {
  const looked = element("filter").value.trim().toLowerCase();
  let any = false;
  for (const row of agentList.querySelectorAll(".agent")) {
    row.hidden = !row.dataset.name.includes(looked);
    any ||= !row.hidden;
  }
  agentList.querySelector(".divider").hidden = looked !== "";
  agentList.querySelector(".none").hidden = any;
}

/** Installs with what was chosen. `skillChoice` is the agents and how, false for none, or null to leave it. */
function install(skillChoice) {
  steps.replaceChildren();
  element("failure").hidden = true;
  showEnd("Installing", "", []);
  choices.hidden = true;
  agentsView.hidden = true;
  progress.hidden = false;
  const chosen = Object.fromEntries(Object.entries(switches).map(([name, input]) => [name, input.checked]));
  ask({ do: "install", store: element("store").value.trim(), ...chosen, skill: skillChoice });
}

const shows = {
  ready(found) {
    element("version").textContent = found.version;
    if (found.installed) {
      const again = found.installed === found.version;
      element("lead").textContent = again
        ? `Version ${found.installed} is installed. Installing it again repairs it and applies what you choose here.`
        : `Version ${found.installed} is installed, and this replaces it with ${found.version}.`;
      element("lead").hidden = false;
      installWord = again ? "Install again" : "Update";
    }
    element("agents-install").textContent = installWord;
    element("store").value = found.store;
    element("store-group").hidden = found.hasStores;
    element("stores-kept").hidden = !found.hasStores;
    for (const [name, input] of Object.entries(switches)) input.checked = found[name];
    skill.checked = found.skill;
    skillInstalled = found.skillInstalled;
    setMode(found.skillMode);
    nameInstall();
    choices.hidden = false;
  },

  updating(found) {
    updating = true;
    document.title = "Reference Store Update";
    element("version").textContent = found.version;
    const lead = found.installed
      ? `Version ${found.installed} is replaced with ${found.version}, and the app starts again when it is done.`
      : "";
    showEnd("Updating Reference Store", lead, []);
    progress.hidden = false;
  },

  folder({ folder }) {
    element("store").value = folder;
  },

  downloading() {
    element("agents-loading-text").textContent = "Downloading Node.js for the skills CLI...";
  },

  agents({ agents }) {
    listed = agents;
    showAgents();
    element("agents-install").disabled = false;
  },

  noAgents({ text }) {
    element("agents-install").disabled = false;
    element("agents-loading").hidden = true;
    const failure = element("agents-failure");
    failure.textContent = `The agents couldn't be listed, so setup goes on without the skill. The app's settings can install it later.\n\n${text}`;
    failure.hidden = false;
  },

  started({ label }) {
    setStep("done");
    const step = element("step").content.firstElementChild.cloneNode(true);
    step.classList.add("is-working");
    step.querySelector(".label").textContent = label;
    steps.append(step);
    step.scrollIntoView({ block: "nearest" });
  },

  note({ text }) {
    const note = document.createElement("p");
    note.className = "note";
    note.textContent = text;
    (steps.lastElementChild ?? steps).append(note);
    note.scrollIntoView({ block: "nearest" });
  },

  installed() {
    setStep("done");
    showEnd("Reference Store is installed", "", ["close", "open"]);
  },

  failed({ text }) {
    setStep("failed");
    const failure = element("failure");
    failure.textContent = text;
    failure.hidden = false;
    if (updating) showEnd("The update didn't finish", "", ["close"]);
    else showEnd("Setup didn't finish", "", ["close", "back"]);
    failure.scrollIntoView({ block: "nearest" });
  },
};

window.setup = {
  show(message) {
    shows[message.is](message);
  },
};

choices.addEventListener("submit", (event) => {
  event.preventDefault();
  if (!skill.checked) {
    install(false);
    return;
  }
  choices.hidden = true;
  agentsView.hidden = false;
  if (listed === null) {
    element("agents-failure").hidden = true;
    element("agents-loading").hidden = false;
    element("agents-install").disabled = true;
    ask({ do: "agents" });
  }
});

agentsView.addEventListener("submit", (event) => {
  event.preventDefault();
  install(listed === null ? null : { agents: chosenAgents(), mode: chosenMode() });
});

skill.addEventListener("change", nameInstall);
agentList.addEventListener("change", showMethod);
element("filter").addEventListener("input", filterAgents);
for (const button of method.querySelectorAll("button")) {
  button.addEventListener("click", () => setMode(button.dataset.mode));
}
element("agents-back").addEventListener("click", () => {
  agentsView.hidden = true;
  choices.hidden = false;
});
element("browse").addEventListener("click", () => ask({ do: "browse" }));
element("open").addEventListener("click", () => ask({ do: "open" }));
element("close").addEventListener("click", () => ask({ do: "close" }));
element("back").addEventListener("click", () => {
  progress.hidden = true;
  choices.hidden = false;
});

ask({ do: "ready" });
