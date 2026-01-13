import pypsa
import numpy as np
import pandas as pd
from tz_pypsa.cost_model import calculate_annuity 

def PrepareNetworkForCFE(
        network: pypsa.Network, 
        buses_with_ci_load: list,
        ci_load_fraction: float | str,
        h2_load_fraction: float | str, 
        technology_palette: list,
        p_nom_extendable: bool,
    ) -> pypsa.Network:

    """
    Prepares a PyPSA network for 24/7 carbon-free energy (CFE) modelling. It does so by creating a sub-system for a 
    Commercial & Industrial (C&I) asset/system on a defined set of buses in the network. This function modifies the 
    given PyPSA network by adding new buses, loads, links, generators, and storage units to represent the C&I system 
    and its interactions with the local grid.

    Parameters:
    -----------
    network : pypsa.Network
        The PyPSA network to be prepared (e.g., Brownfield Network).
    buses_with_ci_load : list
        List of buses on which to model a C&I system/asset.
    ci_load_fraction : float or str
        If float, a fraction of the original load to be assigned to the C&I load.
        If string 'custom', the user must define custom load profiles for each C&I load separately.
    h2_load_fraction : float or str
        If float, a fraction of the original C&I load to be assigned to the C&I hydrogen load.
        If string 'custom', the user must define custom load profiles for each C&I hydrogen load separately.
    technology_palette : list
        List of technologies (generators and storages) to add to the C&I system.
    p_nom_extendable : bool
        Flag indicating whether the nominal power of links and generators can be extended.

    Returns:
    -----------
    pypsa.Network
        The modified PyPSA network with the C&I system integrated.

    Raises:
    -----------
    ValueError
        If an invalid technology is provided in the technology_palette.

    Notes:
    -----------
    - The function adds jitter to the coordinates of new buses to avoid overlap.
    - Small capital and marginal costs are added to links to prevent model infeasibilities.
    - The function ensures that the C&I load is subtracted from the overall load to prevent double-counting.

    """
    
    # STEP 1:
    # Loop through each bus on which we want to model a C&I system/asset. 
    # The logic here is to abstract the C&I system as a separate entity.
    # This is done by adding a new bus, load, and storage unit to the network.
    # If there is C&I hydrogen demand, this is added as a new H2 bus, connected to the C&I bus via a link.

    # TODO: correct the location jitter

    for bus in buses_with_ci_load:

        # define names
        ci_bus_name = f'{bus} C&I Grid'
        ci_bus_name_h2 = f'{bus} C&I H2 Grid'
        ci_load_name = f'{bus} C&I Load'
        ci_load_name_h2 = f'{bus} C&I H2 Load'
        ci_storage_bus_name = f'{bus} C&I Storage'
        ci_storage_bus_name_h2 = f'{bus} C&I H2 Storage'

        # add a bus for the C&I system
        network.add(
            'Bus',
            ci_bus_name,
            x = network.buses.x.loc[bus] + 1, # add jitter
            y = network.buses.y.loc[bus] + 1, # add jitter
        )

        # add another bus to connect C&I bus with energy storage
        network.add(
            'Bus',
            ci_storage_bus_name,
            x = network.buses.x.loc[bus] + 2, # add jitter
            y = network.buses.y.loc[bus] + 1, # add jitter
        )

        # add another H2 bus 
        network.add(
            'Bus',
            ci_bus_name_h2,
            x = network.buses.x.loc[bus] + 1, # add jitter
            y = network.buses.y.loc[bus] + 2, # add jitter
        )

        # add C&I load
        if isinstance(ci_load_fraction, float):
            network.add(
                "Load",
                ci_load_name,
                bus = ci_bus_name,
                p_set = network.loads_t.p_set[bus] * ci_load_fraction,
            )
            # now subtract the C&I load from the overall load to prevent double-counting
            network.loads_t.p_set[bus] = network.loads_t.p_set[bus] - network.loads_t.p_set[ci_load_name]
        elif isinstance(ci_load_fraction, str):
            # retrieve custom load profile from string supplied, which should be the path
            custom_load_profile = pd.read_csv(ci_load_fraction, index_col=0, parse_dates=True).iloc[:, 0]
            network.add(
                "Load",
                ci_load_name,
                bus = ci_bus_name,
                p_set = custom_load_profile,
            )
            # now subtract the C&I load from the overall load to prevent double-counting
            network.loads_t.p_set[bus] = network.loads_t.p_set[bus] - network.loads_t.p_set[ci_load_name]
        else:
            # return error
            raise ValueError("Invalid data supplied for ci_load_fraction. Must be float or path to csv.")
        
        # add C&I H2 load
        # TODO: allow user-defined load, similar to above
        network.add(
            "Load",
            ci_load_name_h2,
            carrier = 'hydrogen',
            bus = ci_bus_name_h2,
            # p_set = 100
            p_set = network.loads_t.p_set[bus] * h2_load_fraction
        )
        # note no need to subtract load - this is additional load due to electrification

        # add C&I H2 storage bus
        network.add(
            'Bus',
            ci_storage_bus_name_h2,
            x = network.buses.x.loc[bus] + 2, # add jitter
            y = network.buses.y.loc[bus] + 2, # add jitter
        )

        # STEP 2:
        # Add virtual links between buses to represent flows of electricity.
        # Specifically, we add the following:
        #   - LocalGrid <-> C&I system
        #   - C&I system <-> C&I storage
        #   - C&I system -> C&I H2 system
        #   - C&I H2 system <-> C&I H2 storage

        # LocalGrid <-> C&I system
        network.add(
            "Link",
            f"{bus} C&I Grid Imports",
            bus0=bus, 
            bus1=ci_bus_name, 
            p_nom=0,
            p_nom_extendable=True, # keep this as True to prevent infeasibilities
            # add small capital and marginal costs to prevent model infeasibilities
            marginal_cost=0.01, 
            capital_cost=10, # don't make too low to prevent overbuilding
        )

        network.add(
            "Link",
            f"{bus} C&I Grid Exports",
            bus0=ci_bus_name, 
            bus1=bus,
            p_nom=0,
            p_nom_extendable=p_nom_extendable,
            # add small capital and marginal costs to prevent model infeasibilities
            marginal_cost=0.01, 
            capital_cost=10, # don't make too low to prevent overbuilding
        )

        # C&I system <-> C&I storage
        network.add(
            "Link",
            f"{bus} C&I Storage Charge",
            bus0=ci_bus_name, 
            bus1=ci_storage_bus_name, 
            p_nom=0,
            p_nom_extendable=p_nom_extendable,
            # add small capital and marginal costs to prevent model infeasibilities
            marginal_cost=0.01, 
            capital_cost=10, # don't make too low to prevent overbuilding
        )

        network.add(
            "Link",
            f"{bus} C&I Storage Discharge",
            bus0=ci_storage_bus_name, 
            bus1=ci_bus_name, 
            p_nom=0,
            p_nom_extendable=p_nom_extendable,
            # add small capital and marginal costs to prevent model infeasibilities
            marginal_cost=0.01, 
            capital_cost=10, # don't make too low to prevent overbuilding
        )

        network.add(
            # Hydrogen carrier kept in MWh units, not tonnes
            "Link",
            f"{bus} C&I H2 Electrolyser",
            bus0=ci_bus_name,
            bus1=ci_bus_name_h2,
            carrier = 'Electrolysis',
            # TODO: set realistic electrolyser parameters
            efficiency = 0.7,  # typical electrolyser efficiency (70%)
            p_nom=0,
            p_nom_extendable=True,
            p_nom_max = 10000, # to update, set as 10MW link for now
            # TODO: add realistic capital and marginal costs for electrolyser
            marginal_cost=50,  # USD/MWh, typical electricity cost for H2 production
            capital_cost= (calculate_annuity(0.1,30) * 1069200) + 53460,  
            # overnight capex - https://docs.nrel.gov/docs/fy25osti/92558.pdf
            # opex - https://docs.nrel.gov/docs/fy24osti/87625.pdf
        )

        network.add(
            # this represents the compressor from electrolyser to H2 storage
            "Link",
            f"{bus} C&I H2 Storage Charge",
            bus0=ci_bus_name_h2, 
            bus1=ci_storage_bus_name_h2,
            # bus2=ci_bus_name,
            efficiency1 = 0.99,
            # efficiency2 = -0.07, # represents energy required for compression 
            p_nom=0,
            p_nom_extendable=p_nom_extendable,
            # add small capital and marginal costs to prevent model infeasibilities
            capital_cost=calculate_annuity(0.1,30) * 0.04e6, # WACC of 10%, 30 year lifetime, 40 k€/MW CAPEX
            marginal_cost=0.01,  # placeholder costs
        )

        network.add(
            # decompression and regulation from pressurised storage
            # back to low pressure for use in DRI
            "Link",
            f"{bus} C&I H2 Storage Discharge",
            bus0=ci_storage_bus_name_h2, 
            bus1=ci_bus_name_h2, 
            efficiency = 0.99,
            p_nom=0,
            p_nom_extendable=p_nom_extendable,
            # add small capital and marginal costs to prevent model infeasibilities
            marginal_cost=0.01, 
            capital_cost=10, # placeholder costs
        )

        # STEP 3:
        # Add generators and storages to C&I bus within the technology palette. 
        # This represents the technologies procured in the C&I's PPA.

        for technology in technology_palette:

            # check if technology is generator or storage
            if technology in network.generators.type.unique():
                
                # get params from existing technologies
                params = (
                    network
                    .generators
                    .loc[ 
                        ((network.generators["type"] == technology) & (network.generators["bus"] == bus) & (network.generators["p_nom_extendable"] == True))
                    ]
                    .groupby(by='type')
                    .first()
                    .melt()
                    .set_index('variable')
                    ['value']
                    .to_dict()
                )

                # get capacity factors if technology is renewable, ensuring correct technology and bus is used
                generator_names = network.generators.index[
                    ((network.generators["type"] == technology) & (network.generators["bus"] == bus) 
                     & (network.generators["p_nom_extendable"] == True))
                ]

                for generator in generator_names:
                    if (network.generators.loc[generator].is_blend_or_ccs is True or
                    generator not in network.generators_t.p_max_pu.columns):
                        cf_int = np.ones((8760,1))
                        cf = pd.DataFrame(cf_int)
                    else:
                        cf = network.generators_t.p_max_pu[generator_names]

                if cf.empty:
                    cf = params['p_max_pu']
                else:
                    cf = cf.iloc[:,0].values

                for generator in generator_names:
                    
                    if network.carriers.loc[network.generators.carrier[generator]].co2_emissions <= 0:
                    # add generator
                        network.add(
                            'Generator', # PyPSA component
                            ci_bus_name + '-' + technology + '-ext-' + str(params['build_year']) + '-' + 'PPA' + '-' + 'Clean', # generator name
                            type = technology, # technology type (e.g., solar, gas-ccgt etc.)
                            bus = ci_bus_name, # region/bus/balancing zone
                            # ---
                            # unique technology parameters by bus
                            p_nom = 0, # starting capacity (MW)
                            p_nom_min = 0, # minimum capacity (MW)
                            #p_nom_max = params['p_nom_max'], # set this to constrain capacity build out, e.g. to a technical potential
                            p_max_pu = cf, # capacity factor
                            p_min_pu = params['p_min_pu'], # minimum capacity factor
                            efficiency = params['efficiency'], # efficiency
                            ramp_limit_up = params['ramp_limit_up'], # per unit
                            ramp_limit_down = params['ramp_limit_down'], # per unit
                            # ---
                            # universal technology parameters
                            p_nom_extendable = p_nom_extendable, # can the model build more?
                            capital_cost = params['capital_cost'], # currency/MW
                            marginal_cost = network.generators.loc[generator].marginal_cost, # currency/MWh
                            carrier = network.generators.loc[generator].carrier, # commodity/carrier
                            build_year = params['build_year'], # year available from
                            lifetime = params['lifetime'], # years
                            start_up_cost = params['start_up_cost'], # currency/MW
                            shut_down_cost = params['shut_down_cost'], # currency/MW
                            committable = params['committable'], # UNIT COMMITMENT
                            ramp_limit_start_up = params['ramp_limit_start_up'], # 
                            ramp_limit_shut_down = params['ramp_limit_shut_down'], # 
                            min_up_time = params['min_up_time'], # 
                            min_down_time = params['min_down_time'],
                            is_blend_or_ccs = params['is_blend_or_ccs'],
                            generation_blend_share = network.generators.loc[generator].generation_blend_share, #
                            min_utilisation_rate = params['min_utilisation_rate'], 
                            max_utilisation_rate = params['max_utilisation_rate']  
                        )
                    
                    else:

                        network.add(
                            'Generator', # PyPSA component
                            ci_bus_name + '-' + technology + '-ext-' + str(params['build_year']) + '-' + 'PPA' + '-' + 'Fossil', # generator name
                            type = technology, # technology type (e.g., solar, gas-ccgt etc.)
                            bus = ci_bus_name, # region/bus/balancing zone
                            # ---
                            # unique technology parameters by bus
                            p_nom = 0, # starting capacity (MW)
                            p_nom_min = 0, # minimum capacity (MW)
                            #p_nom_max = params['p_nom_max'], # set this to constrain capacity build out, e.g. to a technical potential
                            p_max_pu = cf, # capacity factor
                            p_min_pu = params['p_min_pu'], # minimum capacity factor
                            efficiency = params['efficiency'], # efficiency
                            ramp_limit_up = params['ramp_limit_up'], # per unit
                            ramp_limit_down = params['ramp_limit_down'], # per unit
                            # ---
                            # universal technology parameters
                            p_nom_extendable = p_nom_extendable, # can the model build more?
                            capital_cost = params['capital_cost'], # currency/MW
                            marginal_cost = network.generators.loc[generator].marginal_cost, # currency/MWh
                            carrier = network.generators.loc[generator].carrier, # commodity/carrier
                            build_year = params['build_year'], # year available from
                            lifetime = params['lifetime'], # years
                            start_up_cost = params['start_up_cost'], # currency/MW
                            shut_down_cost = params['shut_down_cost'], # currency/MW
                            committable = params['committable'], # UNIT COMMITMENT
                            ramp_limit_start_up = params['ramp_limit_start_up'], # 
                            ramp_limit_shut_down = params['ramp_limit_shut_down'], # 
                            min_up_time = params['min_up_time'], # 
                            min_down_time = params['min_down_time'], # 
                            is_blend_or_ccs = params['is_blend_or_ccs'],
                            generation_blend_share = network.generators.loc[generator].generation_blend_share,
                            min_utilisation_rate = params['min_utilisation_rate'], 
                            max_utilisation_rate = params['max_utilisation_rate']  #                             
                        )
                
            elif technology in network.storage_units.carrier.unique():
                
                # get params
                params = (
                    network
                    .storage_units
                    .loc[ 
                        ((network.storage_units["carrier"] == technology)
                        & (network.storage_units["bus"] == bus)
                        & (network.storage_units["p_nom_extendable"] == True))
                    ]
                    .groupby(by='type')
                    .first()
                    .melt()
                    .set_index('variable')
                    ['value']
                    .to_dict()
                )

                network.add(
                    "StorageUnit",
                    ci_bus_name + '-' + params['carrier'],
                    bus = ci_storage_bus_name,
                    p_nom_extendable = p_nom_extendable,
                    cyclic_state_of_charge=True,
                    max_hours=params['max_hours'],
                    build_year=params['build_year'],
                    carrier=params['carrier'],
                    capital_cost=params['capital_cost'],
                    efficiency_store=params['efficiency_store'],
                    efficiency_dispatch=params['efficiency_dispatch'],
                    standing_loss=params['standing_loss'],
                    lifetime=params['lifetime']
                )
                
                '''

                TODO!
                
                Hydrogen storages need to be modelled with fundamental stores (i.e., PyPSA Store components)
                
                This is described in the links below:
                    - https://fneum.github.io/data-science-for-esm/09-workshop-pypsa.html
                    - https://groups.google.com/g/pypsa/c/Owf6_6aHhRM
                    - https://pypsa.readthedocs.io/en/stable/examples/replace-generator-storage-units-with-store.html
                
                '''

            else:
                raise ValueError(f"Invalid technology: {technology}")
        
        # Add hydrogen storage unit as H2 steel tank
        network.add(
            # TODO: set realistic hydrogen storage parameters
            # TODO: annualise costs
            "Store",
            ci_storage_bus_name_h2 + '-H2 Storage',
            bus = ci_storage_bus_name_h2,
            carrier = 'hydrogen',
            e_nom = 0,
            # e_nom_extendable = True,
            e_cyclic = True,
            capital_cost = calculate_annuity(0.1,30) * 0.019e6, # DEA 0.019 M€/MWh, USD to EUR was about 1 in 2022.
            standing_loss = 0.0001, # per unit per hour
        )
    return network


