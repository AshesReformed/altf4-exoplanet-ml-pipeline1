from eda_analysis import run_eda
from etl_pipeline import run_pipeline

if __name__ == "__main__":
    print("=== ETL ===")
    run_pipeline()
    print("\n=== EDA ===")
    run_eda()
    print("\nDone.")
