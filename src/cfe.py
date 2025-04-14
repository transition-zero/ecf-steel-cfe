import pypsa

def PrepareNetworkForCFE(
        network: pypsa.Network, 
        buses_with_ci_load: list,
        ci_load_fraction: float,
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
    ci_load_fraction : float
        Fraction of the original load to be assigned to the C&I load.
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

    for bus in buses_with_ci_load:

        # define names
        ci_bus_name = f'{bus} C&I Grid'
        ci_load_name = f'{bus} C&I Load'
        ci_storage_bus_name = f'{bus} C&I Storage'

        # add a bus for the C&I system
        network.add(
            'Bus',
            ci_bus_name,
            x = network.buses.x.iloc[0] + 1, # add jitter
            y = network.buses.y.iloc[0] + 1, # add jitter
        )

        # add another bus to connect C&I bus with energy storage
        network.add(
            'Bus',
            ci_storage_bus_name,
            x = network.buses.x.iloc[0] - 1, # add jitter
            y = network.buses.y.iloc[0] - 1, # add jitter
        )

        # add C&I load
        network.add(
            "Load",
            ci_load_name,
            bus = ci_bus_name,
            p_set = network.loads_t.p_set[bus] * ci_load_fraction,
        )

        # now subtract the C&I load from the overall load to prevent double-counting
        network.loads_t.p_set[bus] = network.loads_t.p_set[bus] - network.loads_t.p_set[ci_load_name]

        # STEP 2:
        # Add virtual links between buses to represent flows of electricity.
        # Specifically, we add the following:
        #   - LocalGrid <-> C&I system
        #   - C&I system <-> C&I storage

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
            capital_cost=0.01,
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
            capital_cost=0.01,
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
            capital_cost=0.01,
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
            capital_cost=0.01,
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
                        network.generators.type == technology
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
                    (network.generators["type"] == technology) & (network.generators["bus"] == bus)
                ]
                cf = network.generators_t.p_max_pu[generator_names]
                if cf.empty:
                    cf = params['p_max_pu']
                else:
                    cf = cf.iloc[:,0].values

                # add generator
                network.add(
                    'Generator', # PyPSA component
                    ci_bus_name + '-' + technology + '-ext-' + str(params['build_year']) + '-' + 'PPA', # generator name
                    type = technology, # technology type (e.g., solar, gas-ccgt etc.)
                    bus = ci_bus_name, # region/bus/balancing zone
                    # ---
                    # unique technology parameters by bus
                    p_nom = 0, # starting capacity (MW)
                    p_nom_min = 0, # minimum capacity (MW)
                    p_max_pu = cf, # capacity factor
                    p_min_pu = params['p_min_pu'], # minimum capacity factor
                    efficiency = params['efficiency'], # efficiency
                    ramp_limit_up = params['ramp_limit_up'], # per unit
                    ramp_limit_down = params['ramp_limit_down'], # per unit
                    # ---
                    # universal technology parameters
                    p_nom_extendable = p_nom_extendable, # can the model build more?
                    capital_cost = params['capital_cost'], # currency/MW
                    marginal_cost = params['marginal_cost'], # currency/MWh
                    carrier = params['carrier'], # commodity/carrier
                    build_year = params['build_year'], # year available from
                    lifetime = params['lifetime'], # years
                    start_up_cost = params['start_up_cost'], # currency/MW
                    shut_down_cost = params['shut_down_cost'], # currency/MW
                    committable = params['committable'], # UNIT COMMITMENT
                    ramp_limit_start_up = params['ramp_limit_start_up'], # 
                    ramp_limit_shut_down = params['ramp_limit_shut_down'], # 
                    min_up_time = params['min_up_time'], # 
                    min_down_time = params['min_down_time'], # 
                )
                
            elif technology in network.storage_units.carrier.unique():
                
                # get params
                params = (
                    network
                    .storage_units
                    .loc[ 
                        network.storage_units.carrier == technology
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
                )
                
                '''

                TODO!
                
                Hydrogen storages need to be modelled with fundamental stores (i.e., PyPSA Store components)
                
                This is described in the links below:
                    - https://fneum.github.io/data-science-for-esm/09-workshop-pypsa.html
                    - https://groups.google.com/g/pypsa/c/Owf6_6aHhRM
                    - https://pypsa.readthedocs.io/en/stable/examples/replace-generator-storage-units-with-store.html
                
                '''

                # network.add(
                #     "StorageUnit",
                #     "hydrogen storage underground",
                #     bus = ci_storage_bus_name,
                #     carrier="hydrogen storage underground",
                #     max_hours=168,
                #     capital_cost=1e12,
                #     efficiency_store=0.44,
                #     efficiency_dispatch=0.44,
                #     p_nom_extendable=True,
                #     cyclic_state_of_charge=True,
                # )

            else:
                raise ValueError(f"Invalid technology: {technology}")
            
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
            n.loads_t.p_set.filter(regex=bus).filter(regex=ci_identifier).values.flatten()
        )

        CI_StorageCharge = (
            n.model.variables['Link-p'].sel(
                Link=[i for i in n.links.index if ci_identifier in i and 'Charge' in i and bus in i]
            )
            .sum(dims='Link')
        )

        CI_StorageDischarge = (
            n.model.variables['Link-p'].sel(
                Link=[i for i in n.links.index if ci_identifier in i and 'Discharge' in i and bus in i]
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

        CI_PPA = (
            n.model.variables['Generator-p'].sel(
                Generator=[i for i in n.generators.index if ci_identifier in i and 'PPA' in i and bus in i]
            )
            .sum(dims='Generator')
        )

        # Constraint 1: Hourly matching
        # ---------------------------------------------------------------

        n.model.add_constraints(
            CI_Demand == CI_PPA - CI_GridExport + CI_GridImport + CI_StorageDischarge - CI_StorageCharge
        )
        
        # Constraint 2: CFE target
        # ---------------------------------------------------------------
        n.model.add_constraints(
            ( CI_PPA - CI_GridExport + (CI_GridImport * list(GridCFE) ) ).sum() >= ( (CI_StorageCharge - CI_StorageDischarge) + CI_Demand ).sum() * CFE_Score, 
        )

        # Constraint 3: Excess
        # ---------------------------------------------------------------
        n.model.add_constraints(
            CI_GridExport.sum() <= sum(CI_Demand) * max_excess_export,
        )

        # Constraint 4: Battery can only be charged by clean PPA (not grid)
        # ---------------------------------------------------------------
        n.model.add_constraints(
            CI_PPA >= CI_StorageCharge,
        )

    return n