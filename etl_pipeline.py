import json
import sqlite3
from collections import Counter
from contextlib import closing
from typing import Optional

import pandas as pd
import requests
from pydantic import BaseModel, Field, ValidationError, field_validator

import config

TABLE_COLUMNS = [
    config.ID_COLUMN,
    config.HOST_COLUMN,
    config.METHOD_COLUMN,
    config.YEAR_COLUMN,
    config.RADIUS_COLUMN,
    *config.FEATURE_COLUMNS,
    config.TARGET_COLUMN,
]


class ExoplanetRecord(BaseModel):
    pl_name: str = Field(..., min_length=1)
    hostname: Optional[str] = None
    discoverymethod: Optional[str] = None
    disc_year: Optional[int] = None
    pl_rade: float = Field(..., gt=0.0)
    pl_bmassprov: Optional[str] = None

    pl_bmasse: Optional[float] = None
    pl_orbper: Optional[float] = None
    pl_orbsmax: Optional[float] = None
    pl_insol: Optional[float] = None
    pl_eqt: Optional[float] = None
    st_teff: Optional[float] = None
    st_rad: Optional[float] = None
    st_mass: Optional[float] = None
    st_met: Optional[float] = None

    @field_validator(
        "pl_bmasse", "pl_orbper", "pl_orbsmax", "pl_insol",
        "pl_eqt", "st_teff", "st_rad", "st_mass",
        mode="before",
    )
    @classmethod
    def positive_or_none(cls, value):
        try:
            number = float(value)
        except (ValueError, TypeError):
            return None
        return number if number > 0 else None

    @field_validator("st_met", mode="before")
    @classmethod
    def number_or_none(cls, value):
        # Metallicity is a log ratio, so negative values are valid.
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    @field_validator("disc_year", mode="before")
    @classmethod
    def year_or_none(cls, value):
        try:
            return int(value)
        except (ValueError, TypeError):
            return None


def fetch_raw_data() -> list[dict]:
    columns = ", ".join([
        config.ID_COLUMN,
        config.HOST_COLUMN,
        config.METHOD_COLUMN,
        config.YEAR_COLUMN,
        config.RADIUS_COLUMN,
        config.MASS_PROVENANCE_COLUMN,
        *config.FEATURE_COLUMNS,
    ])
    params = {
        "query": f"select {columns} from {config.NASA_SOURCE_TABLE}",
        "format": "json",
    }
    print("[EXTRACT] Querying NASA TAP API...")
    try:
        response = requests.get(config.NASA_TAP_URL, params=params, timeout=60)
        response.raise_for_status()
        records = response.json()
    except requests.RequestException as error:
        if not config.RAW_SNAPSHOT_PATH.exists():
            raise
        print(f"[EXTRACT] NASA request failed ({error}). Using saved snapshot.")
        return json.loads(config.RAW_SNAPSHOT_PATH.read_text())

    config.RAW_SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    config.RAW_SNAPSHOT_PATH.write_text(json.dumps(records))
    print(f"[EXTRACT] Fetched {len(records):,} records (snapshot saved).")
    return records


def validate_records(raw_records: list[dict]) -> pd.DataFrame:
    valid = []
    dropped_reasons = Counter()
    for record in raw_records:
        try:
            valid.append(ExoplanetRecord(**record).model_dump())
        except ValidationError as error:
            for problem in error.errors():
                dropped_reasons[str(problem["loc"][0])] += 1

    dropped = len(raw_records) - len(valid)
    print(f"[VALIDATE] Valid: {len(valid):,} | Dropped: {dropped:,}")
    for field, count in dropped_reasons.most_common():
        print(f"           invalid or missing '{field}': {count:,}")
    return pd.DataFrame(valid)


def remove_estimated_masses(df: pd.DataFrame) -> pd.DataFrame:
    provenance = df[config.MASS_PROVENANCE_COLUMN].fillna("").str.lower()
    estimated = provenance.str.contains(config.ESTIMATED_MASS_KEYWORD)
    df.loc[estimated, "pl_bmasse"] = None
    print(f"[CLEAN] Removed {estimated.sum():,} masses estimated from radius.")
    return df.drop(columns=[config.MASS_PROVENANCE_COLUMN])


def add_target(df: pd.DataFrame) -> pd.DataFrame:
    before = len(df)
    df = df.drop_duplicates(subset=config.ID_COLUMN)
    print(f"[CLEAN] Removed {before - len(df):,} duplicate planet names.")
    is_terrestrial = (df[config.RADIUS_COLUMN] < config.RADIUS_THRESHOLD).astype(int)
    df = df.assign(**{config.TARGET_COLUMN: is_terrestrial})
    df[config.YEAR_COLUMN] = df[config.YEAR_COLUMN].astype("Int64")
    return df[TABLE_COLUMNS]


def create_table(conn: sqlite3.Connection) -> None:
    feature_definitions = ",\n        ".join(f"{name} REAL" for name in config.FEATURE_COLUMNS)
    conn.execute(f"DROP TABLE IF EXISTS {config.TABLE_NAME}")
    conn.execute(f"""
        CREATE TABLE {config.TABLE_NAME} (
        {config.ID_COLUMN} TEXT PRIMARY KEY,
        {config.HOST_COLUMN} TEXT,
        {config.METHOD_COLUMN} TEXT,
        {config.YEAR_COLUMN} INTEGER,
        {config.RADIUS_COLUMN} REAL NOT NULL CHECK ({config.RADIUS_COLUMN} > 0),
        {feature_definitions},
        {config.TARGET_COLUMN} INTEGER NOT NULL CHECK ({config.TARGET_COLUMN} IN (0, 1))
        )
    """)


def load_to_sqlite(df: pd.DataFrame) -> None:
    with closing(sqlite3.connect(config.DB_PATH)) as conn:
        create_table(conn)
        df.to_sql(config.TABLE_NAME, conn, if_exists="append", index=False)
        conn.commit()
    print(f"[LOAD] Saved {len(df):,} rows to '{config.DB_PATH.name}'.")


def run_pipeline() -> None:
    df = validate_records(fetch_raw_data())
    df = remove_estimated_masses(df)
    df = add_target(df)
    load_to_sqlite(df)


if __name__ == "__main__":
    run_pipeline()