def apply_cfe_constraint(
        n : pypsa.Network, 
        GridCFE : list, 
        ci_buses : list, 
        ci_identifier : str, 
        CFE_Score : float,
        max_excess_export : float,
    ) -> pypsa.Network:
    '''Set CFE constraint
    '''
    for bus in ci_buses:
        # ---
        # fetch necessary variables to implement CFE

        CI_Demand = (
            n.loads_t.p_set
            .filter(regex=bus)
            .filter(regex=ci_identifier)
            .filter(regex=r'^(?!.*H2).*', axis=1) # exclude H2 loads
            .values.flatten()
        )

        CI_H2_Demand = (
            n.model.variables['Link-p'].sel(
                Link=[i for i in n.links.index if ci_identifier in i and 'Electrolyser' in i and bus in i]
            )
            .sum(dims='Link')
        )

        CI_StorageCharge = (
            n.model.variables['Link-p'].sel(
                Link=[i for i in n.links.index if ci_identifier in i and 'Charge' in i and bus in i and 'H2' not in i]
            )
            .sum(dims='Link')
        )

        CI_StorageDischarge = (
            n.model.variables['Link-p'].sel(
                Link=[i for i in n.links.index if ci_identifier in i and 'Discharge' in i and bus in i and 'H2' not in i]
            )
            .sum(dims='Link')
        )

        CI_GridExport = (
            n.model.variables['Link-p'].sel(
                Link=[i for i in n.links.index if ci_identifier in i and 'Export' in i and bus in i]
            )
            .sum(dims='Link')
        )

        CI_GridImport = (
            n.model.variables['Link-p'].sel(
                Link=[i for i in n.links.index if ci_identifier in i and 'Import' in i and bus in i]
            )
            .sum(dims='Link')
        )

        # need to ensure that "Fossil" is included in string of emitting generator for blending/CCS
        CI_PPA_Fossil = (

        ((n.model.variables['Generator-p'].sel(
            Generator=[i for i in n.generators.index if ci_identifier in i and 'PPA' in i and bus in i and 'Fossil' in i]
        )))
        .sum(dims='Generator')
        )
                
        CI_PPA_Clean = (
    
        ((n.model.variables['Generator-p'].sel(
            Generator=[i for i in n.generators.index if ci_identifier in i and 'PPA' in i and bus in i and 'Clean' in i]
        )))
        .sum(dims='Generator')
        )

        # Constraint 1: Hourly matching
        # ---------------------------------------------------------------

        n.model.add_constraints(
            CI_Demand == CI_PPA_Clean + CI_PPA_Fossil - CI_GridExport + CI_GridImport + CI_StorageDischarge - CI_StorageCharge - CI_H2_Demand,
            name=f"cfe-constraint-hourly-matching-{bus}",
        )

        # Constraint 2: CFE target - note the CI_PPA_Fossil is offset by the share of fossil production which must be exported (set by CFE score)
        # ---------------------------------------------------------------
        n.model.add_constraints(
            ( CI_PPA_Clean - (CI_GridExport - (CI_PPA_Fossil * CFE_Score) ) + (CI_GridImport * list(GridCFE) ) ).sum() >= ( (CI_StorageCharge - CI_StorageDischarge) + CI_Demand + CI_H2_Demand).sum() * CFE_Score,
            name=f"cfe-constraint-target-{bus}",
 
        )

        # Constraint 3: Excess
        # ---------------------------------------------------------------
        n.model.add_constraints(
            CI_GridExport.sum() <= sum(CI_Demand) * max_excess_export,
            name=f"cfe-constraint-excess-{bus}",
        )

        # Constraint 4: Battery can only be charged/used by clean PPA (not grid)
        # ---------------------------------------------------------------
        n.model.add_constraints(
            CI_PPA_Clean >= CI_StorageCharge,
            name=f"cfe-constraint-storage-{bus}",
        )

        # Constraint 5: Force fossil fuel production (from blended or CCS) to be exported
        # ---------------------------------------------------------------
        n.model.add_constraints(
            CI_GridExport >= CI_PPA_Fossil * CFE_Score,
            name=f"cfe-constraint-fossil-excess-{bus}",
        )
    
    return n