-- Bronze: GME zonal price records as received, plus ingestion metadata.
-- These field names are valid column names, so no VARIANT is needed: read_files infers the columns, and
-- schemaHints pins the types that matter instead of relying on inference.

CREATE OR REFRESH STREAMING TABLE gme_zonal_prices (
  CONSTRAINT has_price EXPECT (Price IS NOT NULL)
)
COMMENT 'Bronze: GME MGP zonal price records as received, plus ingestion metadata. Append-only.'
CLUSTER BY AUTO
AS SELECT
  * EXCEPT (_rescued_data),
  _rescued_data,                                   -- values that didn't match the schema, kept instead of lost
  _metadata.file_path                AS _file_path,
  _metadata.file_modification_time   AS _file_modified_at,
  current_timestamp()                AS _ingested_at
FROM STREAM read_files(
  '${landing_root}/gme/zonal_prices/',
  format => 'json',
  schemaHints => 'FlowDate INT, Hour INT, Period STRING, Market STRING, Zone STRING, Price DECIMAL(10,2)'
);
