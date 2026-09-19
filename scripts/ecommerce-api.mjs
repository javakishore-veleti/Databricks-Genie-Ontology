import { createRequire } from "node:module";
import { execSync, spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const { Agent, fetch: undiciFetch } = createRequire(import.meta.url)("undici");

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const base = process.env.ECOMMERCE_API_BASE || "http://127.0.0.1:8000";
const healthUrl = `${base}/health`;
const port = Number(new URL(base).port || "8000");
const dispatcher = new Agent({ headersTimeout: 0, bodyTimeout: 0, connectTimeout: 30_000 });

export async function isHealthy() {
  try {
    const response = await undiciFetch(healthUrl, { dispatcher });
    return response.ok;
  } catch {
    return false;
  }
}

export function stopApi() {
  try {
    const pids = execSync(`lsof -tiTCP:${port} -sTCP:LISTEN`, {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    }).trim();
    if (!pids) {
      return;
    }
    console.log(`Stopping FastAPI on port ${port}`);
    for (const pid of pids.split("\n")) {
      try {
        process.kill(Number(pid), "SIGTERM");
      } catch {
        /* already gone */
      }
    }
  } catch {
    /* nothing listening */
  }
}

export function startApi() {
  console.log("Starting FastAPI via npm run ecommerce:api:run");
  return spawn("npm", ["run", "ecommerce:api:run"], {
    cwd: root,
    stdio: "inherit",
    shell: true,
    env: process.env,
  });
}

export async function waitForApi(attempts = 60) {
  for (let i = 1; i <= attempts; i += 1) {
    if (await isHealthy()) {
      return;
    }
    if (i === 1) {
      console.log(`Waiting for FastAPI at ${healthUrl}`);
    }
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
  throw new Error(`FastAPI did not become ready at ${healthUrl}`);
}

export async function withApi(fn) {
  stopApi();
  await new Promise((resolve) => setTimeout(resolve, 500));
  const child = startApi();
  try {
    await waitForApi();
    return await fn();
  } finally {
    child.kill("SIGTERM");
    stopApi();
  }
}

export async function postJson(pathname, req, label) {
  const url = `${base}${pathname}`;
  console.log(`POST ${url}`);
  console.log(label, JSON.stringify(req, null, 2));
  const response = await undiciFetch(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(req),
    dispatcher,
  });
  const text = await response.text();
  let body;
  try {
    body = JSON.parse(text);
  } catch {
    body = text;
  }
  if (!response.ok) {
    console.error(body);
    throw new Error(`${pathname} failed: HTTP ${response.status}`);
  }
  console.log(`${label.replace("Req", "RespResult")}`, JSON.stringify(body, null, 2));
  return body;
}
