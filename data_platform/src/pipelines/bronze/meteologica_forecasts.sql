-- Bronze: Meteologica forecast files, one row per file, exactly as received.
--
-- STREAM read_files(...) is Auto Loader: each run picks up only files it hasn't processed before; the
-- pipeline manages the checkpoint and schema location itself.
--
-- The whole JSON document goes into a single VARIANT column (`raw`), because Meteologica's field names
-- contain spaces and parentheses ("From yyyy-mm-dd hh:mm", "UTC offset from (UTC+/-hhmm)"), which are not
-- valid Delta column names. Silver reads fields from the VARIANT with their original names, e.g.
--   raw:data[0]["From yyyy-mm-dd hh:mm"]::string

CREATE OR REFRESH STREAMING TABLE meteologica_forecasts (
  -- Data quality: every file must identify its series. Violations are counted in the pipeline UI
  -- but rows are kept (warn only), so nothing received is lost.
  CONSTRAINT has_content_id EXPECT (content_id IS NOT NULL),
  CONSTRAINT has_rows EXPECT (array_size(cast(raw:data AS ARRAY<VARIANT>)) > 0)
)
COMMENT 'Bronze: Meteologica forecast files as received (one row per file, JSON in raw), plus ingestion metadata. Append-only.'
CLUSTER BY AUTO                                   -- let Databricks choose the data layout
AS SELECT
  raw:content_id::int                        AS content_id,         -- extracted for filtering; the full document stays in raw
  raw,                                                              -- the complete JSON document as a VARIANT
  _metadata.file_path                        AS _file_path,         -- lineage back to the landed file
  _metadata.file_modification_time           AS _file_modified_at,  -- when the file landed
  current_timestamp()                        AS _ingested_at        -- when this pipeline loaded it
FROM STREAM read_files(
  '${landing_root}/meteologica/',                                   -- all series and dates under the source folder
  format => 'json',
  singleVariantColumn => 'raw'                                      -- whole file into one VARIANT column
);
