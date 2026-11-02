# energy-forecast-la-demo

Reference implementation of an end-to-end forecasting use case on Databricks (AWS, serverless):
REST API ingestion → Unity Catalog volumes → bronze / silver / gold → MLflow training → Unity Catalog model registry → batch inference, deployed with Declarative Automation Bundles and CI/CD.

## Environments
| Environment | Catalog | Storage | Who writes |
|---|---|---|---|
| dev | `dev` | Databricks default storage | developers (bundle `dev` target, development mode) |
| prod | `prod` | customer-owned S3 (external location) | service principal only (bundle `prod` target) |

Data is ingested once, into `prod`. Development reads `prod` read-only and writes only to `dev`.
A `staging` catalog and workspace-level separation are added with the MLOps (MLOps Stacks) setup.

## Unity Catalog layout (same in every catalog)
```
<catalog>
 ├── raw        volumes: api_landing (/<source>/<dataset>/ingest_date=YYYY-MM-DD/<ts>.json), historical
 ├── bronze     <source>_<dataset> tables (append-only), volume: checkpoints
 ├── silver     cleaned, UTC-normalised, deduplicated
 └── gold       features + forecast output
```

## Repo layout (planned)
```
data_platform/      bundle: ingestion + bronze/silver/gold jobs and pipelines
zone_production/    bundle: ML project generated from MLOps Stacks (later)
.github/workflows/  CI/CD
```
