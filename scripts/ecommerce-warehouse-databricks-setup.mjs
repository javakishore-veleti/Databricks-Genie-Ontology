import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { postJson, withApi } from "./ecommerce-api.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

const req = {
  workspace_name: process.env.DATABRICKS_WORKSPACE_NAME || "ecommerce-genie-ontology",
  warehouse_name: process.env.DATABRICKS_WAREHOUSE_NAME || "ecommerce-genie-ontology",
  cluster_size: process.env.DATABRICKS_WAREHOUSE_SIZE || "2X-Small",
  auto_stop_mins: Number(process.env.DATABRICKS_WAREHOUSE_AUTO_STOP_MINS || "10"),
  min_num_clusters: Number(process.env.DATABRICKS_WAREHOUSE_MIN_CLUSTERS || "1"),
  max_num_clusters: Number(process.env.DATABRICKS_WAREHOUSE_MAX_CLUSTERS || "1"),
};

const result = await withApi(() =>
  postJson("/api/v1/ontology/provision-warehouse", req, "WhReq"),
);
upsertEnv({
  DATABRICKS_HOST: result.host,
  DATABRICKS_WAREHOUSE_ID: result.warehouse_id,
});

function upsertEnv(values) {
  const envPath = path.join(root, ".env");
  if (!fs.existsSync(envPath)) {
    console.log("No .env file found; skip writing DATABRICKS_HOST / DATABRICKS_WAREHOUSE_ID");
    return;
  }
  let text = fs.readFileSync(envPath, "utf8");
  for (const [key, value] of Object.entries(values)) {
    if (!value) {
      continue;
    }
    const line = `${key}=${value}`;
    const pattern = new RegExp(`^${key}=.*$`, "m");
    if (pattern.test(text)) {
      text = text.replace(pattern, line);
    } else {
      text += text.endsWith("\n") ? `${line}\n` : `\n${line}\n`;
    }
    console.log(`Wrote ${key} to .env`);
  }
  fs.writeFileSync(envPath, text);
}
