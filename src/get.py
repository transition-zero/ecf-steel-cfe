import os
import pypsa
import pandas as pd

def get_cfe_score_ts(n, run, ci_identifier='C&I'):
    '''Calculate the CFE score and return it as a time series
    '''
    GridCFE = GetGridCFE(n, ci_identifier=ci_identifier, run=run)
    CI_Demand = n.loads_t.p.filter(regex=ci_identifier).sum(axis=1)
    CI_PPA_Clean = n.generators_t.p.filter(regex=ci_identifier).sum(axis=1)
    CI_PPA_Fossil = n.generators_t.p.filter(regex=ci_identifier).sum(axis=1)
    CI_GridExport = n.links_t.p0.filter(regex='Exports').sum(axis=1)
    CI_GridImport = n.links_t.p0.filter(regex='Imports').sum(axis=1)
    CI_StorageDischarge = n.links_t.p0.filter(regex='Discharge').sum(axis=1)
    CI_StorageCharge = n.links_t.p0.filter(regex='Charge').sum(axis=1)
    return (( CI_PPA_Clean + CI_PPA_Fossil - CI_GridExport + (CI_GridImport * list(GridCFE) ) - CI_StorageCharge + CI_StorageDischarge ) / CI_Demand).to_frame(name='CFE Score')


def get_ci_cost_summary(n : pypsa.Network) -> pd.DataFrame:
    '''Returns a summary of the costs for C&I generators, storage units and links
    '''
    ci_generator_costs = (
        n.generators.loc[
            n.generators.index.str.contains('C&I')
        ]
        [['carrier','p_nom','p_nom_opt','capital_cost','marginal_cost', 'p_max_pu']]
        #.reset_index()
    )

    ci_generator_p_max_pu = (
        n.generators_t.p_max_pu.transpose().loc[
            n.generators_t.p_max_pu.transpose().index.str.contains('C&I')
        ]
        .transpose()
        # [['p_max_pu']]
        #.reset_index()
    )

    ci_generator_costs['dispatch'] = n.generators_t.p[ ci_generator_costs.index ].sum()
    # Calculate potential dispatch accounting for both time-varying and static p_max_pu
    potential_dispatch = []
    for gen_id in ci_generator_costs.index:
        if gen_id in ci_generator_p_max_pu.columns:
            # Time-varying p_max_pu
            potential = (ci_generator_costs.loc[gen_id, 'p_nom_opt'] * ci_generator_p_max_pu[gen_id]).sum()
        else:
            # Static p_max_pu
            potential = (ci_generator_costs.loc[gen_id, 'p_nom_opt'] * ci_generator_costs.loc[gen_id, 'p_max_pu'] * len(ci_generator_p_max_pu))
        potential_dispatch.append(potential)
    
    ci_generator_costs['potential_dispatch'] = potential_dispatch
    ci_generator_costs['curtailment'] = ci_generator_costs['potential_dispatch'] - ci_generator_costs['dispatch']
    ci_generator_costs['curtailment_perc'] = ci_generator_costs['curtailment']/ci_generator_costs['potential_dispatch']

    # storage
    ci_storage_costs = (
        n.storage_units.loc[
            n.storage_units.index.str.contains('C&I')
        ]
        [['carrier','p_nom','p_nom_opt','capital_cost','marginal_cost']]
        #.reset_index()
    )

    ci_storage_costs['dispatch'] = n.storage_units_t.p_dispatch[ ci_storage_costs.index ].sum()

    # links
    ci_links_costs = (
        n.links.loc[
            n.links.index.str.contains('C&I')
        ]
        [['carrier','p_nom','p_nom_opt','capital_cost','marginal_cost']]
        #.reset_index()
    )

    # zero link costs because they are virtual
    ci_links_costs['capital_cost'] = 0
    ci_links_costs['marginal_cost'] = 0

    ci_links_costs['dispatch'] = n.links_t.p0[ ci_links_costs.index ].sum()

    df = pd.concat([ci_generator_costs, ci_storage_costs, ci_links_costs]).round(3)

    df.loc[:, 'capex'] = df['p_nom_opt'] * df['capital_cost']
    df.loc[:, 'opex'] = df['dispatch'] * df['marginal_cost']

    # marginal price of the brownfield bus
    ci_brown_bus = n.buses[n.buses.index.str.contains('C&I')].index.str.split('C&I').str[0].str.strip()[0]

    # calculate import costs
    import_links_t = n.links_t.p0.filter(regex='C&I').filter(regex='Import').sum(axis=1)
    import_link_p = n.buses_t.marginal_price[ci_brown_bus]
    import_cost = ( import_links_t * import_link_p ).sum() 

    # append to df
    df.loc[ df.index.str.contains('Import'), 'import_cost' ] = import_cost

    # calculate export revenues
    export_links_t = n.links_t.p0.filter(regex='C&I').filter(regex='Export').sum(axis=1)
    export_link_p = n.buses_t.marginal_price.filter(regex='^(?!.*C&I)').mean(axis=1)
    export_revenue = -( export_links_t * export_link_p ).sum().sum()

    # append to df
    df.loc[ df.index.str.contains('Export'), 'export_revenue' ] = export_revenue

    # fillna
    df.fillna(0, inplace=True)

    df.loc[:, 'unit_cost'] = (df['capex'] + df['opex'] + df['import_cost'] + df['export_revenue']) / df['dispatch']

    return df


