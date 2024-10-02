import os
import yaml
import pypsa

import tz_pypsa as tza
from tz_pypsa.model import Model

from .helpers import *
from .constraints import *

def run_brownfield_scenario(
        run : dict = None,
        configs : dict = None
) -> pypsa.Network:

    '''Run a brownfield scenario without CFE considerations.
    '''
    
    # setup network
    print('loading model: ', run['stock_model'])

    network = (
        Model.load_model(
            run['stock_model'], 
            frequency = configs['global_vars']['frequency'],
            timesteps = configs['global_vars']['timesteps'],
            select_nodes=run['select_nodes'], 
            years=[ configs['global_vars']['year'] ],
            backstop=run['backstop'],
            set_global_constraints=configs['global_vars']['set_global_constraints'],
        )
    )

    # ensure p_nom is extendable
    network.generators['p_nom_extendable']      = True
    network.storage_units['p_nom_extendable']   = True
    network.links['p_nom_extendable']           = run['allow_grid_expansion']

    # set p_nom_min
    network.generators['p_nom_min']      = network.generators['p_nom']
    network.storage_units['p_nom_min']   = network.storage_units['p_nom']
    network.links['p_nom_min']           = network.links['p_nom']

    # ----------------------------------------------------------------------
    # Step 1: 
    # Separate C&I and non-C&I load
    # ----------------------------------------------------------------------

    for bus in run['nodes_with_ci_load']:
        # subtract out C&I load from bus
        network.loads_t.p_set[bus] *= (1 - run['ci_load_fraction'])

        # add C&I load to bus as a separate load
        ci_load = bus + '-' + configs['global_vars']['ci_label']
        network.add(
            "Load",
            ci_load,
            bus=bus,
            p_set=network.loads_t.p_set[bus] * run['ci_load_fraction'],
        )
    
    # ----------------------------------------------------------------------
    # Step 2: 
    # Create a bus for C&I PPA
    # ----------------------------------------------------------------------

    for bus in run['nodes_with_ci_load']:

        # add bus for C&I PPA
        ci_bus = bus + '-' + configs['global_vars']['ci_label'] + '-' + 'System'
        network.add(
            "Bus",
            ci_bus,
        )
        
        # add link to represent C&I grid imports
        network.add(
            "Link",
            name=ci_bus + '-' + 'grid-import',
            bus0=ci_bus,
            bus1=bus,
            type='HVAC',
            carrier='transmission-HVAC-overhead',
            build_year=configs['global_vars']['year'],
            p_nom_extendable=False,
            # parameters below make it a bidirectional lossless links
            capital_cost=0,
            marginal_cost=0,
            efficiency=1,
            p_min_pu=0,
        )

        # add link to represent C&I grid exports
        network.add(
            "Link",
            name=ci_bus + '-' + 'grid-export',
            bus0=bus,
            bus1=ci_bus,
            type='HVAC',
            carrier='transmission-HVAC-overhead',
            build_year=configs['global_vars']['year'],
            p_nom_extendable=False,
            # parameters below make it a bidirectional lossless links
            capital_cost=0,
            marginal_cost=0,
            efficiency=1,
            p_min_pu=0,
        )

        # ----------------------------------------------------------------------
        # Step 3: 
        # Add new generators and storages solely for C&I PPA
        # ----------------------------------------------------------------------

        for technology in configs['technology_palette'][run['palette']]:
            # add generator if technolgy is a generator
            if technology in network.generators.type.unique():

                # get params
                params = (
                    network
                    .generators
                    .loc[ 
                        network.generators.type == technology
                    ]
                    .groupby(by='type')
                    .first()
                    .melt()
                    .set_index('attribute')
                    ['value']
                    .to_dict()
                )

                # get cf if renewable
                cf = network.generators_t.p_max_pu.filter(regex = bus + '-' + technology)

                if cf.empty:
                    cf = params['p_max_pu']
                else:
                    cf = cf.iloc[:,0].values

                # add generator
                network.add(
                    'Generator', # PyPSA component
                    ci_bus + '-' + technology + '-ext-' + str(params['build_year']) + '-' + 'PPA', # generator name
                    type = technology, # technology type (e.g., solar, gas-ccgt etc.)
                    bus = ci_bus, # region/bus/balancing zone
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
                    p_nom_extendable = False, # can the model build more?
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
            
            # add storage if technology is a storage unit
            if technology in network.storage_units.carrier.unique():

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
                    .set_index('attribute')
                    ['value']
                    .to_dict()
                )
                
                # add bus for storage
                ci_bus_storage = ci_bus + '-' + params['carrier']
                network.add(
                    'Bus',
                    ci_bus_storage,
                )

                network.add(
                    "StorageUnit",
                    ci_bus + '-' + params['carrier'],
                    bus = ci_bus + '-' + params['carrier'],
                    p_nom_extendable = False,
                    cyclic_state_of_charge=True,
                    max_hours=params['max_hours'],
                    build_year=params['build_year'],
                    carrier=params['carrier'],
                    capital_cost=params['capital_cost'],
                )

                # add link to represent storage charge
                network.add(
                    "Link",
                    ci_bus + '-' + params['carrier'] + "-charge",
                    bus0 = ci_bus,
                    bus1 = ci_bus_storage,
                    efficiency = 0.9,
                    p_nom_extendable = False,
                    #capital_cost=params['capital_cost'],
                    #marginal_cost=params['marginal_cost'],
                )

                # add link to represent storage discharge
                network.add(
                    "Link",
                    ci_bus + '-' + params['carrier'] + "-discharge",
                    bus0 = ci_bus_storage,
                    bus1 = ci_bus,
                    p_nom_extendable = False,
                    efficiency = params['efficiency_dispatch'],
                    marginal_cost=params['marginal_cost'],
                )

                # # add storage unit
                # network.add(
                #     'StorageUnit',
                #     ppa_bus + '-' + params['carrier'],
                #     bus=ppa_bus + '-' + params['carrier'], 
                #     carrier=params['carrier'],
                #     p_nom=0, # starting capacity (MW)
                #     p_nom_min=0, # minimum capacity (MW)
                #     p_nom_extendable=False,
                #     capital_cost=params['capital_cost'],
                #     marginal_cost=params['marginal_cost'],
                #     build_year=params['build_year'],
                #     lifetime=params['lifetime'],
                #     state_of_charge_initial=params['state_of_charge_initial'],
                #     max_hours=params['max_hours'],
                #     efficiency_store=params['efficiency_store'],
                #     efficiency_dispatch=params['efficiency_dispatch'],
                #     standing_loss=params['standing_loss'],
                #     cyclic_state_of_charge=params['cyclic_state_of_charge'],
                # )

    # ----------------------------------------------------------------------
    # ADD CONSTRAINTS
    # ----------------------------------------------------------------------

    lp_model = network.optimize.create_model()

    # Renewable targets
    # --------------------

    lp_model, network = constraint_clean_generation_target(lp_model, network, ci_nodes=run['nodes_with_ci_load'], configs=configs)

    # Charging storages with fossil fuels
    # --------------------

    if not configs['global_vars']['enable_fossil_charging']:
        lp_model, network = constraint_fossil_storage_charging(lp_model, network)

    # solve
    print('Beginning optimization...')

    try:
        network.optimize.solve_model(
            solver_name=configs['global_vars']['solver'],
        )
    except:
        network.optimize(
            solver_name=configs['global_vars']['solver'],
            #solver_options={ 'solver': 'pdlp' },
            #multi_year_investment=True,
        )
    
    # save results
    setup_dir(
        path_to_dir=configs['paths']['output_model_runs'] + run['name'] + '/solved_networks/'
    )

    network.export_to_netcdf(
        os.path.join(
            configs['paths']['output_model_runs'], run['name'], 'solved_networks', 'brownfield_' + str(configs['global_vars']['year']) + '.nc'
        )
    )
    
    return network