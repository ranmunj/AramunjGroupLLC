const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const script = fs.readFileSync(path.join(__dirname, "../script.js"), "utf8");

function element() {
  const classes = new Set();
  return {
    events: {},
    attributes: {},
    dataset: {},
    textContent: "",
    disabled: false,
    classList: {
      add: (name) => classes.add(name),
      remove: (name) => classes.delete(name),
      contains: (name) => classes.has(name),
      toggle(name, force = !classes.has(name)) {
        force ? classes.add(name) : classes.delete(name);
        return force;
      },
    },
    addEventListener(name, handler) {
      this.events[name] = handler;
    },
    setAttribute(name, value) {
      this.attributes[name] = value;
    },
    focus() {
      this.focused = true;
    },
    reset() {
      this.didReset = true;
    },
  };
}

function setup(fetchImpl) {
  const form = element();
  const status = element();
  const button = element();
  const toggle = element();
  const link = element();
  const body = element();
  const document = element();
  form.querySelector = () => button;
  document.body = body;
  document.querySelector = (selector) =>
    ({
      "#leadForm": form,
      "#formStatus": status,
      ".nav-toggle": toggle,
    })[selector] || null;
  document.querySelectorAll = (selector) =>
    selector === "#primaryNav a" ? [link] : [];
  const desktop = element();
  const window = {
    scrollY: 0,
    addEventListener() {},
    matchMedia: (query) =>
      query.includes("min-width") ? desktop : { matches: true },
  };
  const payload = {
    name: "Preview Test",
    company: "Example",
    email: "test@example.com",
    phone: "",
    organization: "Small business",
    country: "Zimbabwe",
    project_type: "Software Upgrades & Modernization",
    budget: "Not sure yet",
    message: "Please assess our current business application.",
  };
  const calls = [];
  vm.runInNewContext(script, {
    document,
    window,
    FormData: class {
      entries() {
        return Object.entries(payload);
      }
    },
    fetch: async (...args) => {
      calls.push(args);
      return fetchImpl(...args);
    },
  });
  return {
    form,
    status,
    button,
    toggle,
    link,
    body,
    document,
    desktop,
    calls,
    payload,
    submit: () => form.events.submit({ preventDefault() {} }),
  };
}

test("inquiry posts all existing API fields and resets only after success", async () => {
  const app = setup(async () => ({
    ok: true,
    json: async () => ({ success: true }),
  }));
  await app.submit();
  assert.equal(app.calls[0][0], "/api/leads");
  assert.equal(app.calls[0][1].method, "POST");
  assert.deepEqual(JSON.parse(app.calls[0][1].body), app.payload);
  assert.equal(app.status.dataset.state, "success");
  assert.equal(app.form.didReset, true);
  assert.equal(app.button.disabled, false);
  assert.equal(app.form.attributes["aria-busy"], "false");
});

test("pending submission cannot send a duplicate request", async () => {
  let finish;
  const app = setup(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  const first = app.submit();
  assert.equal(app.button.disabled, true);
  assert.equal(app.form.attributes["aria-busy"], "true");
  await app.submit();
  assert.equal(app.calls.length, 1);
  finish({ ok: true, json: async () => ({ success: true }) });
  await first;
  assert.equal(app.button.disabled, false);
});

test("server errors preserve form details and never expose database errors", async () => {
  const app = setup(async () => ({
    ok: false,
    json: async () => ({ error: "postgres password=secret" }),
  }));
  await app.submit();
  assert.equal(app.form.didReset, undefined);
  assert.equal(app.status.dataset.state, "error");
  assert.doesNotMatch(app.status.textContent, /postgres|secret/);
  assert.match(app.status.textContent, /aramunj@icloud.com/);
  assert.equal(app.button.disabled, false);
  await app.submit();
  assert.equal(app.calls.length, 2);
});

test("network and non-JSON failures restore the submit button", async () => {
  for (const fail of [
    async () => {
      throw new Error("network unavailable");
    },
    async () => ({
      ok: false,
      json: async () => {
        throw new Error("invalid JSON");
      },
    }),
  ]) {
    const app = setup(fail);
    await app.submit();
    assert.equal(app.status.dataset.state, "error");
    assert.equal(app.form.didReset, undefined);
    assert.equal(app.button.disabled, false);
  }
});

test("mobile navigation closes by link, Escape, and desktop resize", () => {
  const app = setup(async () => ({}));
  app.toggle.events.click();
  assert.equal(app.toggle.attributes["aria-expanded"], "true");
  app.link.events.click();
  assert.equal(app.body.classList.contains("nav-open"), false);
  app.toggle.events.click();
  app.document.events.keydown({ key: "Escape" });
  assert.equal(app.toggle.attributes["aria-expanded"], "false");
  assert.equal(app.toggle.focused, true);
  app.toggle.events.click();
  app.desktop.events.change({ matches: true });
  assert.equal(app.body.classList.contains("nav-open"), false);
});
