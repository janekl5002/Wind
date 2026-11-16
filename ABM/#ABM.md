# Agent-Based Model for the Adoption of Wind-Assisted Ship Propulsion (WASP)

This folder contains the complete implementation of an **agent-based simulation framework** designed to analyse the adoption dynamics of **wind-assisted ship propulsion (WASP)** technologies in commercial shipping fleets.

The model integrates **empirical vessel-level data**, **behavioural diffusion theory**, and **economic decision-making** to evaluate adoption pathways.
---

## Folder Structure

```text
ABM/
│
├── run.py              # Main experiment and analysis script
├── experiments.py      # Secondary experiment and analysis script
├── model.py            # Core ABM logic and model-level dynamics
├── agent.py            # Vessel agent definition and decision-making
├── data_loader.py      # EU MRV data preprocessing and enrichement with scraped vessel age
├── utils.py            # Economic helper functions (ENPV, fuel price)
│
├── year_built_api.py   # Vessel build-year data scraping
├── vessel_built_years.csv
│
├── fuel_price_api.py   # Fuel price and monthly changes API
├── test_fuel_api.py    # Tests confirming whether or not the fuel price API works
│
└── 2024-v141-18122025-EU MRV Publication of information.xlsx
