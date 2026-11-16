import pandas as pd
import numpy as np
from pathlib import Path

def load_mrv_vessel_data(
    path = "ABM/2024-v141-18122025-EU MRV Publication of information.xlsx",
    built_csv = "ABM/vessel_built_years.csv",
    max_fuel_intensity_kg_nm = 500,
    min_fuel_intensity_kg_nm = 5,
    debug = False
):
    """
    Load and clean EU MRV vessel data for ABM use.

    Returns:
        vessel_data: DataFrame with columns
            - age
            - fuel (monthly tonnes)
            - fuel_intensity_kg_nm
            - miles (annual nautical miles)
            - co2_monthly_kg
            - ship_type
    """

    # Read Excel with multi-level headers
    mrv = pd.read_excel(path, header = [0, 1, 2])

    # Flatten headers
    mrv.columns = [
        " | ".join([str(x).strip() for x in col if str(x) != "nan"])
        for col in mrv.columns
    ]

    # Identify required columns
    fuel_col = next(
        c for c in mrv.columns
        if "Total fuel consumption" in c and "[m tonnes]" in c
    )

    intensity_col = next(
        c for c in mrv.columns
        if "Fuel consumption per distance [kg / n mile]" in c
    )

    ship_type_col = next(
        c for c in mrv.columns
        if c.endswith("Ship type")
    )

    imo_col = next(c for c in mrv.columns if "IMO" in c and "Number" in c)

    co2_col = next(c for c in mrv.columns if "CO₂ emissions per distance" in c and "[kg CO₂ / n mile]" in c)

    # Convert to numeric
    mrv["fuel_annual_tonnes"] = pd.to_numeric(mrv[fuel_col], errors = "coerce")
    mrv["fuel_per_nm_kg"] = pd.to_numeric(mrv[intensity_col], errors = "coerce")
    mrv["ship_type"] = mrv[ship_type_col].astype(str)
    mrv[imo_col] = pd.to_numeric(mrv[imo_col], errors = "coerce")
    mrv["co2_per_nm_kg"] = pd.to_numeric(mrv[co2_col], errors = "coerce")

    # Drop invalid rows
    mrv = mrv.dropna(
        subset=["fuel_annual_tonnes", "fuel_per_nm_kg", "co2_per_nm_kg"]
    )

    mrv = mrv[
        (mrv["fuel_annual_tonnes"] > 0) &
        (mrv["fuel_per_nm_kg"] > 0) &
        (mrv["co2_per_nm_kg"] > 0)
    ]

    # Remove imporobable fuel intensities
    mrv = mrv[
        (mrv["fuel_per_nm_kg"] >= min_fuel_intensity_kg_nm) &
        (mrv["fuel_per_nm_kg"] <= max_fuel_intensity_kg_nm)
    ]

    # Compute annual distance
    mrv["distance_nm"] = (
        mrv["fuel_annual_tonnes"] * 1_000 / mrv["fuel_per_nm_kg"]
    )

    # Final clean
    mrv = mrv[
        (mrv["distance_nm"] > 1_000) &
        (mrv["distance_nm"] < 200_000)
    ]

    # Vessel age handling
    current_year = 2024
    # Year of latest EU MRV data
    built_path = Path(built_csv)

    if built_path.exists():
        try:
            built = pd.read_csv(built_path)
            mrv = mrv.merge(built, left_on = imo_col, right_on = "imo", how = "left")
            mrv["age"] = current_year - mrv["year_built"]

            if debug:
                print(f"Loaded vessel ages from {built_path}")

        except Exception as e:
            if debug:
                print(f"Failed to load built-year data ({e}). Using random vessel ages.")
            mrv["age"] = np.random.uniform(5, 20, len(mrv))
    else:
        if debug:
            print(f"Built-year file not found ({built_path}). Using random vessel ages.")
        mrv["age"] = np.random.uniform(5, 20, len(mrv))

    # Fallback for missing or invalid ages
    missing_age = mrv["age"].isna() | (mrv["age"] < 0)
    mrv.loc[missing_age, "age"] = np.random.uniform(5, 20, missing_age.sum())

    # Cap at max lifetime
    mrv["age"] = mrv["age"].clip(lower = 0, upper = 30)

    # Monthly CO2 baseline
    mrv["co2_monthly_kg"] = (mrv["distance_nm"] / 12) * mrv["co2_per_nm_kg"]

    # Build ABM-ready vessel data
    vessel_data = pd.DataFrame({
        "age": mrv["age"],
        "fuel": mrv["fuel_annual_tonnes"] / 12,
        "fuel_intensity_kg_nm": mrv["fuel_per_nm_kg"],
        "miles": mrv["distance_nm"],
        "ship_type": mrv["ship_type"],
        "co2_monthly_kg": mrv["co2_monthly_kg"],
    }).reset_index(drop = True)

    return vessel_data
