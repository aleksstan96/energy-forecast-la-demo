# Silver (Python): one row per forecast interval, typed and in UTC.
#
# A pipeline can mix SQL and Python files. The order of execution is not written anywhere: the pipeline
# reads which tables each dataset depends on (here: bronze.meteologica_forecasts) and builds the graph.

from pyspark import pipelines as dp
from pyspark.sql import functions as F

# Pipeline configuration value (set per target through a bundle variable). Lets dev process a sample of
# the data and prod everything, with the same code.
SAMPLE_PCT = int(spark.conf.get("sample_pct", "100"))


@dp.table(
    name="silver.meteologica_forecasts_15min",   # schema prefix: published to the silver schema
    comment="Silver: Meteologica forecasts, one row per series, issue and 15-minute interval (UTC). Keeps every issue.",
    cluster_by_auto=True,
)
# Expectations in Python: expect = warn, expect_or_drop = drop the row, expect_or_fail = stop the update.
@dp.expect_or_drop("forecast_not_null", "forecast IS NOT NULL")
@dp.expect("interval_is_15_min", "interval_end_utc = interval_start_utc + INTERVAL 15 MINUTES")
def meteologica_forecasts_15min():
    # spark.readStream.table(...) on a pipeline table = streaming read: only new bronze rows are processed,
    # so this is a streaming table (append-only).
    bronze = spark.readStream.table("bronze.meteologica_forecasts")
    if SAMPLE_PCT < 100:
        # Same sample on every run (hash of the file path), so incremental processing stays consistent.
        bronze = bronze.where(F.pmod(F.hash("_file_path"), F.lit(100)) < SAMPLE_PCT)

    rows = bronze.select(
        "content_id",
        F.expr("raw:content_name::string").alias("content_name"),
        F.to_timestamp(F.regexp_extract("_file_path", r"_([0-9]{12})\.json$", 1), "yyyyMMddHHmm").alias("issued_at_utc"),
        F.explode(F.expr("cast(raw:data AS ARRAY<VARIANT>)")).alias("d"),
        "_file_path",
    )

    def utc(local_field, offset_field):
        return F.to_timestamp(
            F.concat(F.expr(f'd:["{local_field}"]::string'), F.substring(F.expr(f'd:["{offset_field}"]::string'), 4, 5)),
            "yyyy-MM-dd HH:mmXX",
        )

    out = (
        rows.select(
            "content_id",
            F.regexp_extract("content_name", r"^Italy ([A-Z]+) ", 1).alias("zone"),
            F.when(F.col("content_name").ilike("%price%"), "price")
             .when(F.col("content_name").ilike("%solar%"), "solar")
             .when(F.col("content_name").ilike("%wind%"), "wind").alias("kind"),
            "issued_at_utc",
            utc("From yyyy-mm-dd hh:mm", "UTC offset from (UTC+/-hhmm)").alias("interval_start_utc"),
            utc("To yyyy-mm-dd hh:mm", "UTC offset to (UTC+/-hhmm)").alias("interval_end_utc"),
            F.expr("d:forecast::string").cast("decimal(12,2)").alias("forecast"),
            "_file_path",
        )
        .withColumn("local_date", F.to_date(F.from_utc_timestamp("interval_start_utc", "Europe/Rome")))
        .withColumn(
            "quarter_hour",
            ((F.unix_timestamp("interval_start_utc")
              - F.unix_timestamp(F.to_utc_timestamp(F.col("local_date").cast("timestamp"), "Europe/Rome"))) / 900
             ).cast("int") + 1,
        )
        .withColumn(
            "horizon_minutes",
            ((F.unix_timestamp("interval_start_utc") - F.unix_timestamp("issued_at_utc")) / 60).cast("int"),
        )
    )
    return out
