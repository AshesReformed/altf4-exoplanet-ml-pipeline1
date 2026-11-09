# 🪐 ALT-F4 | Exoplanet Structural Classification Pipeline

An ETL (Extract, Transform, Load) and Exploratory Data Analysis (EDA) pipeline for confirmed exoplanets using data from the [NASA Exoplanet Archive](https://exoplanetarchive.ipac.caltech.edu/).

This is **Project 1 of 3**. It retrieves, validates, and processes exoplanet data before storing it in an SQLite database. The resulting dataset serves as the foundation for the classification models developed in Projects 2 and 3.

The project also includes a Flask-based web dashboard configured for deployment on Vercel.

## Dataset

This project uses the NASA Exoplanet Archive's `pscomppars` table, which contains information about confirmed exoplanets. Data is retrieved through NASA's Table Access Protocol (TAP) API without requiring an API key.

The dataset includes planetary measurements such as:

- Planetary radius
- Planetary mass
- Orbital period
- Semi-major axis
- Equilibrium temperature
- Insolation flux

It also includes host-star properties such as:

- Stellar temperature
- Stellar radius
- Stellar mass
- Stellar metallicity

Additional information, including planet names, host-star names, discovery methods, and discovery years, is also stored.

## ETL Pipeline

The pipeline consists of five main stages.

### 1. Extract

- Retrieve data from the NASA TAP API using the `pscomppars` table.
- Request the required fields configured in `config.py`.
- Save the raw response to `data/raw/pscomppars.json`.
- If the API request fails, use the previously saved snapshot if available.

### 2. Validate

Records are validated using Pydantic.

- Remove records without a valid planet name or positive planetary radius.
- Count and report invalid records.
- Convert invalid optional numerical measurements to `NULL`.
- Apply appropriate validation rules to physical measurements while preserving valid negative metallicity values.

### 3. Clean

- Remove planetary mass estimates identified as being derived from planetary radius using the `pl_bmassprov` field.
- Remove duplicate planet names.

This helps reduce the risk of target leakage when planetary radius is used to define the classification label.

### 4. Create Target Labels

A binary target variable named `is_terrestrial` is created using planetary radius:

- `1` — Planetary radius is below 2.0 Earth radii.
- `0` — Planetary radius is 2.0 Earth radii or greater.

This is a size-based classification rule. It does not establish the actual composition of a planet or confirm that every planet below the threshold is rocky.

### 5. Load

The cleaned dataset is stored in an SQLite database named `exoplanets.db`, inside a table called `exoplanets`.

Database features include:

- `pl_name` as the primary key.
- A positive-radius constraint.
- A constraint ensuring that `is_terrestrial` contains only `0` or `1`.
- Missing feature values preserved as `NULL` for later preprocessing.

## Analysis Scope: Transit Planets

The database retains planets discovered through different detection methods. However, the exploratory analysis and default classification workflow focus on **transiting planets**.

Transit observations provide planetary-radius measurements that are directly relevant to the target definition. Restricting the main analysis to transit planets also helps maintain consistency across the selected discovery category.

Other discovery methods remain available in the database and can be included in additional analyses.

**Important for Project 2:** Planets orbiting the same host star may share similar stellar properties. Therefore, training and testing datasets should be split by `hostname` to prevent planets from the same star system appearing in both sets.

## Exploratory Data Analysis

The exploratory analysis is performed using `eda_analysis.py`.

It prints summary statistics to the terminal and generates six visualizations saved in the `plots/` directory.

| Plot | Description |
|---|---|
| `method_comparison.png` | Compares target-class proportions and mass availability across discovery methods. |
| `data_overview.png` | Displays class balance and missing-value proportions across selected features. |
| `radius_distribution.png` | Shows planetary-radius distribution, including a closer view of the 2.0 Earth-radius threshold. |
| `feature_by_class.png` | Compares feature distributions between the two target classes. |
| `period_vs_radius.png` | Visualizes the relationship between orbital period and planetary radius. |
| `correlation_heatmap.png` | Displays Spearman correlations between selected numerical features. |

`method_comparison.png` uses all planets, while the remaining five visualizations use transit planets only.

## Flask Dashboard

The project includes a web-based dashboard built using **Flask** and configured for deployment on **Vercel**.

The dashboard is implemented in `api/index.py`.

### Dashboard Features

- **Dataset Overview:** Displays summary counts for the complete dataset, transit planets, and both target classes.
- **Planetary Radius Distribution:** Visualizes the distribution of planetary radii.
- **Period vs. Radius:** Shows the relationship between orbital period and planetary radius.
- **Correlation Heatmap:** Displays correlations between selected numerical variables.
- **Database Viewer:** Allows users to explore stored records with selectable row limits.
- **Data Refresh:** Provides an option to retrieve updated data from NASA through the `/refetch` route.

The dashboard generates its visualizations dynamically rather than relying on the saved EDA image files.

### Vercel Deployment

The Flask application is configured for Vercel using `vercel.json`.

The configuration uses `api/index.py` as the Python application entry point and routes incoming requests to the Flask application.

To deploy:

1. Push the project to GitHub.
2. Import the repository into [Vercel](https://vercel.com/).
3. Keep the existing Vercel configuration.
4. Deploy the application.
5. Check the deployment logs to confirm that the application starts correctly.

**Deployment consideration:** The application currently uses an SQLite database stored in the project directory. Vercel's serverless environment does not guarantee persistent writable storage for local database files. Database creation, data refresh, and persistence should therefore be tested in the deployed environment.

## Project Structure

| File / Directory | Purpose |
|---|---|
| `config.py` | Stores shared settings, paths, column names, feature definitions, and the radius threshold. |
| `etl_pipeline.py` | Handles data extraction, validation, cleaning, target creation, and database loading. |
| `data_access.py` | Provides functions for loading database records, features, target labels, and host-star groups. |
| `eda_analysis.py` | Generates summary statistics and six exploratory visualizations. |
| `main.py` | Executes the ETL pipeline followed by exploratory data analysis. |
| `api/index.py` | Contains the Flask dashboard and application entry point for Vercel. |
| `vercel.json` | Configures the Vercel Python runtime and request routing. |
| `requirements.txt` | Contains the Python dependencies required by the project. |
| `data/raw/` | Stores the raw NASA response or saved snapshot. |
| `plots/` | Stores the generated EDA visualizations. |
| `exoplanets.db` | SQLite database containing the processed dataset. |

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/AshesReformed/altf4-exoplanet-ml-pipeline.git

cd altf4-exoplanet-ml-pipeline
```

### 2. Create a Virtual Environment

```bash
python -m venv .venv
```

Activate the environment:

**Windows:**

```bash
.venv\Scripts\activate
```

**macOS / Linux:**

```bash
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Pipeline

```bash
python main.py
```

This executes the ETL workflow, builds the SQLite database, and generates the exploratory analysis plots.

### 5. Run the Dashboard Locally

```bash
python api/index.py
```

The Flask development server starts locally. Open the address displayed in the terminal to access the dashboard.

For production deployment, use Vercel.

## Using the Dataset in Later Projects

The `data_access.py` module provides functions for loading model features, target labels, and host-star identifiers.

Example:

```python
from data_access import load_xy, load_groups

# Load transit planets using the default configuration
X, y = load_xy()

# Load host-star identifiers for grouped train/test splitting
groups = load_groups()

# Load planets from all discovery methods
X_all, y_all = load_xy(method=None)
```

The default feature list is defined in `config.py`.

Planetary radius is excluded from the feature matrix because it is used to create the `is_terrestrial` target variable. Including it as a feature would introduce direct target leakage.

The `load_xy()` function also supports `include_mass=False` when planetary mass needs to be excluded from a modelling experiment.

## Limitations

- **Simplified classification rule:** The 2.0 Earth-radius threshold is a size-based definition and does not directly determine planetary composition.
- **Missing measurements:** Some planetary and stellar measurements are unavailable. Missing values are retained as `NULL` for later preprocessing.
- **Measurement uncertainty:** Archive measurements can have different sources and levels of uncertainty. These should be considered when interpreting analysis and model results.
- **Observational bias:** The dataset contains confirmed planets discovered through available observation methods. It should not be considered a complete representation of all planets in the galaxy.
- **Deployment storage:** The dashboard uses a local SQLite database. Persistence and data-refresh behaviour should be tested in Vercel's serverless environment.

## Project Contributors

**Team ALT-F4**

This project was developed collaboratively by:

| Contributor | GitHub Profile |
|---|---|
| **AshesReformed** | [@AshesReformed](https://github.com/AshesReformed) |
| **velnox-m** | [@velnox-m](https://github.com/velnox-m) |
| **kamranbashir56** | [@kamranbashir56](https://github.com/kamranbashir56) |
| **hanzla269** | [@hanzla269](https://github.com/hanzla269) |

## Data Source

[NASA Exoplanet Archive](https://exoplanetarchive.ipac.caltech.edu/)

**Dataset Table:** `pscomppars`
