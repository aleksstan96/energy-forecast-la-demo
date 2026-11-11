-- Bronze: raw files as received, one row per file, plus ingestion metadata.
--
-- STREAM read_files(...) is Auto Loader: each update processes only files it hasn't seen before.
-- The pipeline manages the checkpoint and schema location.
--
-- singleVariantColumn loads each JSON document into one VARIANT column. Use it when the source's field
-- names are not valid Delta column names (spaces, parentheses), or to keep the payload exactly as received;
-- later layers read fields with path syntax, e.g. raw:field or raw:["field with spaces"].

CREATE OR REFRESH STREAMING TABLE meteologica_forecasts (
  -- Expectations: data quality rules. Default = warn (rows kept, violations counted in the pipeline UI);
  -- ON VIOLATION DROP ROW or FAIL UPDATE change the behaviour.
  CONSTRAINT has_content_id EXPECT (content_id IS NOT NULL),
  CONSTRAINT has_rows EXPECT (array_size(cast(raw:data AS ARRAY<VARIANT>)) > 0)
)
COMMENT 'Bronze: Meteologica forecast files as received (one row per file), plus ingestion metadata. Append-only.'
CLUSTER BY AUTO                                   -- Databricks chooses and maintains the data layout
AS SELECT
  raw:content_id::int                 AS content_id,
  raw,
  _metadata.file_path                 AS _file_path,        -- _metadata: file-level metadata for lineage
  _metadata.file_modification_time    AS _file_modified_at,
  current_timestamp()                 AS _ingested_at
FROM STREAM read_files(
  '${landing_root}/meteologica/',                          -- value from the pipeline configuration
  format => 'json',
  singleVariantColumn => 'raw'
);
