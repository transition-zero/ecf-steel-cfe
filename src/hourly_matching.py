import os
import yaml
import pypsa

import tz_pypsa as tza
from tz_pypsa.model import Model

from .helpers import *

def run_hourly_matching_scenario(
        run : dict = None,
        configs : dict = None,
        brownfield_network : pypsa.Network = None,
    ) -> pypsa.Network:
    
    '''Run a network with annually matched renewable generation.
    '''
    
    # make a copy of the brownfield network
    network = brownfield_network.copy()

    # fix p_nom to p_nom_opt in brownfield network
    network.generators['p_nom']      = network.generators['p_nom_opt']
    network.links['p_nom']           = network.links['p_nom_opt']
    network.storage_units['p_nom']   = network.storage_units['p_nom_opt']

    # make everything unextendable
    network.generators['p_nom_extendable']      = False
    network.links['p_nom_extendable']           = False
    network.storage_units['p_nom_extendable']   = False

    # make C&I assets extendable
    network.generators.loc[network.generators.bus.str.contains(configs['global_vars']['ci_label']), 'p_nom_extendable' ]        = True
    network.links.loc[network.links.bus0.str.contains(configs['global_vars']['ci_label']), 'p_nom_extendable' ]                 = True
    network.storage_units.loc[network.storage_units.bus.str.contains(configs['global_vars']['ci_label']), 'p_nom_extendable' ]  = True
    
    # -----------------------------------
    # Add hourly matching constraints
    # -----------------------------------

    # init linopy model
    lp_model = network.optimize.create_model()

    for bus in run['nodes_with_ci_load']:

        lhs_generators = [i for i in network.generators.index if configs['global_vars']['ci_label'] in i and bus in i]
        lhs_storages = [i for i in network.storage_units.index if configs['global_vars']['ci_label'] in i and bus in i]
        rhs_load = network.loads_t.p_set[bus + '-' + configs['global_vars']['ci_label']]

        # get hourly dispatch from clean generators
        lhs_total_hourly_generation = (
            lp_model
            .variables['Generator-p']
            .sel(Generator=lhs_generators)
            .sum('Generator')
        )

        # get hourly dispatch from storage
        lhs_total_hourly_storage_discharge = (
            lp_model
            .variables['StorageUnit-p_dispatch']
            .sel(StorageUnit=lhs_storages)
            .sum('StorageUnit')
        )

        lp_model.add_constraints(
            lhs_total_hourly_generation + lhs_total_hourly_storage_discharge == run['cfe_score'] * rhs_load,
            name = f'cfe_constraint_{bus}',
        )
    
    # solve
    print('Beginning optimisation')

    network.optimize.solve_model(
        solver_name=configs['global_vars']['solver'],
    )

    # save results
    setup_dir(
        path_to_dir=configs['paths']['output_model_runs'] + run['name'] + '/solved_networks/'
    )

    network.export_to_netcdf(
        os.path.join(
            configs['paths']['output_model_runs'], run['name'], 'solved_networks', 'hourly_matching_' + str(configs['global_vars']['year']) + '_cfe' + str(int(run['cfe_score']*100)) + '.nc'
        )
    )

    return network