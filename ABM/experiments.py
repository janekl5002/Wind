import pandas as pd
import numpy as np
import mesa
import matplotlib.pyplot as plt
import seaborn as sns
print(pd.__version__, np.__version__, mesa.__version__)
from data_loader import load_mrv_vessel_data
from model import WASPAdoptionModel

# Load vessel_data once

vessel_data = load_mrv_vessel_data(
    "ABM/2024-v141-18122025-EU MRV Publication of information.xlsx",
    debug = True
)

# Model Run Function

def run_model(vessel_data, **kwargs):
    model = WASPAdoptionModel(vessel_data, **kwargs)
    for _ in range(360):
        model.step()
    return model


# Extract Agent Features for Analysis

def extract_agent_table(model):
    rows = []
    for a in model.agents:
        rows.append({
            "adopted": int(a.adopted),
            "aware_end": int(a.aware),
            "fuel_use_monthly": float(a.fuel_use_monthly),
            "mileage_annual": float(a.mileage_annual),
            "remaining_life": int(a.remaining_life),
            "age_years": float(a.age_years),
        })
    custom_df = pd.DataFrame(rows)
    return custom_df


# Run Base Model

model_base = run_model(vessel_data, initial_awareness_share = 0.02)
custom_df = extract_agent_table(model_base)
print("Adoption rate:", custom_df["adopted"].mean())


# Quantify Feature Importance

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

def feature_importance_logit(custom_df):
    
    X = custom_df[["fuel_use_monthly", "mileage_annual", "remaining_life", "age_years"]].values
    y = custom_df["adopted"].values
    # in case of stratify crash
    strat = y if (y.sum() > 0 and y.sum() < len(y)) else None

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=0, stratify=strat
    )
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    clf = LogisticRegression(max_iter = 2000)
    clf.fit(X_train_s, y_train)

    feature_names = ["fuel_use_monthly", "mileage_annual", "remaining_life", "age_years"]
    coefs = clf.coef_[0]
    ranked = sorted(zip(feature_names, coefs), key=lambda x: abs(x[1]), reverse=True)

    print("\nFeature importance (logit |coef|):")
    for name, c in ranked:
        print(f"{name:>16}: {c:+.4f}")
    print("Test accuracy:", clf.score(X_test_s, y_test))

feature_importance_logit(custom_df)


# Sensitivity Analysis

for p in [0.0005, 0.00118, 0.002]:
    for q in [0.02, 0.039, 0.06]:
        model_sens = run_model(vessel_data, p = p, q = q)
        adoption_rate = extract_agent_table(model_sens)["adopted"].mean()
        print(f"p={p}, q={q}, final adoption={adoption_rate:.3f}")


# Fuel Consumption Intensity by Ship Type

print("\n--- Fuel consumption intensity by ship type ---")
print(vessel_data.groupby("ship_type")["fuel_intensity_kg_nm"].describe())

# Visualizations

# Fuel Intensity Distribution

plt.figure(figsize = (6, 4))
plt.hist(vessel_data["fuel_intensity_kg_nm"], bins = 50, color = "skyblue", edgecolor = "black")
plt.xlabel("Fuel consumption [kg / nm]")
plt.ylabel("Number of vessels")
plt.title("Distribution of Fuel Intensity (EU MRV 2024)")
plt.xlim(0, 400)
plt.grid(True)
plt.show()

# Fuel Use vs Distance

plt.figure(figsize = (6, 4))
plt.scatter(vessel_data["miles"], vessel_data["fuel"]* 12, alpha = 0.3, s = 10)
plt.xlabel("Annual distance [nm]")
plt.ylabel("Yearly fuel consumption [t]")
plt.title("Fuel Use vs Distance (MRV vessels)")
plt.grid(True)
plt.show()

# Heatmap: Adoption vs Age and Distance

age_bins = pd.cut(vessel_data["age"], bins = [0, 10, 20, 30])
dist_bins = pd.qcut(vessel_data["miles"], q = 4)

heat_df = pd.DataFrame({
    "Age bin": age_bins,
    "Distance bin": dist_bins,
    "Adopted": [a.adopted for a in model_base.agents]
})

heatmap_data = heat_df.pivot_table(
    values = "Adopted",
    index = "Age bin",
    columns = "Distance bin",
    aggfunc = "mean"
)

plt.figure(figsize = (7, 5))
sns.heatmap(heatmap_data, annot=True, cmap = "viridis", fmt = ".2f")
plt.title("Adoption probability by age and distance")
plt.tight_layout()
plt.show()
