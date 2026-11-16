import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from data_loader import load_mrv_vessel_data
from model import WASPAdoptionModel

# Global plotting style
plt.rcParams.update({
    "figure.figsize": (8, 5),
    "axes.grid": True,
    "grid.alpha": 0.3,
    "axes.spines.top": False,
    "axes.spines.right": False,
})

MONTHS = 360
YEARS = np.arange(MONTHS) / 12


# Load and inspect MRV data

vessel_data = load_mrv_vessel_data(
    "ABM/2024-v141-18122025-EU MRV Publication of information.xlsx",
    debug=True
)

print("\n--- Vessel data preview ---")
print(vessel_data.head())


# Helper functions

def run_model(vessel_data, reporting_active, reporting_coverage, seed = 1):
    model = WASPAdoptionModel(
        vessel_data,
        use_fuel_price_api = True,  # Enable API integration for real fuel prices
        reporting_active = reporting_active,
        reporting_coverage = reporting_coverage,
        seed = seed
    )
    for _ in range(MONTHS):
        model.step()
    return model


def adoption_share(model):
    return np.array(model.adoption_history) / len(model.vessels)


# Scenario table

scenarios = {
    "No reporting": 0.0,
    "Low reporting": 0.25,
    "Medium reporting": 0.5,
    "Full reporting": 1.0,
}

results = []

for name, coverage in scenarios.items():
    model = run_model(
        vessel_data,
        reporting_active=coverage > 0,
        reporting_coverage=coverage,
        seed=1
    )
    results.append({
        "Scenario": name,
        "Reporting coverage": coverage,
        "Final adoption share": model.adoption_history[-1] / len(model.vessels)
    })

results_df = pd.DataFrame(results)
results_df["Final adoption share"] = results_df["Final adoption share"].map("{:.1%}".format)

print("\n--- Scenario comparison ---")
print(results_df)


# Core scenarios
# Full reporting
model_reporting = WASPAdoptionModel(vessel_data, reporting_active = True, reporting_coverage = 1.0)
for _ in range(360):
    model_reporting.step()

# Partial reporting
model_partial_reporting = WASPAdoptionModel(vessel_data, reporting_active = True, reporting_coverage = 0.25)
for _ in range(360):
    model_partial_reporting.step()

# No reporting
model_no_reporting = WASPAdoptionModel(vessel_data, reporting_active = False)
for _ in range(360):
    model_no_reporting.step()


# Adoption curves

plt.figure()
plt.plot(YEARS, adoption_share(model_reporting), label = "Full reporting")
plt.plot(YEARS, adoption_share(model_partial_reporting), label = "Partial reporting")
plt.plot(YEARS, adoption_share(model_no_reporting), label = "No reporting")
plt.xlabel("Time [years]")
plt.ylabel("Adoption share")
plt.title("WASP adoption over time")
plt.legend()
plt.tight_layout()
plt.show()


# CO2 and Fuel Tracking
def plot_fuel_co2(model, label):
    months = len(model.fuel_baseline_history)
    years = np.arange(months) / 12  # convert months to years

    plt.figure(figsize = (12, 5))

    # Fuel
    plt.subplot(1, 2, 1)
    plt.plot(years, model.fuel_baseline_history, label = "Baseline")
    plt.plot(years, model.fuel_saved_history, label = "Saved")
    plt.plot(years, model.fuel_net_history, label = "Net")
    plt.xlabel("Time [years]")
    plt.ylabel("Monthly Fuel [t]")
    plt.title(f"Fuel Consumption ({label})")
    plt.legend()
    plt.grid(True)

    # CO2
    plt.subplot(1, 2, 2)
    plt.plot(years, model.co2_baseline_history, label = "Baseline")
    plt.plot(years, model.co2_saved_history, label = "Saved")
    plt.plot(years, model.co2_net_history, label = "Net")
    plt.xlabel("Time [years]")
    plt.ylabel("CO2 Emissions [tCO2]")
    plt.title(f"CO2 Emissions ({label})")
    plt.legend()
    plt.grid(True)

    plt.tight_layout()
    plt.show()


# Plot fuel and CO2 for different reporting scenarios
plot_fuel_co2(model_reporting, "Full Reporting")
plot_fuel_co2(model_partial_reporting, "Partial Reporting")
plot_fuel_co2(model_no_reporting, "No Reporting")