def GetGridCFE(
    n: pypsa.Network,   
    ci_identifier: str,
    run: dict
):
    """

    Calculate the CFE score of a grid, intra- and inter-regionally. Here, we follow the mathematical
    expressions presented by Xu and Jenkins (2021): https://acee.princeton.edu/24-7/

    Parameters:
    -----------
    network : pypsa.Network
        The optimised network for which we are calculating the GridCFE.
    bus : str
        The country bus for which we are calculating the GridCFE.
    ci_identifier : str
        The unique identifer used to identify C&I assets.

    Returns:
    -----------
    CFE Score: list
        Hourly resolution CFE scores for each snapshot in the network.

    Let:
    -----------
    R = Intra-regional grid
    Z = Inter-regional grid

    """

    

        # get global clean carriers
    global_clean_carriers = [
        i
        for i in n.carriers.query(" co2_emissions <= 0").index.tolist()
        if i in n.generators.carrier.tolist()
    ]

    for bus in run["nodes_with_ci_load"]:
        # get clean generators in R
        R_clean_generators = n.generators.loc[
            # clean carriers
            (n.generators.carrier.isin(global_clean_carriers))
            &
            #exclude assets not in R
            (n.generators.index.str.contains(bus)) &
            # exclude C&I assets
            (~n.generators.index.str.contains(ci_identifier))
        ].index

        # get all generators
        R_all_generators = n.generators.loc[
            (~n.generators.index.str.contains(ci_identifier))
            &
            (n.generators.index.str.contains(bus)) 
        ].index

        # calculate CFE sceore
        total_clean_generation = n.generators_t.p[R_clean_generators].sum(axis=1)
        total_generation = n.generators_t.p[R_all_generators].sum(axis=1)

    # return CFE score
    return (total_clean_generation / total_generation).round(2).tolist()


def load_from_dir(path) -> dict:
    '''Loads all networks in a directory into a dictionary
    '''
    networks = {}
    for f in os.listdir(path):
        if f.endswith('.nc'):
            if 'brownfield' in f:
                networks['n_bf'] = pypsa.Network(f'{path}/{f}')
            elif 'annual_matching' in f:
                name = f.split('_')[3].replace('.nc','')
                cfe = f.split('_')[2]
                networks[f'n_am_{cfe}_{name}'] = pypsa.Network(f'{path}/{f}')
            elif 'hourly_matching' in f:
                name = f.split('_')[3].replace('.nc','')
                cfe = f.split('_')[2]
                networks[f'n_hm_{cfe}_{name}'] = pypsa.Network(f'{path}/{f}')
    return networks


