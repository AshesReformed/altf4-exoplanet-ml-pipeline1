import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.patches import Patch

import config
from data_access import load_dataframe

TERRESTRIAL_LABEL = f"Terrestrial (< {config.RADIUS_THRESHOLD} R_Earth)"
LARGER_LABEL = f"Larger (>= {config.RADIUS_THRESHOLD} R_Earth)"
CLASS_COLORS = {TERRESTRIAL_LABEL: "crimson", LARGER_LABEL: "navy"}
LOG_SCALE_COLUMNS = {"pl_bmasse", "pl_orbper", "pl_orbsmax", "pl_insol", "st_rad"}
SUBSET_NOTE = f"({config.TRAINING_METHOD} planets)"
MIN_METHOD_COUNT = 10


def save_plot(filename: str, rect=(0, 0, 1, 1)) -> None:
    config.PLOTS_DIR.mkdir(exist_ok=True)
    plt.tight_layout(rect=rect)
    plt.savefig(config.PLOTS_DIR / filename, dpi=150)
    plt.close()
    print(f"[EDA] Saved plots/{filename}")


def training_subset(df):
    return df[df[config.METHOD_COLUMN] == config.TRAINING_METHOD]


def with_class_labels(df):
    labels = df[config.TARGET_COLUMN].map({1: TERRESTRIAL_LABEL, 0: LARGER_LABEL})
    return df.assign(planet_class=labels)


def print_summary(df) -> None:
    subset = training_subset(df)
    print(f"All planets: {len(df):,}")
    print("\nDiscovery methods:")
    print(df[config.METHOD_COLUMN].value_counts())

    print(f"\n--- {config.TRAINING_METHOD} planets only: {len(subset):,} ---")
    print("\nClass proportions:")
    print(subset[config.TARGET_COLUMN].value_counts(normalize=True).round(3))
    print("\nMissing values:")
    print(subset.isnull().sum())
    print("\nSummary statistics:")
    print(subset[[config.RADIUS_COLUMN, *config.FEATURE_COLUMNS]].describe().T[["mean", "std", "min", "50%", "max"]])
    print("\nMedian of each feature per class (0 = larger, 1 = terrestrial):")
    print(subset.groupby(config.TARGET_COLUMN)[config.FEATURE_COLUMNS].median().T.round(3))


def plot_method_comparison(df) -> None:
    summary = df.groupby(config.METHOD_COLUMN).agg(
        planets=(config.TARGET_COLUMN, "size"),
        terrestrial_share=(config.TARGET_COLUMN, "mean"),
        mass_share=("pl_bmasse", lambda values: values.notna().mean()),
    )
    summary = summary[summary["planets"] >= MIN_METHOD_COUNT].sort_values("planets")
    labels = [f"{name} (n={count:,})" for name, count in summary["planets"].items()]

    fig, (left, right) = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
    terrestrial_bars = left.barh(labels, summary["terrestrial_share"] * 100, color="crimson")
    left.bar_label(terrestrial_bars, fmt="%.0f%%", padding=3)
    left.set_xlim(0, summary["terrestrial_share"].max() * 120)
    left.set_title("Terrestrial planets (%)")
    mass_bars = right.barh(labels, summary["mass_share"] * 100, color="gray")
    right.bar_label(mass_bars, fmt="%.0f%%", padding=3)
    right.set_title("Planets with a measured mass (%)")
    right.set_xlim(0, 115)
    fig.suptitle(f"Discovery Methods (at least {MIN_METHOD_COUNT} planets)")
    save_plot("method_comparison.png", rect=(0, 0, 1, 0.95))


def plot_data_overview(df) -> None:
    fig, (left, right) = plt.subplots(1, 2, figsize=(11, 4))

    counts = with_class_labels(df)["planet_class"].value_counts()
    left.bar(counts.index, counts.values, color=[CLASS_COLORS[name] for name in counts.index])
    left.set_title("Class Balance")
    left.set_ylabel("Number of planets")

    missing = df[config.FEATURE_COLUMNS].isnull().mean().sort_values() * 100
    right.barh(missing.index, missing.values, color="gray")
    right.set_title("Missing Values per Feature")
    right.set_xlabel("Missing (%)")
    fig.suptitle(f"Data Overview {SUBSET_NOTE}")
    save_plot("data_overview.png", rect=(0, 0, 1, 0.95))