# Uncertainty analysis

seeds = range(10)
records = []

for seed in seeds:
    model = run_model(vessel_data, True, 0.5, seed = seed)
    records.append(adoption_share(model))

records = np.array(records)

mean_adoption = records.mean(axis = 0)
p10 = np.percentile(records, 10, axis = 0)
p90 = np.percentile(records, 90, axis = 0)

plt.figure()
plt.plot(YEARS, mean_adoption, label = "Mean adoption")
plt.fill_between(YEARS, p10, p90, alpha = 0.3, label = "10–90%")
plt.xlabel("Time [years]")
plt.ylabel("Adoption share")
plt.title("Adoption uncertainty (partial reporting)")
plt.legend()
plt.tight_layout()
plt.show()


# Adoption by ship type

agent_df = pd.DataFrame({
    "ship_type": vessel_data["ship_type"],
    "adopted": [a.adopted for a in model_reporting.vessels]
})

adoption_by_type = agent_df.groupby("ship_type")["adopted"].mean().sort_values()

adoption_by_type.plot(kind = "barh")
plt.xlabel("Adoption share")
plt.title("Adoption by ship type (full reporting)")
plt.tight_layout()
plt.show()


# Reporting × Initial Awareness Heatmap

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Heatmap parameters
reporting_coverages = np.linspace(0.0, 1.0, 6)
initial_awareness_levels = [0.01, 0.05, 0.10, 0.20]
years = 30
steps = years * 12
seed = 42

# Prepare storage
heatmap_results = pd.DataFrame(
    index=[int(a * 100) for a in initial_awareness_levels],
    columns=[int(r * 100) for r in reporting_coverages],
    dtype=float
)

# Run simulations
for awareness in initial_awareness_levels:
    for coverage in reporting_coverages:

        model = WASPAdoptionModel(
            vessel_data,
            reporting_active = coverage > 0,
            reporting_coverage = coverage,
            initial_awareness_share = awareness,
            seed = seed
        )

        for _ in range(steps):
            model.step()

        final_adoption = model.adoption_history[-1] / len(model.vessels)
        heatmap_results.loc[int(awareness * 100), int(coverage * 100)] = final_adoption

# Display results
print("\nFinal adoption heatmap (rows = initial awareness %, columns = reporting %):")
print(heatmap_results)

# Plot heatmap
plt.figure(figsize = (8, 5))
im = plt.imshow(
    heatmap_results.values,
    origin = "lower",
    aspect = "auto",
    cmap = "YlGnBu",
    vmin = 0,
    vmax = 1
)

# Axis labels
plt.xticks(
    ticks=range(len(heatmap_results.columns)),
    labels=[f"{c}%" for c in heatmap_results.columns]
)
plt.yticks(
    ticks=range(len(heatmap_results.index)),
    labels=[f"{i}%" for i in heatmap_results.index]
)
plt.xlabel("Reporting Coverage")
plt.ylabel("Initial Awareness Level")
plt.title("Reporting × Initial Awareness Heatmap\n(Final WASP Adoption Share after 30 years)")

# Colorbar
cbar = plt.colorbar(im)
cbar.set_label("Final Adoption Share")

plt.tight_layout()
plt.show()


# Decision visualisation

def plot_decision_snapshots(model, years, label = "", xlim = None, ylim = None):
    """
    Plot multiple decision-boundary snapshots in one figure.
    years: list of ints
    xlim/ylim: optional tuples to fix axis ranges across panels
    """
    n = len(years)
    fig, axes = plt.subplots(1, n, figsize = (4 * n, 4), sharex = True, sharey = True)
    if n == 1:
        axes = [axes]

    for ax, year in zip(axes, years):
        xs, ys, cs = [], [], []

        for a in model.vessels:
            # Only meaningful once they are aware and have a computed ENPV
            if a.aware and a.last_enpv is not None and a.last_expected_saving is not None:
                xs.append(a.last_expected_saving)
                ys.append(a.last_enpv)
                cs.append("tab:orange" if a.adopted else "tab:blue")

        ax.scatter(xs, ys, c = cs, alpha = 0.35, s = 10)
        ax.axhline(0, linestyle="--", linewidth=1)
        ax.set_title(f"Year {year}")

        if xlim is not None:
            ax.set_xlim(*xlim)
        if ylim is not None:
            ax.set_ylim(*ylim)

        ax.set_xlabel("Risk-adjusted expected saving")

    axes[0].set_ylabel("ENPV of retrofit")
    fig.suptitle(f"Decision boundaries over time {label}".strip())
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    plt.show()


