import sqlite3
from contextlib import closing
from typing import Optional

import pandas as pd

import config


def load_dataframe(method: Optional[str] = None) -> pd.DataFrame:
    """Load the table. Pass a discovery method (e.g. "Transit") to filter."""
    if not config.DB_PATH.exists():
        raise FileNotFoundError("Database not found. Run 'python etl_pipeline.py' first.")

    query = f"SELECT * FROM {config.TABLE_NAME}"
    params = ()
    if method is not None:
        query += f" WHERE {config.METHOD_COLUMN} = ?"
        params = (method,)
    query += f" ORDER BY {config.ID_COLUMN}"

    with closing(sqlite3.connect(config.DB_PATH)) as conn:
        df = pd.read_sql(query, conn, params=params)
    if df.empty:
        raise ValueError(f"No planets found for discovery method '{method}'.")
    return df


def load_xy(
    include_mass: bool = True,
    method: Optional[str] = config.TRAINING_METHOD,
) -> tuple[pd.DataFrame, pd.Series]:
    """Return features and target for machine learning.

    Transit planets only by default; pass method=None for all planets.
    The radius is never included: the target is computed from it.
    """
    df = load_dataframe(method)
    features = [c for c in config.FEATURE_COLUMNS if include_mass or c != "pl_bmasse"]
    return df[features], df[config.TARGET_COLUMN]


def load_groups(method: Optional[str] = config.TRAINING_METHOD) -> pd.Series:
    """Host star of each planet, in the same row order as load_xy().

    Planets of one star share stellar features, so a train/test split should
    keep each star on one side only (for example with GroupShuffleSplit).
    """
    return load_dataframe(method)[config.HOST_COLUMN]
