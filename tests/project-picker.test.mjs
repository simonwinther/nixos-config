import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";

const root = new URL("../dotfiles/chrome/.local/share/browser-extensions/project-picker/", import.meta.url);
const source = readFileSync(new URL("api.js", root), "utf8");
const context = vm.createContext({ URLSearchParams, AbortSignal });
vm.runInContext(source, context);
const api = context.ProjectPickerAPI;
const id = (digit) => `g-p-${digit.repeat(32)}`;
const project = (digit, name) => ({ id: id(digit), display: { name }, gizmo_type: "snorlax" });
const session = { user: { id: "user-one" }, accessToken: "in-memory-test-token" };
const page = (projects, cursor = null) => ({ items: projects.map((gizmo) => ({ gizmo: { gizmo } })), cursor });
const plain = (value) => JSON.parse(JSON.stringify(value));

function setup(responses, { cookie = () => "", signal } = {}) {
  const requests = [];
  const queue = [...responses];
  return {
    requests,
    load: () => api.collect({
      cookie, signal,
      request: async (path, headers) => {
        requests.push({ path, headers });
        assert.ok(queue.length, `Unexpected request: ${path}`);
        const next = queue.shift();
        if (next instanceof Error) throw next;
        return next;
      },
    }),
  };
}

test("collects all pages, deduplicates overlaps, and exports only picker metadata", async () => {
  const app = setup([session, page([project("1", "First")], "next / + cursor"),
    page([project("1", "Renamed"), project("2", "Second")]), session]);
  const result = plain(await app.load());
  assert.deepEqual(result.projects.map((value) => value.name), ["Renamed", "Second"]);
  assert.equal(result.complete, true);
  assert.equal(result.projects[0].url, `https://chatgpt.com/g/${id("1")}/project`);
  assert.match(app.requests[2].path, /cursor=next\+%2F\+%2B\+cursor/);
  assert.match(app.requests[1].path, /owned_only=false/);
  assert.equal(app.requests[1].headers.Authorization, "Bearer in-memory-test-token");
  assert.ok(!JSON.stringify(result).includes("in-memory-test-token"));
});

test("handles the direct gizmos response and excludes ordinary custom entries", () => {
  const result = api.page({ gizmos: [project("1", "First"), { id: "g-custom", display: { name: "Other" } }], cursor: null });
  assert.equal(result.projects.length, 1);
});

test("an explicitly complete empty list can remove old cached projects", async () => {
  const app = setup([session, page([]), session]);
  assert.deepEqual(plain(await app.load()).projects, []);
});

test("uses the selected workspace rather than silently falling back to personal", async () => {
  const app = setup([session, { accounts: { work: { account: { account_id: "workspace-one", name: "Work" } } } },
    page([project("1", "Work project")]), session], { cookie: () => "other=1; _account=work" });
  const result = await app.load();
  assert.equal(result.workspace_id, "workspace-one");
  assert.equal(result.workspace_name, "Work");
  assert.equal(app.requests[2].headers["ChatGPT-Account-ID"], "workspace-one");
  await assert.rejects(setup([session, { accounts: {} }], { cookie: () => "_account=missing" }).load(), /identify/);
});

test("the personal account cookie does not require a workspace UUID", async () => {
  const app = setup([session, page([project("1", "Personal project")]), session], { cookie: () => "_account=personal" });
  const result = await app.load();
  assert.equal(result.workspace_id, "personal");
  assert.equal(app.requests[1].headers["ChatGPT-Account-ID"], undefined);
  assert.equal(app.requests.length, 3);
});

test("personal entries can have a null account ID", async () => {
  const app = setup([session, { accounts: { default: { account: { account_id: null, structure: "personal" } } } },
    page([]), session], { cookie: () => "_account=default" });
  assert.equal((await app.load()).workspace_id, "personal");
  assert.equal(app.requests[2].headers["ChatGPT-Account-ID"], undefined);
});

test("rejects failed later pages, missing cursors, malformed projects, and cursor loops", async () => {
  const badPages = [{ items: [] }, { items: [{ gizmo: {} }], cursor: null },
    page([{ id: id("1"), display: {} }]), page([{ id: "bad-id", gizmo_type: "snorlax" }])];
  for (const bad of badPages) {
    await assert.rejects(setup([session, page([project("1", "First")], "next"), bad]).load());
  }
  await assert.rejects(setup([session, page([], "loop"), page([], "loop")]).load(), /repeated/);
  await assert.rejects(setup([session, page([], "next"), new Error("Offline")]).load(), /Offline/);
});

