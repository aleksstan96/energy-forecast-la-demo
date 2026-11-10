# data_platform: Declarative Automation Bundle

This project uses Declarative Automation Bundles (formerly Databricks Asset Bundles) for deployment.
Read the comment block at the top of `databricks.yml` for the project's conventions before changing anything.

## Prerequisites
Install the Databricks CLI (>= v0.288.0): `brew tap databricks/tap && brew install databricks`. Verify with `databricks -v`.

## For AI agents
- Read the `databricks-core` skill for CLI basics, authentication and the deployment workflow, then the
  product skill for the task: `databricks-dabs` (bundle config), `databricks-jobs` (jobs),
  `databricks-pipelines` (Lakeflow pipelines), `databricks-serverless` (compute).
- If the skills are not available, install them: `databricks aitools install`.
- After any change: `pytest` and `databricks bundle validate --strict -t dev`.
- Never deploy to `prod` from a laptop; prod is deployed by CI as the service principal.
- Never write simulated data to the `prod` catalog.
