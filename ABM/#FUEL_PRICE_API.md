# Fuel Price API Integration

The ABM model now integrates with the USDA AgTransport API to fetch real-time fuel prices and calculate monthly changes.

## Features

- **Current Fuel Prices**: Fetches the latest available fuel prices from USDA API
- **Monthly Change Calculation**: Calculates historical monthly growth rates from API data
- **Automatic Fallback**: Falls back to default values if API is unavailable
- **Multiple Fuel Types**: Supports VLSFO, Marine Gas Oil, and IFO 380cst

## Setup

1. **Set API Token** (optional but recommended):
   ```bash
   # In your .env file or environment variables
   USDA_APP_TOKEN=your_token_here
   ```

2. **Install Dependencies**:
   ```bash
   pip install requests python-dotenv pandas
   ```

## Usage

### Basic Usage (Automatic API Fetch)

```python
from model import WASPAdoptionModel
from data_loader import load_mrv_vessel_data

# Load vessel data
vessel_data = load_mrv_vessel_data("2024-v141-18122025-EU MRV Publication of information.xlsx")

# Create model - will automatically fetch fuel prices from API
model = WASPAdoptionModel(
    vessel_data,
    use_fuel_price_api=True  # Enable API integration (default: True)
)

# Run simulation
for _ in range(360):
    model.step()
```

### Manual Fuel Price Control

```python
# Use custom fuel prices (disables API)
model = WASPAdoptionModel(
    vessel_data,
    fuel_price_start=600.0,      # USD per metric tonne
    fuel_price_growth=0.003,      # 0.3% monthly growth
    use_fuel_price_api=False      # Disable API
)
```

### Partial API Usage

```python
# Fetch current price from API, but use custom growth rate
model = WASPAdoptionModel(
    vessel_data,
    fuel_price_start=None,        # Will fetch from API
    fuel_price_growth=0.005,      # Use custom growth rate
    use_fuel_price_api=True
)
```

## API Functions

### `get_fuel_price_with_fallback()`

Fetches current fuel price and monthly growth rate with fallback to defaults.

```python
from fuel_price_api import get_fuel_price_with_fallback

price, growth = get_fuel_price_with_fallback(
    default_price=500.0,
    default_growth=0.005
)
print(f"Fuel price: ${price:.2f}/tonne")
print(f"Monthly growth: {growth*100:.2f}%")
```

### `get_latest_fuel_price()`

Get only the latest fuel price.

```python
from fuel_price_api import get_latest_fuel_price

price = get_latest_fuel_price()
if price:
    print(f"Current price: ${price:.2f}/tonne")
```

### `calculate_monthly_change()`

Calculate only the monthly growth rate.

```python
from fuel_price_api import calculate_monthly_change

growth = calculate_monthly_change()
if growth:
    print(f"Monthly growth rate: {growth*100:.2f}%")
```

## Fuel Types

The API tries to fetch prices in this order:
1. **VLSFO** (Very Low Sulphur Fuel Oil - IMO 2020 Grade 0.5%) - Preferred
2. **Marine Gas Oil** - Fallback option 1
3. **IFO 380cst** - Fallback option 2

## Error Handling

If the API is unavailable or returns no data:
- The model will use default values (500 USD/tonne, 0.5% monthly growth)
- A warning message will be printed
- The simulation will continue normally

## Notes

- The API requires a USDA App Token (set via `USDA_APP_TOKEN` environment variable)
- Without a token, the API will return errors and defaults will be used
- Monthly growth rate is calculated from historical data (last 500 records)
- Fuel prices are updated monthly in the simulation using the growth rate