def plot_radius_distribution(df) -> None:
    fig, (full, zoom) = plt.subplots(1, 2, figsize=(12, 5))

    sns.histplot(df[config.RADIUS_COLUMN], bins=60, color="teal", log_scale=True, ax=full)
    full.set_title("All sizes")
    full.set_xlabel("Radius (Earth radii, log scale)")

    small = df[df[config.RADIUS_COLUMN].between(0.5, 4)]
    sns.histplot(small[config.RADIUS_COLUMN], bins=40, color="teal", ax=zoom)
    zoom.set_title("Zoom: 0.5 to 4 Earth radii")
    zoom.set_xlabel("Radius (Earth radii)")

    for axis in (full, zoom):
        axis.axvline(config.RADIUS_THRESHOLD, color="red", linestyle="--", label="Class boundary")
    zoom.legend()
    fig.suptitle(f"Planet Radius Distribution {SUBSET_NOTE}")
    save_plot("radius_distribution.png", rect=(0, 0, 1, 0.95))


def plot_feature_by_class(df) -> None:
    plot_df = with_class_labels(df)
    fig, axes = plt.subplots(3, 3, figsize=(14, 10))
    for axis, column in zip(axes.flat, config.FEATURE_COLUMNS):
        sns.histplot(
            data=plot_df,
            x=column,
            hue="planet_class",
            palette=CLASS_COLORS,
            stat="density",
            common_norm=False,
            element="step",
            log_scale=column in LOG_SCALE_COLUMNS,
            legend=False,
            ax=axis,
        )
        axis.set_title(column)
        axis.set_ylabel("")
    handles = [Patch(facecolor=color, edgecolor=color, alpha=0.4, label=name) for name, color in CLASS_COLORS.items()]
    fig.legend(handles=handles, loc="lower center", ncol=2)
    fig.suptitle(f"Feature Distributions by Class {SUBSET_NOTE}")
    save_plot("feature_by_class.png", rect=(0, 0.05, 1, 0.97))


def plot_period_vs_radius(df) -> None:
    plt.figure(figsize=(9, 6))
    sns.scatterplot(
        data=with_class_labels(df),
        x="pl_orbper",
        y=config.RADIUS_COLUMN,
        hue="planet_class",
        palette=CLASS_COLORS,
        alpha=0.6,
        s=25,
    )
    plt.xscale("log")
    plt.yscale("log")
    plt.axhline(config.RADIUS_THRESHOLD, color="black", linestyle=":")
    plt.title(f"Orbital Period vs. Planet Radius {SUBSET_NOTE}")
    plt.xlabel("Orbital period (days, log scale)")
    plt.ylabel("Radius (Earth radii, log scale)")
    plt.legend(title="Planet class")
    save_plot("period_vs_radius.png")


def plot_correlation_heatmap(df) -> None:
    columns = [config.RADIUS_COLUMN, *config.FEATURE_COLUMNS, config.TARGET_COLUMN]
    plt.figure(figsize=(9, 7))
    sns.heatmap(df[columns].corr(method="spearman"), annot=True, fmt=".2f", cmap="coolwarm", vmin=-1, vmax=1)
    plt.title(f"Spearman Correlation Heatmap {SUBSET_NOTE}")
    save_plot("correlation_heatmap.png")


def generate_plots(df) -> None:
    sns.set_theme(style="whitegrid")
    plot_method_comparison(df)

    subset = training_subset(df)
    plot_data_overview(subset)
    plot_radius_distribution(subset)
    plot_feature_by_class(subset)
    plot_period_vs_radius(subset)
    plot_correlation_heatmap(subset)


def run_eda() -> None:
    df = load_dataframe()
    print_summary(df)
    generate_plots(df)


if __name__ == "__main__":
    run_eda()