def get_emissions(n: pypsa.Network) -> float:
    '''Returns emissions in tonnes CO2-eq
    '''
    return (
        (
            n.generators_t.p 
            / n.generators.efficiency 
            * n.generators.carrier.map(n.carriers.co2_emissions)
        )
        .sum()
        .sum()
    )

def get_ci_parent_emissions(n: pypsa.Network, nodes_with_ci_loads) -> float:
    '''Returns hourly emissions in tonnes CO2-eq for the C&I bus
    '''
    ci_parent_generators = n.generators[n.generators.index.str.contains(nodes_with_ci_loads)]
    ci_parent_generators_t = n.generators_t.p[ci_parent_generators.index]
    ci_parent_load = 1/(n.loads_t.p.filter(regex=nodes_with_ci_loads).filter(regex='^(?!.*C&I)'))
    emissions = (
        (
            ci_parent_generators_t
            / ci_parent_generators.efficiency 
            * ci_parent_generators.carrier.map(n.carriers.co2_emissions)
        )
        .sum(axis=1)
    )
    emissions_intensity = emissions * ci_parent_load.squeeze()
    return emissions_intensity


def get_unit_cost(n : pypsa.Network) -> pd.DataFrame:
    '''Returns the unit cost in $/MWh for each component and carrier
    '''
    return (
        (
            n.statistics()['Capital Expenditure'] 
            + n.statistics()['Operational Expenditure']
        )
        .div(n.statistics()['Supply'])
        .round(2)
        .reset_index()
        .rename(columns={'level_0' : 'component','level_1' : 'carrier', 0: 'System Cost [$/MWh]'})
    )

def get_ci_generation(n : pypsa.Network) -> pd.DataFrame:
    '''Returns the generation in MWh for each CI bus
    '''

    # ci_buses = n.buses[n.buses.index.str.contains('C&I')].index.tolist()
    ci_generation = n.generators_t.p.filter(regex='C&I').sum().sum()
    ci_generation_df = pd.DataFrame({
        'name': [n.name],
        'ci_generation': [ci_generation]
    })
    return ci_generation_df

def get_total_ci_procurement_cost(n: pypsa.Network) -> pd.DataFrame:
    """
    Returns the total annual system cost in M$ for each C&I procured component and carrier,
    excluding Transmission rows.
    """
    stats = n.statistics(groupby=["bus", "carrier"])
    capex = stats['Capital Expenditure'].fillna(0)
    opex = stats['Operational Expenditure'].fillna(0)
    total_cost = (capex + opex).div(1e6).round(2).reset_index()
    filtered = (
        total_cost
        .query(
            "level_1.str.contains('C&I') "
            "and not level_2.str.contains('Transmission')"
        )
        .drop(columns=['level_1'])
        .rename(columns={'level_0': 'component', 'level_2': 'carrier', 0: 'annual_system_cost [M$]'})
    )
    return filtered if not filtered.empty else pd.DataFrame(columns=['component', 'carrier', 'annual_system_cost [M$]'])

def get_ci_lcoe(n : pypsa.Network) -> pd.DataFrame:
    '''Returns the levelised cost of electricity (LCOE) in $/MWh for each C&I procured generator and storage unit
    '''
    stats = n.statistics(groupby=["bus","carrier"])
    supply = stats['Supply'].fillna(0).reset_index()
    electricity_delivered = supply.query(
        "level_0.str.contains('Generator') and level_1.str.contains('C&I')"
    )['Supply'].sum()

    capex = stats['Capital Expenditure'].fillna(0).div(electricity_delivered)
    opex = stats['Operational Expenditure'].fillna(0).div(electricity_delivered)
    total_costs = (capex + opex).round(2).reset_index()
    total_costs = (
        total_costs
        .query(
            "level_1.str.contains('C&I') "
            "and not level_0.str.contains('Link') "
            "and not level_1.str.contains('H2') "
            "and not level_2.str.contains('Transmission')"
        )
        .drop(columns=['level_1'])
        .rename(columns={'level_0': 'component', 'level_2': 'carrier', 0: 'lcoe_usd_per_mwh'})
        .query("lcoe_usd_per_mwh > 0")
    )
    return total_costs

