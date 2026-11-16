# Vessel Built Year Retrieval via API

The `year_built_api.py` module is used to retrieve vessel **year built** information via a commercial maritime data API and to store this information locally for use in the Agent-Based Model (ABM).

Vessel age is a key determinant of adoption behaviour in the model, as it directly influences remaining operational lifetime, expected net present value (ENPV) of retrofitting, and heterogeneity across the fleet. Incorporating empirically sourced build-year data improves the realism and empirical grounding of the simulation compared to purely synthetic age assumptions, as used in earlier ABM studies of wind-assisted propulsion adoption such as Chica et al. (2023).

---

## Data Source

Vessel build-year information is retrieved based on **IMO numbers** from the **Datalastic Vessel Tracker API**:

- **Datalastic API** — https://datalastic.com

Datalastic provides structured vessel registry and specification data, including construction year, via authenticated REST API endpoints. Access to the API normally requires a paid subscription. However, a limited free trial is available and was sufficient for the purposes of this project. The API key could therefore be obtained by the project group without incurring immediate costs.
Access credentials are supplied to the application through an environment variable (`DATALASTIC_API_KEY`) and are not stored directly in the codebase.

---

## Features

- **IMO-Based Identification**: Retrieves vessel build year using IMO numbers as unique vessel identifiers  
- **API-Based Access**: Uses authenticated HTTP requests to obtain structured vessel metadata  
- **Batch Processing**: Supports retrieval of build-year data for large vessel sets  
- **Incremental Checkpointing**: Periodically writes results to disk to prevent data loss during long-running API calls  
- **Failure Handling**: Gracefully handles missing data, API errors, and rate limiting without interrupting execution  
- **Resume Capability**: Supports restarting interrupted runs by skipping vessels with previously retrieved build-year data  
- **ABM Integration**: Output is directly consumed by `data_loader.py` to initialise vessel ages in the ABM  

---

## Output

The scraper produces a CSV file located at: ABM/vessel_built_years.csv


with the following structure:

| Column        | Description                                |
|---------------|--------------------------------------------|
| `imo`         | International Maritime Organization number |
| `year_built` | Year the vessel was constructed            |

The use of this file is optional but recommended. If the file is unavailable or incomplete, the ABM automatically falls back to synthetic vessel age generation based on Chica et al. (2023) to ensure uninterrupted simulation execution.

---

## Configuration Notes

- The API key must be provided via the environment variable `DATALASTIC_API_KEY`.
- The service is subscription-based; however, a free trial can be used for temporarily limited data collection.
- API request pacing and retry behaviour are configurable to comply with Datalastic rate limits.
- The save frequency can be adjusted through the `SAVE_EVERY` parameter to balance performance and robustness.

---
