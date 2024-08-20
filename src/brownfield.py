import os
import yaml
import pypsa

import tz_pypsa as tza
from tz_pypsa.model import Model

from .helpers import *

def run_brownfield_scenario(
        run : dict = None,
        configs : dict = None
) -> pypsa.Network:

    '''Run a brownfield scenario without CFE considerations.
    '''
    
    # setup network
    print('loading model: ', run['core_model'])

    network = (
        Model.load_model(
            run['core_model'], 
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
    network.links['p_nom_extendable']           = True
    network.storage_units['p_nom_extendable']   = True

    # ----------------------------------------------------------------------
    # Step 1: 
    # Separate C&I and non-C&I load
    # ----------------------------------------------------------------------

    for bus in run['nodes_with_ci_load']:
        # subtract out C&I load from bus
        network.loads_t.p_set[bus] *= (1 - run['ci_load_fraction'])

        # add C&I load to bus as a separate load
        network.add(
            "Load",
            bus + '-' + configs['global_vars']['ci_label'],
            bus=bus,
            p_set=network.loads_t.p_set[bus] * run['ci_load_fraction'],
        )
    
    # ----------------------------------------------------------------------
    # Step 2: 
    # Create a bus for C&I PPA
    # ----------------------------------------------------------------------

    for bus in run['nodes_with_ci_load']:

        # add bus for C&I PPA
        network.add(
            "Bus",
            bus + '-' + configs['global_vars']['ci_label'],
        )
        
        # add bus for C&I PPA
        network.add(
            "Link",
            name='virtual-link-' + bus + '-' + configs['global_vars']['ci_label'] + '-' + bus,
            bus0=bus + '-' + configs['global_vars']['ci_label'],
            bus1=bus,
            type=network.links.type.unique()[0],
            carrier=network.links.carrier.unique()[0],
            build_year=network.links.build_year.unique()[0],
            p_nom_extendable=False,
            marginal_cost=0,
            capital_cost=0,
            efficiency=1,
        )
    
    # ----------------------------------------------------------------------
    # Step 3: 
    # Add new generators and storages solely for C&I PPA
    # ----------------------------------------------------------------------

    for bus in run['nodes_with_ci_load']:
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
                    bus + '-' + technology + '-ext-' + str(params['build_year']) + '-' + configs['global_vars']['ci_label'], # generator name
                    type = technology, # technology type (e.g., solar, gas-ccgt etc.)
                    bus = bus + '-' + configs['global_vars']['ci_label'], # region/bus/balancing zone
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
            
            # add storage if technolgy is a storage unit
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

                # add storage unit
                network.add(
                    'StorageUnit',
                    bus + '-' + technology + '-ext-' + str(params['build_year']) + '-' + configs['global_vars']['ci_label'],
                    bus=bus + '-' + configs['global_vars']['ci_label'], 
                    carrier=params['carrier'],
                    p_nom=0, # starting capacity (MW)
                    p_nom_min=0, # minimum capacity (MW)
                    p_nom_extendable=False,
                    capital_cost=params['capital_cost'],
                    marginal_cost=params['marginal_cost'],
                    build_year=params['build_year'],
                    lifetime=params['lifetime'],
                    state_of_charge_initial=params['state_of_charge_initial'],
                    max_hours=params['max_hours'],
                    efficiency_store=params['efficiency_store'],
                    efficiency_dispatch=params['efficiency_dispatch'],
                    standing_loss=params['standing_loss'],
                    cyclic_state_of_charge=params['cyclic_state_of_charge'],
                )

    # ----------------------------------------------------------------------
    # Step 4: 
    # Set renewable targets in brownfield network
    # ----------------------------------------------------------------------
    # TODO!

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