def get_total_annual_system_cost(n : pypsa.Network) -> pd.DataFrame:
    '''Returns the total annual system cost in M$ for each component and carrier
    '''
    return (
        (
            n.statistics()['Capital Expenditure'] 
            + n.statistics()['Operational Expenditure']
        )
        .div(1e6)
        .round(2)
        .reset_index()
        .rename(columns={'level_0' : 'component','level_1' : 'carrier', 0: 'annual_system_cost [M$]'})
    )


def get_ci_procurement(n, ci_identifier):
    '''Returns the fractional procurement of C&I assets
    '''
    ci_load = n.loads_t.p.filter(regex=ci_identifier).sum().sum()
    return pd.DataFrame({
        # imports
        'Grid supply' : (
            n.links_t.p0.filter(regex=ci_identifier).filter(regex='Import').sum().sum(),# / ci_load,
        ),
        # exports
        'Excess' : (
            n.links_t.p1.filter(regex=ci_identifier).filter(regex='Export').sum().sum(),# / ci_load,
        ),
        # ppa
        'C&I PPA' : (
            n.generators_t.p[
                n.generators.loc[
                    n.generators.index.str.contains(ci_identifier),
                    ].index
                ]
            .sum(axis=1)
            .sum()
            - n.links_t.p0.filter(regex=ci_identifier).filter(regex='Storage Charge').sum().sum()
            + n.links_t.p0.filter(regex=ci_identifier).filter(regex='Storage Discharge').sum().sum()
            #/ ci_load
        ),
    })


def split_scenario_col(df : pd.DataFrame, col_name: str):
    '''Splits the scenario column into two columns
    '''
    df.loc[ df[col_name].str.contains('n_bf'), 'Scenario' ] = 'Reference'
    df.loc[df[col_name].str.contains(r'RES\d+'), 'Scenario'] = (
        df.loc[df[col_name].str.contains(r'RES\d+'), col_name]
        .str.extract(r'RES(\d+)')[0]
        .astype(str) + '% RES'
    )
    df.loc[ df[col_name].str.contains('n_hm'), 'Scenario' ] = df.query(f"{col_name}.str.contains('CFE')")[col_name].str.split('_', expand=True)[2].str.replace('CFE','CFE-')
    df.loc[ df.Scenario.str.contains('CFE'), 'CFE Score'] = df.loc[ df.Scenario.str.contains('CFE'), 'Scenario'].str.replace('CFE-','').astype(int)
    return df


def get_ci_carriers(n: pypsa.Network) -> pd.DataFrame:
    '''Returns the C&I carriers
    '''
    ci_carriers = list(n.generators[n.generators.index.str.contains('C&I')].carrier.unique()) + \
              list(n.storage_units[n.storage_units.index.str.contains('C&I')].carrier.unique()) + \
              list(n.links[n.links.index.str.contains('H2')].carrier.unique())

    # Only add store carriers if there are any stores in the network
    if not n.stores.empty:
        h2_stores = n.stores[n.stores.index.str.contains('H2')]
        if not h2_stores.empty:
            ci_carriers += list(h2_stores.carrier.unique())

    # Filter out carriers that are not present in n.carriers.index to avoid KeyError
    valid_ci_carriers = pd.Index(ci_carriers).intersection(n.carriers.index)
    return n.carriers.loc[valid_ci_carriers, 'nice_name']