def plot_state_stack(state_history, label = ""):
    """
    Plot how vessels move through decision stages over time.
    state_history: list of dicts with keys: unaware, aware_not_adopted, adopted
    """
    df = pd.DataFrame(state_history)
    years = np.arange(len(df)) / 12

    plt.figure(figsize = (8, 5))
    plt.stackplot(
        years,
        df["unaware"], df["aware_not_adopted"], df["adopted"],
        labels = ["Unaware", "Aware (no adoption)", "Adopted"],
        alpha = 0.8
    )
    plt.xlabel("Time [years]")
    plt.ylabel("Number of vessels")
    plt.title(f"Decision stages over time {label}".strip())
    plt.legend(loc = "upper left")
    plt.tight_layout()
    plt.show()


# Partial reporting scenario (collect state history and yearly decision snapshots)
model = WASPAdoptionModel(
    vessel_data,
    reporting_active = True,
    reporting_coverage = 0.25,
    seed=1
)

state_history = []
snapshots = {}

for t in range(MONTHS):
    model.step()

    unaware = sum((not a.aware) for a in model.vessels)
    adopted = sum(a.adopted for a in model.vessels)
    aware_not_adopted = len(model.vessels) - unaware - adopted

    state_history.append({
        "unaware": unaware,
        "aware_not_adopted": aware_not_adopted,
        "adopted": adopted
    })

    # Store snapshots at selected years
    if (t + 1) % 12 == 0:
        year = (t + 1) // 12
        if year in [1, 2, 3, 5, 10, 15, 30]:
            xs, ys, cs = [], [], []
            for a in model.vessels:
                if a.aware and a.last_enpv is not None and a.last_expected_saving is not None:
                    xs.append(a.last_expected_saving)
                    ys.append(a.last_enpv)
                    cs.append("tab:orange" if a.adopted else "tab:blue")
            snapshots[year] = (xs, ys, cs)

# Plot state pipeline
plot_state_stack(state_history, label="(Partial reporting)")

# Decide axis limits from stored snapshots
all_x = np.concatenate([np.array(snapshots[y][0]) for y in snapshots if len(snapshots[y][0]) > 0]) \
        if len(snapshots) else np.array([])
all_y = np.concatenate([np.array(snapshots[y][1]) for y in snapshots if len(snapshots[y][1]) > 0]) \
        if len(snapshots) else np.array([])

xlim = (float(np.nanpercentile(all_x, 1)), float(np.nanpercentile(all_x, 99))) if all_x.size else None
ylim = (float(np.nanpercentile(all_y, 1)), float(np.nanpercentile(all_y, 99))) if all_y.size else None

# Temporarily attach the stored snapshot values back to agents for plotting convenience
def plot_decision_snapshots_from_store(snapshots, label = "", xlim = None, ylim = None):
    years = sorted(snapshots.keys())
    n = len(years)
    fig, axes = plt.subplots(1, n, figsize=(4 * n, 4), sharex = True, sharey = True)
    if n == 1:
        axes = [axes]

    for ax, year in zip(axes, years):
        xs, ys, cs = snapshots[year]
        ax.scatter(xs, ys, c=cs, alpha = 0.35, s = 10)
        ax.axhline(0, linestyle="--", linewidth = 1)
        ax.set_title(f"Year {year}", fontsize = 5)
        ax.set_xlabel("Risk-adjusted expected saving", fontsize = 7)

        if xlim is not None:
            ax.set_xlim(*xlim)
        if ylim is not None:
            ax.set_ylim(*ylim)

    axes[0].set_ylabel("ENPV of retrofit")
    fig.suptitle(f"Decision boundaries over time {label}".strip())
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    plt.show()


plot_decision_snapshots_from_store(
    snapshots,
    label = "(Partial reporting)",
    xlim = xlim,
    ylim = ylim
)
