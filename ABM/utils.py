import numpy as np

# Fuel price
def update_fuel_price(price, growth):
    return price * (1 + growth)

# ENPV
def compute_enpv(
    remaining_life,
    fuel_use_monthly,
    fuel_price,
    fuel_price_growth, 
    saving_ratio,
    capex,
    opex_monthly,
    discount_rate,
):
    r = discount_rate / 12
    npv = -capex

    for t in range(1, remaining_life + 1):
        
        price_t = fuel_price * ((1 + fuel_price_growth) ** t)

        savings_t = fuel_use_monthly * saving_ratio * price_t

        npv += (savings_t - opex_monthly) / ((1 + r) ** t)

    return npv
