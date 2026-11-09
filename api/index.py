import base64
import io
from pathlib import Path
import sys

# Ensure Matplotlib operates in non-interactive headless mode for Vercel
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

# Add root directory to path for project imports
ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))

from flask import Flask, redirect, render_template_string, request, url_for
import config
from data_access import load_dataframe
from eda_analysis import CLASS_COLORS, LARGER_LABEL, TERRESTRIAL_LABEL, training_subset, with_class_labels
from etl_pipeline import run_pipeline

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>ALT-F4 Exoplanet Pipeline</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <style>
        body { background-color: #f8f9fa; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        .card { border-radius: 12px; border: 1px solid #e9ecef; box-shadow: 0 4px 6px rgba(0,0,0,0.02); }
        .stat-number { font-size: 2rem; font-weight: 700; }
        .table-container { max-height: 550px; overflow-y: auto; }
        .plot-img { width: 100%; height: auto; border-radius: 8px; border: 1px solid #dee2e6; }
    </style>
</head>
<body class="py-4">
    <div class="container">
        <div class="bg-white p-4 p-md-5 rounded-4 shadow-sm mb-4">
            
            <!-- Header section with Refetch button -->
            <div class="d-flex flex-wrap justify-content-between align-items-center mb-3 gap-2">
                <div>
                    <h1 class="h2 mb-1 fw-bold text-dark">🪐 ALT-F4 NASA Exoplanet Pipeline</h1>
                    <p class="text-secondary mb-0">Automated ETL & EDA Dashboard (Project 1 of 3)</p>
                </div>
                <div class="d-flex align-items-center gap-2">
                    <span class="badge bg-primary fs-6 px-3 py-2">Group: ALT-F4</span>
                    <a href="/refetch" class="btn btn-outline-danger btn-sm px-3 fw-semibold">🔄 Refetch Data from NASA</a>
                </div>
            </div>
            
            <hr class="my-4">
            
            <!-- Metric Summary Cards -->
            <div class="row g-3 text-center mb-4">
                <div class="col-6 col-md-3">
                    <div class="card p-3 bg-light">
                        <div class="stat-number text-dark">{{ total }}</div>
                        <div class="text-muted small">Total Confirmed Planets</div>
                    </div>
                </div>
                <div class="col-6 col-md-3">
                    <div class="card p-3 bg-light">
                        <div class="stat-number text-primary">{{ transit }}</div>
                        <div class="text-muted small">Transit Method Planets</div>
                    </div>
                </div>
                <div class="col-6 col-md-3">
                    <div class="card p-3 bg-light">
                        <div class="stat-number text-danger">{{ terrestrial }}</div>
                        <div class="text-muted small">Terrestrial (&lt; 2.0 R_Earth)</div>
                    </div>
                </div>
                <div class="col-6 col-md-3">
                    <div class="card p-3 bg-light">
                        <div class="stat-number text-secondary">{{ larger }}</div>
                        <div class="text-muted small">Gas Giants / Sub-Neptunes</div>
                    </div>
                </div>
            </div>

            <!-- Tabs: EDA Graphs vs SQLite Table -->
            <ul class="nav nav-tabs mb-4" id="mainTab" role="tablist">
                <li class="nav-item">
                    <button class="nav-link active fw-bold" id="graphs-tab" data-bs-toggle="tab" data-bs-target="#graphs" type="button" role="tab">📊 Visual EDA Graphs</button>
                </li>
                <li class="nav-item">
                    <button class="nav-link fw-bold" id="table-tab" data-bs-toggle="tab" data-bs-target="#table" type="button" role="tab">📁 Validated Database Table</button>
                </li>
            </ul>

            <div class="tab-content" id="mainTabContent">
                
                <!-- TAB 1: EDA PLOTS -->
                <div class="tab-pane fade show active" id="graphs" role="tabpanel">
                    <div class="row g-4">
                        <div class="col-md-6">
                            <h5 class="fw-bold mb-2 text-secondary">Planetary Radius Valley (Fulton Gap)</h5>
                            <img src="data:image/png;base64,{{ plots.radius_dist }}" class="plot-img">
                        </div>
                        <div class="col-md-6">
                            <h5 class="fw-bold mb-2 text-secondary">Feature Correlation Heatmap</h5>
                            <img src="data:image/png;base64,{{ plots.correlation }}" class="plot-img">
                        </div>
                        <div class="col-12 mt-4">
                            <h5 class="fw-bold mb-2 text-secondary">Orbital Period vs. Planetary Radius</h5>
                            <img src="data:image/png;base64,{{ plots.period_vs_radius }}" class="plot-img">
                        </div>
                    </div>
                </div>

                <!-- TAB 2: SQLITE DATABASE TABLE -->
                <div class="tab-pane fade" id="table" role="tabpanel">
                    <div class="d-flex flex-wrap justify-content-between align-items-center mb-3 gap-2">
                        <h5 class="mb-0 fw-bold">SQLite Table View (Showing {{ current_limit }} rows)</h5>
                        
                        <!-- Row Display Limit Selector -->
                        <div class="btn-group btn-group-sm" role="group">
                            <span class="btn btn-outline-secondary disabled">Show:</span>
                            <a href="/?limit=25#table" class="btn btn-outline-primary {% if limit == '25' %}active{% endif %}">25</a>
                            <a href="/?limit=50#table" class="btn btn-outline-primary {% if limit == '50' %}active{% endif %}">50</a>
                            <a href="/?limit=100#table" class="btn btn-outline-primary {% if limit == '100' %}active{% endif %}">100</a>
                            <a href="/?limit=250#table" class="btn btn-outline-primary {% if limit == '250' %}active{% endif %}">250</a>
                            <a href="/?limit=all#table" class="btn btn-outline-primary {% if limit == 'all' %}active{% endif %}">All</a>
                        </div>
                    </div>

                    <div class="table-container border rounded">
                        {{ table_html | safe }}
                    </div>
                </div>

            </div>

        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""


def fig_to_base64(fig):
    """Encodes a Matplotlib figure directly into a base64 string for HTML display."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=130)
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return img_str


def generate_eda_plots(df):
    """Generates visual charts in-memory."""
    sns.set_theme(style="whitegrid")
    plots = {}
    subset = training_subset(df)

    # 1. Radius Valley Distribution Plot
    fig, (full, zoom) = plt.subplots(1, 2, figsize=(10, 4.2))
    sns.histplot(
        subset[config.RADIUS_COLUMN],
        bins=50,
        color="teal",
        log_scale=True,
        ax=full,
    )
    full.set_title("All sizes (Log Scale)")
    full.set_xlabel("Radius (Earth radii)")

    small = subset[subset[config.RADIUS_COLUMN].between(0.5, 4)]
    sns.histplot(small[config.RADIUS_COLUMN], bins=30, color="teal", ax=zoom)
    zoom.set_title("Zoom: 0.5 to 4 Earth radii")
    zoom.set_xlabel("Radius (Earth radii)")

    for ax in (full, zoom):
        ax.axvline(
            config.RADIUS_THRESHOLD,
            color="red",
            linestyle="--",
            label="Class Boundary (2.0)",
        )
    zoom.legend()
    fig.suptitle(
        "Planet Radius Distribution (Transit Planets)",
        fontsize=11,
        fontweight="bold",
    )
    plots["radius_dist"] = fig_to_base64(fig)

    # 2. Orbital Period vs Radius Scatter Plot
    fig, ax = plt.subplots(figsize=(9, 4.5))
    sns.scatterplot(
        data=with_class_labels(subset),
        x="pl_orbper",
        y=config.RADIUS_COLUMN,
        hue="planet_class",
        palette=CLASS_COLORS,
        alpha=0.6,
        s=25,
        ax=ax,
    )
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.axhline(config.RADIUS_THRESHOLD, color="black", linestyle=":")
    ax.set_title(
        "Orbital Period vs. Planet Radius", fontsize=11, fontweight="bold"
    )
    ax.set_xlabel("Orbital period (days, log scale)")
    ax.set_ylabel("Radius (Earth radii, log scale)")
    plots["period_vs_radius"] = fig_to_base64(fig)

    # 3. Correlation Heatmap
    fig, ax = plt.subplots(figsize=(8, 4.8))
    cols = [
        config.RADIUS_COLUMN,
        *config.FEATURE_COLUMNS,
        config.TARGET_COLUMN,
    ]
    sns.heatmap(
        subset[cols].corr(method="spearman"),
        annot=True,
        fmt=".2f",
        cmap="coolwarm",
        vmin=-1,
        vmax=1,
        ax=ax,
    )
    ax.set_title(
        "Spearman Correlation Heatmap", fontsize=11, fontweight="bold"
    )
    plots["correlation"] = fig_to_base64(fig)

    return plots


@app.route("/")
def home():
    if not config.DB_PATH.exists():
        run_pipeline()

    df = load_dataframe()
    transit_df = training_subset(df)
    terrestrial_count = int(transit_df[config.TARGET_COLUMN].sum())

    # Handle table row limit query parameter
    limit_param = request.args.get("limit", "50")
    if limit_param == "all":
        display_df = df
        current_limit_str = f"All {len(df):,}"
    else:
        try:
            limit_val = int(limit_param)
            display_df = df.head(limit_val)
            current_limit_str = f"{limit_val}"
        except ValueError:
            display_df = df.head(50)
            current_limit_str = "50"
            limit_param = "50"

    # Generate charts dynamically
    plots = generate_eda_plots(df)

    table_html = display_df.to_html(
        classes="table table-striped table-hover mb-0", index=False
    )

    return render_template_string(
        HTML_TEMPLATE,
        total=f"{len(df):,}",
        transit=f"{len(transit_df):,}",
        terrestrial=f"{terrestrial_count:,}",
        larger=f"{len(transit_df) - terrestrial_count:,}",
        table_html=table_html,
        limit=limit_param,
        current_limit=current_limit_str,
        plots=plots,
    )


@app.route("/refetch")
def refetch():
    """Route to force a live API fetch from NASA and recreate SQLite database."""
    run_pipeline()
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)