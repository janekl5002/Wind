# Wind Propulsion Data Analysis

Group project for analyzing wind propulsion technology in shipping.

## Project Structure

```
├── data/                 # Data storage
│   ├── raw/             # Raw data
│   ├── processed/       # Processed data
│   └── external/        # External datasets
├── analysis/            # Analysis scripts
├── notebooks/           # Jupyter notebooks
├── visualization/       # Charts and maps
├── docs/               # Documentation
└── requirements.txt     # Python dependencies
```

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
cp env.example .env
# Edit .env with your API keys
```

## Usage

Run analysis:
```bash
python scripts/main.py
```

## Team Members

- David, Greta, Janek, Lolo, Nicolas, Uli

## Data Sources

- IWSA vessel database
- AIS tracking data
- Weather APIs
- News monitoring
- Econowind PLC data
