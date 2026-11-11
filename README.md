# energy-forecast-la-demo

Reference implementation of an end-to-end forecasting use case on Databricks (AWS, serverless):
REST API ingestion → Unity Catalog volumes → bronze / silver / gold → MLflow training → Unity Catalog model registry → batch inference, deployed with Declarative Automation Bundles and CI/CD.

## Environments
| Environment | Catalog | Storage | Who writes |
|---|---|---|---|
| dev | `dev` | Databricks default storage | developers (bundle `dev` target, development mode) |
| prod | `prod` | customer-owned S3 (external location) | service principal only (bundle `prod` target) |

Data is ingested once, into `prod`. Development reads `prod` read-only and writes only to `dev`.
A `staging` catalog and workspace-level separation can be added in the MLOps phase (MLOps Quickstart pattern).

## Where the code lives
The Git folder is the code you edit. GitHub is the truth. The bundle copy is what runs, deployed per target. Dev is yours to break, and prod is deployed by CI as the service principal.

## Unity Catalog layout (same in every catalog)
```
<catalog>
 ├── raw        volumes: api_landing (/<source>/<dataset>/ingest_date=YYYY-MM-DD/<file>), historical (/<source>/<dataset>/*.jsonl)
 ├── bronze     <source>_<dataset> tables (append-only), volume: checkpoints
 ├── silver     cleaned, UTC-normalised, deduplicated
 └── gold       features + forecast output
```

## Sources (simulated in dev; formats follow the providers' documented APIs)
| Source | Dataset | Cadence | Format notes |
|---|---|---|---|
| Terna (grid operator) | total load (actual + forecast, per bidding zone) | daily | local time + UTC offset per record, numbers as strings |
| Terna | actual generation (national, by primary source) | daily | hourly GWh as strings |
| GME (market operator) | MGP zonal prices | daily | hourly until 30 Sep 2025, 15-minute periods from 1 Oct 2025 |
| Meteologica (forecast provider) | power, solar and wind forecasts per zone | several issues a day | 15-minute rows, local From/To + UTC offset, values as strings |

## Repo layout
```
data_platform/      bundle: ingestion + bronze/silver/gold jobs and pipelines
  databricks.yml    targets (dev per developer, prod as a service principal), variables
  resources/        jobs and pipelines (<name>.<type>.yml)
  src/
    pipelines/meteologica/
      transformations/   pipeline source code: bronze (SQL) -> silver (Python) -> silver "latest" (SQL)
      explorations/      notebooks for analysis, not run by the pipeline
    simulation/, notebooks/   demo-only simulated data (dev target only)
    ingestion/        showcase notebook: API call with parameters and Unity Catalog secrets
  tests/            unit tests, run locally and in CI (not deployed)
zone_production/    bundle: ML project (MLOps Quickstart pattern, later)
.github/workflows/  CI/CD (later)
```

## Local checks
```
cd data_platform
python -m venv .venv && . .venv/bin/activate && pip install -r requirements-dev.txt
pytest
databricks bundle validate -t dev
```
