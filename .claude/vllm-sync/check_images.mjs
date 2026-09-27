#!/usr/bin/env node
/**
 * --check-images: are the pinned `docker_image:` tags still pullable?
 *
 * Opt-in and network-bound, so it never runs as part of the default pipeline,
 * and it is strictly report-only: a dead tag has no mechanical fix (the right
 * replacement is a judgement about which image the recipe was verified on).
 *
 * Commit-pinned ROCm nightlies are the recurring case — `vllm/vllm-openai-rocm`
 * keeps roughly two weeks of `nightly-<sha>` tags, so any such pin dies on a
 * schedule. The check speaks the OCI distribution protocol directly (anonymous
 * bearer token, then a manifest HEAD), which works for Docker Hub and quay.
 */

import { readFileSync, writeFileSync, readdirSync, statSync } from "node:fs";
import { join, relative, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO = join(HERE, "..", "..");

const MANIFEST_ACCEPT = [
  "application/vnd.oci.image.index.v1+json",
  "application/vnd.oci.image.manifest.v1+json",
  "application/vnd.docker.distribution.manifest.list.v2+json",
  "application/vnd.docker.distribution.manifest.v2+json",
].join(", ");

function walk(dir, out = []) {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) walk(full, out);
    else if (full.endsWith(".yaml")) out.push(full);
  }
  return out;
}

function collectPins() {
  const pins = [];
  for (const file of walk(join(REPO, "models"))) {
    readFileSync(file, "utf8")
      .split("\n")
      .forEach((line, i) => {
        const m = line.match(/docker_image:\s*["']?([^"'\s#]+)/);
        if (m) pins.push({ file: relative(REPO, file), line: i + 1, image: m[1] });
      });
  }
  return pins;
}

/** "quay.io/ascend/vllm-ascend:v1" -> {registry, repo, tag} with Hub defaults. */
function parseImage(image) {
  const [ref, tag = "latest"] = image.split(":");
  const parts = ref.split("/");
  const hasRegistry = parts.length > 1 && /[.:]/.test(parts[0]);
  const registry = hasRegistry ? parts.shift() : "registry-1.docker.io";
  let repo = parts.join("/");
  if (registry === "registry-1.docker.io" && parts.length === 1) repo = `library/${repo}`;
  return { registry, repo, tag };
}

async function tokenFor(header) {
  const realm = /realm="([^"]+)"/.exec(header)?.[1];
  if (!realm) return null;
  const service = /service="([^"]+)"/.exec(header)?.[1];
  const scope = /scope="([^"]+)"/.exec(header)?.[1];
  const url = new URL(realm);
  if (service) url.searchParams.set("service", service);
  if (scope) url.searchParams.set("scope", scope);
  const res = await fetch(url, { signal: AbortSignal.timeout(20000) });
  if (!res.ok) return null;
  const body = await res.json();
  return body.token || body.access_token || null;
}

async function checkImage(image) {
  const { registry, repo, tag } = parseImage(image);
  const url = `https://${registry}/v2/${repo}/manifests/${encodeURIComponent(tag)}`;
  const headers = { Accept: MANIFEST_ACCEPT };
  try {
    let res = await fetch(url, { method: "HEAD", headers, signal: AbortSignal.timeout(20000) });
    if (res.status === 401) {
      const token = await tokenFor(res.headers.get("www-authenticate") || "");
      if (!token) return { status: "unknown", detail: "anonymous auth refused" };
      res = await fetch(url, {
        method: "HEAD",
        headers: { ...headers, Authorization: `Bearer ${token}` },
        signal: AbortSignal.timeout(20000),
      });
    }
    if (res.ok) return { status: "alive", detail: `HTTP ${res.status}` };
    if (res.status === 404) return { status: "dead", detail: "manifest not found (404)" };
    return { status: "unknown", detail: `HTTP ${res.status}` };
  } catch (err) {
    return { status: "unknown", detail: `request failed: ${String(err.message).slice(0, 80)}` };
  }
}

async function main() {
  const args = Object.fromEntries(
    process.argv.slice(2).reduce((acc, a, i, arr) => {
      if (a.startsWith("--")) {
        const next = arr[i + 1];
        acc.push([a.slice(2), !next || next.startsWith("--") ? true : next]);
      }
      return acc;
    }, [])
  );
  const reportDir = args["report-dir"];
  const target = args.target ? String(args.target).replace(/^v/, "") : null;

  const pins = collectPins();
  const distinct = [...new Set(pins.map((p) => p.image))];
  const results = new Map();
  for (const image of distinct) {
    results.set(image, await checkImage(image));
  }

  const rows = pins.map((p) => {
    const result = results.get(p.image);
    const { tag } = parseImage(p.image);
    const notes = [];
    if (/^nightly-[0-9a-f]{7,}$/.test(tag)) {
      notes.push("commit-pinned nightly — these expire on a rolling window");
    }
    if (target && /^v?\d+\.\d+\.\d+$/.test(tag) && tag.replace(/^v/, "") !== target) {
      notes.push(`pins ${tag}, target release is ${target}`);
    }
    return { ...p, ...result, notes };
  });

  const dead = rows.filter((r) => r.status === "dead");
  const unknown = rows.filter((r) => r.status === "unknown");
  if (reportDir) {
    writeFileSync(join(reportDir, "images.json"), JSON.stringify({ target, rows }, null, 2));
  }

  console.log(`checked ${distinct.length} distinct image pins across ${pins.length} recipe lines`);
  console.log(`  alive ${rows.length - dead.length - unknown.length}, dead ${dead.length}, unknown ${unknown.length}`);
  for (const r of [...dead, ...unknown]) {
    console.log(`  ${r.status.toUpperCase()} ${r.file}:${r.line} ${r.image} — ${r.detail}`);
  }
  for (const r of rows.filter((x) => x.notes.length)) {
    console.log(`  NOTE ${r.file}:${r.line} ${r.image} — ${r.notes.join("; ")}`);
  }
}

main();