test("rejects expired login and account or workspace switches during enumeration", async () => {
  await assert.rejects(setup([{ user: { id: "user-one" } }]).load(), /Sign in/);
  await assert.rejects(setup([session, page([]), { ...session, user: { id: "user-two" } }]).load(), /changed/);
  let calls = 0;
  const app = setup([session, page([]), session], { cookie: () => calls++ ? "_account=work" : "" });
  await assert.rejects(app.load(), /changed/);
});

test("aborting an enumeration never produces a snapshot", async () => {
  const controller = new AbortController();
  controller.abort();
  await assert.rejects(setup([session], { signal: controller.signal }).load(), { name: "AbortError" });
});

test("request errors reveal HTTP status without logging session or response content", async () => {
  let options;
  const request = api.requester(async (path, value) => {
    options = value;
    return { ok: false, status: 401, body: { cancel: async () => {} } };
  }, new AbortController().signal);
  await assert.rejects(request("/example", { Authorization: "secret" }), /HTTP 401/);
  assert.equal(options.credentials, "include");
  assert.equal(options.redirect, "error");
  assert.equal(options.cache, "no-store");
});

test("background forwards only top-frame snapshots to the native host and reports native failures", async () => {
  let listener;
  let completed;
  let installed;
  const sent = [];
  const badges = [];
  const refreshes = [];
  const chrome = {
    runtime: {
      onMessage: { addListener: (value) => { listener = value; } },
      onInstalled: { addListener: (value) => { installed = value; } },
      sendNativeMessage: async (...args) => { sent.push(args); return { ok: true }; },
    },
    action: {
      setBadgeText: async (value) => { badges.push(value); }, setTitle: async () => {},
      onClicked: { addListener: () => {} },
    },
    tabs: {
      sendMessage: async (...args) => { refreshes.push(args); }, onUpdated: { addListener: () => {} },
      query: async () => [{ id: 7 }],
    },
    scripting: { executeScript: async (value) => { sent.push(["inject", value]); } },
    webRequest: { onCompleted: { addListener: (value) => { completed = value; } } },
  };
  vm.runInNewContext(readFileSync(new URL("background.js", root), "utf8"), { chrome, URL });
  const sender = { frameId: 0, url: "https://chatgpt.com/", tab: { id: 7 } };
  const message = { type: "project-picker-snapshot", snapshot: { complete: true } };
  listener(message, { ...sender, url: "https://example.com/" }, () => assert.fail());
  listener(message, { ...sender, frameId: 1 }, () => assert.fail());
  assert.equal(sent.length, 0);
  const reply = await new Promise((resolve) => assert.equal(listener(message, sender, resolve), true));
  assert.equal(reply.ok, true);
  assert.equal(sent[0][0], "com.desktop.project_picker");
  await new Promise((resolve) => listener({ type: "project-picker-error", code: "http_403", error: "HTTP 403" }, sender, resolve));
  assert.equal(sent[1][1].action, "status");
  assert.equal(sent[1][1].code, "http_403");
  await installed();
  assert.deepEqual(plain(sent[2][1].files), ["api.js", "content.js"]);
  chrome.runtime.sendNativeMessage = async () => { throw new Error("No native host"); };
  assert.equal((await new Promise((resolve) => listener(message, sender, resolve))).ok, false);
  assert.equal(badges.at(-1).text, "!");
  completed({ method: "GET", statusCode: 200, tabId: 7, url: "https://chatgpt.com/backend-api/gizmos/snorlax/sidebar" });
  assert.equal(refreshes.length, 0);
  completed({ method: "PATCH", statusCode: 200, tabId: 7, url: "https://chatgpt.com/backend-api/gizmos/test" });
  assert.equal(refreshes[0][0], 7);
  completed({ method: "DELETE", statusCode: 204, tabId: 7, url: "https://chatgpt.com/backend-api/projects/test" });
  completed({ method: "DELETE", statusCode: 200, tabId: 7, url: "https://chatgpt.com/backend-api/another-route/test" });
  assert.equal(refreshes.length, 3);
  completed({ method: "DELETE", statusCode: 403, tabId: 7, url: "https://chatgpt.com/backend-api/projects/test" });
  completed({ method: "POST", statusCode: 200, tabId: 7, url: "https://chatgpt.com/backend-api/conversation" });
  assert.equal(refreshes.length, 3);
});

