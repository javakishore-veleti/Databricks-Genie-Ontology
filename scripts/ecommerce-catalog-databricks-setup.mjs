import { postJson, withApi } from "./ecommerce-api.mjs";

const req = {
  workflow: "provision",
  question: "",
  confirm: "",
  as_job: false,
};

await withApi(() => postJson("/api/v1/ontology/workflows/run", req, "WfReq"));