def calculate_lcoh(
    n: pypsa.Network,
    electrolyser: str = "C&I H2 Electrolyser",
    compressor: str = "C&I H2 Storage Charge",
    decompressor: str = "C&I H2 Storage Discharge",
    h2_store: str = "C&I H2 Storage-H2 Storage",
    h2_demand: str = "C&I H2 Load"
) -> dict:
    
    # 1. Annualised capex + opex
    # Find the actual names by substring match
    elec_link = [k for k in n.links.index if electrolyser in k][0]
    comp_link = [k for k in n.links.index if compressor in k][0]
    decomp_link = [k for k in n.links.index if decompressor in k][0]
    store_name = [k for k in n.stores.index if h2_store in k][0]

    capex_elec = n.links.at[elec_link, "p_nom_opt"] * n.links.at[elec_link, "capital_cost"]
    capex_comp = n.links.at[comp_link, "p_nom_opt"] * n.links.at[comp_link, "capital_cost"]
    capex_decomp = n.links.at[decomp_link, "p_nom_opt"] * n.links.at[decomp_link, "capital_cost"]
    capex_store = n.stores.at[store_name, "e_nom_opt"] * n.stores.at[store_name, "capital_cost"]

    total_capex = capex_elec + capex_comp + capex_decomp + capex_store

    # 2. Variable opex and marginal costs
    var_elec = (n.links_t.p0[elec_link]).sum() * n.links.at[elec_link, "marginal_cost"]
    var_comp = (n.links_t.p0[comp_link]).sum() * n.links.at[comp_link, "marginal_cost"]
    var_decomp = (n.links_t.p0[decomp_link]).sum() * n.links.at[decomp_link, "marginal_cost"]

    total_var_opex = var_elec + var_comp + var_decomp

    # 3. Electricity costs (using marginal price of the electricity bus)
    # Identify the electricity bus the electrolyser draws power from
    elec_bus = n.links.at[elec_link, "bus0"]

    # Electricity cost = sum(power_intake * marginal_price * snapshot_weighting)
    p_in_elec = n.links_t.p0[elec_link]
    elec_prices = n.buses_t.marginal_price[elec_bus].clip(lower=0)
    total_elec_cost = (p_in_elec * elec_prices).sum()

    # 4. Total Hydrogen demand
    # Find the actual H2 demand load by substring match
    h2_demand_col = [col for col in n.loads_t.p.columns if h2_demand in col][0]
    total_h2_consumed_mwh = (n.loads_t.p[h2_demand_col]).sum()
    total_h2_consumed_kg = total_h2_consumed_mwh * 1000 / 33.33

    # Calculate LCOH (USD / MWh_H2)
    total_system_cost = total_capex + total_var_opex + total_elec_cost
    lcoh_usd_mwh = total_system_cost / total_h2_consumed_mwh

    # Calculate component costs in USD / MWh_H2
    electrolyser_component = (capex_elec + var_elec)/ total_h2_consumed_kg
    comp_component = (capex_comp + var_comp + capex_decomp + var_decomp) / total_h2_consumed_kg
    store_component = capex_store / total_h2_consumed_kg
    electricity_component = total_elec_cost / total_h2_consumed_kg
    
    # Convert to USD / kg (Assuming LHV of H2 is ~33.33 kWh/kg = 0.03333 MWh/kg)
    lcoh_usd_kg = lcoh_usd_mwh * 0.03333

    return {
        "LCOH (USD/MWh)": lcoh_usd_mwh,
        "LCOH (USD/kg)": lcoh_usd_kg,
        "Electrolyser cost (USD/kg)": electrolyser_component,
        "Compressor cost (USD/kg)": comp_component,
        "Store cost (USD/kg)": store_component,
        "Electricity cost (USD/kg)": electricity_component,
        "Total H2 Consumed (MWh)": total_h2_consumed_mwh
    }