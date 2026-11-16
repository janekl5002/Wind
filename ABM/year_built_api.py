import os
import time
import random
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# Configuration

MRV_PATH = "ABM/2024-v141-18122025-EU MRV Publication of information.xlsx"
OUTPUT_PATH = "ABM/vessel_built_years.csv"

# The DATALASTIC_API_KEY was not included inside this notebook 
# as I had to sign up for a free trail to be able to use it
# and it is therefore connected to my payment information

DATALASTIC_API_KEY = os.getenv("DATALASTIC_API_KEY", "").strip()

# API endpoint (Ship Specs Info)
DATALASTIC_VESSEL_INFO_URL = "https://api.datalastic.com/api/v0/vessel_info"

# Rate limiting / pacing
REQUEST_DELAY = (0.4, 0.8)
TIMEOUT = 20

# Save every 10
SAVE_EVERY = 10

print("API key loaded:", bool(DATALASTIC_API_KEY))
print("CWD:", os.getcwd())
print("OUTPUT_PATH absolute:", os.path.abspath(OUTPUT_PATH))

# Load MRV file

def load_mrv_raw(path: str) -> pd.DataFrame:
    mrv = pd.read_excel(path, header = [0, 1, 2])
    mrv.columns = [
        " | ".join([str(x).strip() for x in col if str(x) != "nan"])
        for col in mrv.columns
    ]
    return mrv


# HTTP session w/ retries

def build_session() -> requests.Session:
    """
    Retries transient failures (5xx, some 429s depending on server behavior),
    uses exponential backoff.
    """
    session = requests.Session()
    retry = Retry(
        total = 5,
        connect = 5,
        read = 5,
        status = 5,
        backoff_factor = 1.0,
        status_forcelist = [429, 500, 502, 503, 504],
        allowed_methods = ["GET"],
        raise_on_status = False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


# Datalastic fetch

def fetch_year_built_datalastic(imo: int, session: requests.Session) -> int | None:
    """
    Calls:
      GET https://api.datalastic.com/api/v0/vessel_info?api-key=...&imo=...
    Returns:
      year_built as int, or None if missing/not found.
    """
    params = {"api-key": DATALASTIC_API_KEY, "imo": str(int(imo))}
    try:
        r = session.get(DATALASTIC_VESSEL_INFO_URL, params = params, timeout = TIMEOUT)
    except requests.RequestException as e:
        print(f"  !! Request error for IMO {imo}: {e}")
        return None

    # Handle obvious auth issues early
    if r.status_code in (401, 403):
        print(f"  !! Auth error (HTTP {r.status_code}) for IMO {imo}. Check API key.")
        return None

    if r.status_code == 429:
        # Rate limited: wait a bit longer and let outer loop continue
        retry_after = r.headers.get("Retry-After")
        sleep_s = int(retry_after) if retry_after and retry_after.isdigit() else 10
        print(f"  !! Rate limited (429) for IMO {imo}. Sleeping {sleep_s}s.")
        time.sleep(sleep_s)
        return None

    if r.status_code == 402:
        print(f"  !! HTTP 402 (Rate/plan limit) for IMO {imo}. Stopping run to avoid filling CSV with None.")
        raise SystemExit("Datalastic API limit reached (HTTP 402).")

    if r.status_code != 200:
        print(f"  !! HTTP {r.status_code} for IMO {imo}: {r.text[:200]}")
        return None

    try:
        data = r.json()
    except ValueError:
        print(f"  !! Non-JSON response for IMO {imo}: {r.text[:200]}")
        return None

    # Datalastic responses contain a "data" object/list; focus on a field named "year_built".
    year = None

    if isinstance(data, dict):
        # Common patterns: {"data": {...}} or {"data": [{...}]}
        payload = data.get("data", data)
        if isinstance(payload, dict):
            year = payload.get("year_built")
        elif isinstance(payload, list) and payload:
            year = payload[0].get("year_built")
    elif isinstance(data, list) and data:
        year = data[0].get("year_built")

    try:
        return int(year) if year is not None and str(year).isdigit() else None
    except Exception:
        return None


# Resume and batch runner
    
def load_existing_results(path: str) -> tuple[list[dict], set[int]]:
    if not os.path.exists(path):
        return [], set()

    try:
        df = pd.read_csv(path)
        if "imo" not in df.columns:
            return [], set()

        df["imo"] = pd.to_numeric(df["imo"], errors = "coerce")

        if "year_built" in df.columns:
            df["year_built"] = pd.to_numeric(df["year_built"], errors = "coerce")
            # Only treat as done if year_built is present
            done = set(df.loc[df["year_built"].notna(), "imo"].dropna().astype(int).tolist())
            records = df.loc[df["imo"].notna(), ["imo", "year_built"]].to_dict("records")
        else:
            done = set()
            records = df.loc[df["imo"].notna(), ["imo"]].to_dict("records")

        return records, done

    except Exception as e:
        print(f"Warning: couldn't read existing CSV for resume ({path}): {e}")
        return [], set()

def scrape_built_years_api(imo_list: list[int], save_every: int = SAVE_EVERY) -> pd.DataFrame:
    if not DATALASTIC_API_KEY:
        raise SystemExit(
            "Missing DATALASTIC_API_KEY.\n"
            "Set it as an environment variable, e.g.\n"
            "  export DATALASTIC_API_KEY='YOUR_KEY'\n"
        )

    session = build_session()

    existing_records, done_imos = load_existing_results(OUTPUT_PATH)
    remaining = [int(x) for x in imo_list if int(x) not in done_imos]

    out = existing_records[:] # Keep what I already have
    total = len(remaining)

    print(f"Total IMOs in input: {len(imo_list)}")
    if done_imos:
        print(f"Resuming: {len(done_imos)} already in {OUTPUT_PATH}, {total} remaining.")
    else:
        print(f"Starting fresh: {total} to fetch.")

    for i, imo in enumerate(remaining, 1):
        print(f"[{i}/{total}] Fetching IMO {imo} ...", end = "")
        year = fetch_year_built_datalastic(imo, session)
        print(f" year_built = {year}")

        out.append({"imo": int(imo), "year_built": year})

        # Quick check
        if i <= 10:
            print("  First years so far:", [r.get("year_built") for r in out[-i:]])

        # Checkpoint save
        if i % save_every == 0:
            df_chk = pd.DataFrame(out).drop_duplicates(subset=["imo"], keep="last")
            df_chk.to_csv(OUTPUT_PATH, index=False)
            print(f"[Checkpoint] Saved {len(df_chk)} rows to {OUTPUT_PATH}")

        time.sleep(random.uniform(*REQUEST_DELAY))

    df_out = pd.DataFrame(out).drop_duplicates(subset = ["imo"], keep = "last")
    df_out.to_csv(OUTPUT_PATH, index=False)
    print(f"Done. Saved {len(df_out)} rows to {OUTPUT_PATH}")
    return df_out


# Main

if __name__ == "__main__":
    print("Loading MRV file...")
    mrv = load_mrv_raw(MRV_PATH)

    imo_col = next(c for c in mrv.columns if "IMO" in c and "Number" in c)
    imo_numbers = mrv[imo_col].dropna().astype(int).unique().tolist()

    print(f"Found {len(imo_numbers)} IMO numbers")
    print("First 10 IMOs:", imo_numbers[:10])

    print("Starting Datalastic vessel_info lookups...")
    scrape_built_years_api(imo_numbers)
