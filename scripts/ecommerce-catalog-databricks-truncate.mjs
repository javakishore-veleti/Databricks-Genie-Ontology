import { postJson, withApi } from "./ecommerce-api.mjs";

const req = {
  catalog: process.env.DATABRICKS_CATALOG || "ecommerce_genie_ontology",
  confirm: "DELETE",
};

await withApi(() => postJson("/api/v1/ontology/truncate", req, "TcReq"));
