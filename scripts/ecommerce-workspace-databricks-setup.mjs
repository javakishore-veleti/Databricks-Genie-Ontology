import { postJson, withApi } from "./ecommerce-api.mjs";

const adminEmails = (process.env.DATABRICKS_WORKSPACE_ADMIN_EMAILS || "")
  .split(",")
  .map((value) => value.trim())
  .filter(Boolean);

const req = {
  workspace_name: process.env.DATABRICKS_WORKSPACE_NAME || "ecommerce-genie-ontology",
  aws_region: process.env.DATABRICKS_AWS_REGION || "us-east-1",
  pricing_tier: process.env.DATABRICKS_PRICING_TIER || "PREMIUM",
  compute_mode: "SERVERLESS",
  admin_emails: adminEmails,
};

await withApi(() => postJson("/api/v1/ontology/provision-workspace", req, "PwReq"));
