import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import test from "node:test";

const templateRoot = new URL("../", import.meta.url);

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request("http://localhost/", {
      headers: { accept: "text/html" },
    }),
    {
      ASSETS: {
        fetch: async () => new Response("Not found", { status: 404 }),
      },
    },
    {
      waitUntil() {},
      passThroughOnException() {},
    },
  );
}

test("server-renders the battlefield spectrum planning dashboard", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /<html lang="zh-CN">/i);
  assert.match(html, /<title>战场智能频谱筹划平台<\/title>/i);
  assert.match(html, /aria-label="战场智能频谱筹划导航"/i);
  assert.match(html, /联合任务保障/);
  assert.match(html, /频段资源/);
  assert.match(html, /冲突评估/);
  assert.match(html, /动态重筹/);
  assert.match(html, /脱敏摘要模式/);
});

test("keeps the production page independent from the starter preview", async () => {
  const [page, layout, packageJson] = await Promise.all([
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/layout.tsx", import.meta.url), "utf8"),
    readFile(new URL("../package.json", import.meta.url), "utf8"),
  ]);

  assert.match(page, /^"use client";/);
  assert.match(page, /const scenarios: Record<ScenarioKey, Scenario>/);
  assert.match(page, /aria-label="战场智能频谱筹划导航"/);
  assert.match(layout, /generateMetadata/);
  assert.match(layout, /lang="zh-CN"/);
  assert.match(packageJson, /"test": "npm run build && node --test tests\/rendered-html\.test\.mjs"/);
  assert.doesNotMatch(page, /SkeletonPreview|Codex is working|Your site is taking shape/);

  await assert.rejects(access(new URL("public/_sites-preview", templateRoot)));
});