function contentApp() {
  let focused = true;
  let clock = 100000;
  let handler;
  let collector;
  const timers = new Map();
  const intervals = [];
  const events = {};
  const sent = [];
  const collections = [];
  const document = { visibilityState: "visible", cookie: "", hasFocus: () => focused,
    addEventListener: (event, callback) => { events[event] = callback; },
    removeEventListener: (event) => { delete events[event]; } };
  const context = {
    document, AbortController, fetch: () => assert.fail("Unexpected network access"), Date: { now: () => clock },
    window: { addEventListener: (event, callback) => { events[event] = callback; },
      removeEventListener: (event) => { delete events[event]; } },
    setTimeout: (callback, delay) => { const id = Symbol(); timers.set(id, { callback, delay }); return id; },
    clearTimeout: (id) => timers.delete(id),
    setInterval: (callback, delay) => { const timer = { callback, delay }; intervals.push(timer); return timer; },
    clearInterval: (timer) => { if (timer) timer.cleared = true; },
    ProjectPickerAPI: {
      requester: () => () => {},
      errorCode: api.errorCode,
      collect: async (options) => { collections.push(options); return collector ? collector(options) : { complete: true }; },
    },
    chrome: { runtime: {
      id: "fixture-extension",
      sendMessage: async (message) => { sent.push(message); return { ok: true }; },
      onMessage: { addListener: (callback) => { handler = callback; }, removeListener: () => {} },
    } },
  };
  vm.createContext(context);
  const source = readFileSync(new URL("content.js", root), "utf8");
  const install = () => vm.runInContext(source, context);
  install();
  return {
    timers, intervals, sent, collections, install,
    focus(value) { focused = value; events[value ? "focus" : "blur"]?.(); },
    visibility(value) { document.visibilityState = value; events.visibilitychange(); },
    advance(value) { clock += value; },
    refresh() { handler({ type: "project-picker-refresh" }); },
    collect(callback) { collector = callback; },
    invalidate() { context.chrome.runtime.sendMessage = () => { throw new Error("Extension context invalidated."); }; },
    async tick() {
      assert.equal(timers.size, 1);
      const [key, { callback, delay }] = [...timers][0];
      timers.delete(key);
      clock += delay;
      await callback();
    },
  };
}

test("visible pages sync even when the picker takes keyboard focus", async () => {
  const app = contentApp();
  app.install();
  assert.equal(app.intervals.length, 1);
  assert.equal(app.intervals[0].delay, 30000);
  app.focus(false);
  await app.tick();
  assert.equal(app.collections.length, 1);
  assert.equal(app.sent[0].type, "project-picker-status");
  assert.equal(app.sent[1].type, "project-picker-snapshot");
});

test("hidden tabs stop scheduling requests until made visible", async () => {
  const app = contentApp();
  app.visibility("hidden");
  assert.equal(app.timers.size, 0);
  app.intervals[0].callback();
  assert.equal(app.timers.size, 0);
  app.visibility("visible");
  await app.tick();
  assert.equal(app.collections.length, 1);
  app.advance(300000);
  app.intervals[0].callback();
  await app.tick();
  assert.equal(app.collections.length, 2);
});

test("content coalesces mutations during a fetch into one follow-up refresh", async () => {
  const app = contentApp();
  let release;
  app.collect(() => new Promise((resolve) => { release = resolve; }));
  const pending = app.tick();
  await new Promise(setImmediate);
  app.refresh();
  app.refresh();
  release({ complete: true });
  await pending;
  assert.equal(app.timers.size, 1);
  app.collect(() => ({ complete: true }));
  await app.tick();
  assert.equal(app.collections.length, 2);
  assert.equal(app.timers.size, 0);
});

test("opening the picker or changing tabs does not discard an in-flight sync", async () => {
  const app = contentApp();
  let release;
  app.collect(() => new Promise((resolve) => { release = resolve; }));
  const pending = app.tick();
  await new Promise(setImmediate);
  app.focus(false);
  app.visibility("hidden");
  release({ complete: true });
  await pending;
  assert.equal(app.collections[0].signal.aborted, false);
  assert.equal(app.sent.at(-1).type, "project-picker-snapshot");
});

test("content reports failure codes so the picker can display the cause", async () => {
  const app = contentApp();
  app.collect(() => { throw Object.assign(new Error("HTTP 403"), { code: "http_403" }); });
  await app.tick();
  assert.equal(app.sent.at(-1).type, "project-picker-error");
  assert.equal(app.sent.at(-1).code, "http_403");
});

test("extension reload stops stale timers without an unhandled rejection", async () => {
  const app = contentApp();
  app.invalidate();
  await app.tick();
  assert.equal(app.collections.length, 0);
  assert.equal(app.intervals[0].cleared, true);
  assert.equal(app.timers.size, 0);
});


test("failed requests identify their stage and programming errors are not network failures", async () => {
  for (const [path, stage] of [["/api/auth/session", "session"],
    ["/backend-api/accounts/check/v4-2023-04-27", "workspace"],
    ["/backend-api/gizmos/snorlax/sidebar", "projects"]]) {
    const request = api.requester(async () => { throw new TypeError("Failed to fetch"); }, new AbortController().signal);
    await assert.rejects(request(path), (error) => error.stage === stage && api.errorCode(error) === "network");
  }
  assert.equal(api.errorCode(new TypeError("Cannot read properties of undefined")), "unexpected");
});
