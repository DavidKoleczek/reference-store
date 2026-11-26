"use strict";

// The page asks the exe for things with `ask`, and the exe answers by calling `window.setup.show`.

const element = (id) => document.getElementById(id);
const ask = (message) => window.ipc.postMessage(JSON.stringify(message));

const choices = element("choices");
const progress = element("progress");
const steps = element("steps");
const switches = {
  lan: element("lan"),
  desktopShortcut: element("desktop-shortcut"),
  startMenuShortcut: element("start-menu-shortcut"),
  startAtSignIn: element("start-at-sign-in"),
};

// An update shows the same steps, with nothing to choose before them and nothing to go back to.
let updating = false;

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

const shows = {
  ready(found) {
    element("version").textContent = found.version;
    if (found.installed) {
      const again = found.installed === found.version;
      element("lead").textContent = again
        ? `Version ${found.installed} is installed. Installing it again repairs it and applies what you choose here.`
        : `Version ${found.installed} is installed, and this replaces it with ${found.version}.`;
      element("lead").hidden = false;
      element("install").textContent = again ? "Install again" : "Update";
    }
    element("store").value = found.store;
    element("store-group").hidden = found.hasStores;
    element("stores-kept").hidden = !found.hasStores;
    for (const [name, input] of Object.entries(switches)) input.checked = found[name];
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
  steps.replaceChildren();
  element("failure").hidden = true;
  showEnd("Installing", "", []);
  choices.hidden = true;
  progress.hidden = false;
  const chosen = Object.fromEntries(Object.entries(switches).map(([name, input]) => [name, input.checked]));
  ask({ do: "install", store: element("store").value.trim(), ...chosen });
});

element("browse").addEventListener("click", () => ask({ do: "browse" }));
element("open").addEventListener("click", () => ask({ do: "open" }));
element("close").addEventListener("click", () => ask({ do: "close" }));
element("back").addEventListener("click", () => {
  progress.hidden = true;
  choices.hidden = false;
});

ask({ do: "ready" });
