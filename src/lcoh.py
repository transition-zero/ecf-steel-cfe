import math

def calculate_lcoh(
    installed_power_kw: float = 100000.0,
    capex_usd_kw: float = 2310.0,
    energy_consumption_kwh_kg: float = 52.40,
    stack_durability_h: float = 80000.0,
    stack_degradation_pct_per_1000h: float = 0.12,
    stack_replacement_costs_pct_capex: float = 15.00,
    other_opex_pct_capex: float = 2.00,
    operating_hours_per_year: float = 4000.0,
    average_electricity_costs_usd_mwh: float = 41.53,
    grid_fees_usd_mwh: float = 39.70,
    electricity_taxes_usd_mwh: float = 30.30,
    capex_subsidy_usd_kw: float = 0.0,
    feed_in_tariff_usd_kg: float = 0.0,
    reduction_grid_taxes_usd_mwh: float = 0.0,
    oxygen_sale_price_usd_t: float = 0.0,
    economic_lifetime_years: float = 25.0,
    cost_of_capital_pct: float = 7.0
) -> dict:
    """
    Calculates the Levelised Cost of Hydrogen (LCOH) in USD/kg based on the
    European Hydrogen Observatory Methodology.
    https://observatory.clean-hydrogen.europa.eu/tools-reports/levelised-cost-hydrogen-calculator
    """
    
    # Equation 2: Calculation of stack replacements
    total_operating_hours = operating_hours_per_year * economic_lifetime_years
    stack_replacements = math.floor(total_operating_hours / stack_durability_h)
    
    # Equation 3: Calculation of average energy consumption per kg hydrogen (kWh/kg)
    ec = energy_consumption_kwh_kg
    sd = stack_degradation_pct_per_1000h / 100.0
    sdur = stack_durability_h
    sr = stack_replacements
    oh = operating_hours_per_year
    el = economic_lifetime_years
    
    term1 = (ec * (1 + (sd * sdur / 1000)) + ec) / 2
    term2 = (sr * sdur) / (oh * el)
    part1 = term1 * term2
    
    term3 = (ec * (1 + (sd * ((oh * el) - (sr * sdur)) / 1000)) + ec) / 2
    term4 = ((oh * el) - (sr * sdur)) / (oh * el)
    part2 = term3 * term4
    
    avg_energy_consumption_kwh_kg = part1 + part2
    
    # Equation 4: Calculation of electrolysis unit capacity (kg/h)
    capacity_kg_h = installed_power_kw / avg_energy_consumption_kwh_kg
    
    # Equation 5: Calculation of electrolysis hydrogen output (kg)
    annual_hydrogen_output_kg = operating_hours_per_year * capacity_kg_h
    total_hydrogen_output_kg = annual_hydrogen_output_kg * economic_lifetime_years
    
    # Equation 6: Calculation of the energy consumption (MWh)
    total_energy_consumption_mwh = (total_hydrogen_output_kg * avg_energy_consumption_kwh_kg) / 1000
    
    # Equation 7: Calculation of the electrolyser CAPEX (USD)
    electrolyser_capex_usd = installed_power_kw * capex_usd_kw
    
    # NPV of hydrogen output calculation to account for cost of capital (Discounted Annuity)
    r = cost_of_capital_pct / 100.0
    if r > 0:
        discount_factor = (1 - (1 + r)**(-el)) / r
        npv_hydrogen_output = annual_hydrogen_output_kg * discount_factor
    else:
        npv_hydrogen_output = total_hydrogen_output_kg
        
    # Equation 8: CAPEX costs per kilogram of hydrogen produced (USD/kg)
    capex_usd_kg = electrolyser_capex_usd / npv_hydrogen_output
    
    # Equation 9 & 10: Electricity costs per kilogram (USD/kg)
    cost_of_energy_usd = total_energy_consumption_mwh * average_electricity_costs_usd_mwh
    electricity_cost_usd_kg = cost_of_energy_usd / total_hydrogen_output_kg
    
    # Equation 11, 12 & 13: Other OPEX costs per kilogram (USD/kg)
    stack_replacement_costs_usd = (stack_replacement_costs_pct_capex / 100.0) * electrolyser_capex_usd * sr
    other_opex_usd = electrolyser_capex_usd * (other_opex_pct_capex / 100.0) * el
    other_opex_usd_kg = (other_opex_usd + stack_replacement_costs_usd) / total_hydrogen_output_kg
    
    # Equation 14 & 15: Grid fees per kilogram (USD/kg)
    grid_fees_usd = total_energy_consumption_mwh * grid_fees_usd_mwh
    grid_fees_usd_kg = grid_fees_usd / total_hydrogen_output_kg
    
    # Equation 16 & 17: Electricity taxes per kilogram (USD/kg)
    taxes_usd = total_energy_consumption_mwh * electricity_taxes_usd_mwh
    taxes_usd_kg = taxes_usd / total_hydrogen_output_kg
    
    # Equation 18 to 22: Subsidies per kilogram (USD/kg)
    subsidy_1 = capex_subsidy_usd_kw * installed_power_kw
    subsidy_2 = feed_in_tariff_usd_kg * total_hydrogen_output_kg
    subsidy_3 = reduction_grid_taxes_usd_mwh * total_energy_consumption_mwh
    subsidies_usd_kg = -1 * ((subsidy_1 / npv_hydrogen_output) + ((subsidy_2 + subsidy_3) / total_hydrogen_output_kg))
    
    # Equation 23, 24 & 25: Oxygen Revenues per kilogram (USD/kg)
    oxygen_output_kg = total_hydrogen_output_kg * 8
    oxygen_revenues_usd = oxygen_output_kg * (oxygen_sale_price_usd_t / 1000)
    oxygen_usd_kg = -1 * (oxygen_revenues_usd / total_hydrogen_output_kg)
    
    # Equation 1: Total Levelized Cost of Hydrogen (LCOH)
    total_lcoh_usd_kg = (capex_usd_kg + electricity_cost_usd_kg + other_opex_usd_kg + 
                         grid_fees_usd_kg + taxes_usd_kg + subsidies_usd_kg + oxygen_usd_kg)
    
    return {
        "Total LCOH (USD/kg)": total_lcoh_usd_kg,
        "Components (USD/kg)": {
            "CAPEX": capex_usd_kg,
            "Electricity": electricity_cost_usd_kg,
            "Other OPEX": other_opex_usd_kg,
            "Grid Fees": grid_fees_usd_kg,
            "Taxes": taxes_usd_kg,
            "Subsidies": subsidies_usd_kg,
            "Oxygen": oxygen_usd_kg
        }
    }

# Example Usage
if __name__ == "__main__":
    result = calculate_lcoh(
        installed_power_kw=2650,
        capex_usd_kw=84,
        average_electricity_costs_usd_mwh=10.7,
        grid_fees_usd_mwh=0,
        electricity_taxes_usd_mwh=0,
        cost_of_capital_pct=10
    )
    print(f"Total LCOH: {result['Total LCOH (USD/kg)']:.2f} USD/kg")
    print("Breakdown:")
    for component, value in result['Components (USD/kg)'].items():
        print(f"  {component}: {value:.2f} USD/kg")