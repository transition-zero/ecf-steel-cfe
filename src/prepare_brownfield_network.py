
import pypsa

from tz_pypsa.model import Model

def SetupBrownfieldNetwork(run, configs) -> pypsa.Network:
    '''This function sets up the brownfield system
    '''
    
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

    # set p_nom_min to prevent decommissioning of assets
    network.generators['p_nom_min']      = network.generators['p_nom']
    network.storage_units['p_nom_min']   = network.storage_units['p_nom']
    network.links['p_nom_min']           = network.links['p_nom']

    return network



    # # ----------------------------------------------------------------------
    # # ADD CONSTRAINTS
    # # ----------------------------------------------------------------------

    # lp_model = network.optimize.create_model()

    # # Renewable targets
    # # --------------------

    # lp_model, network = constraint_clean_generation_target(lp_model, network, ci_nodes=run['nodes_with_ci_load'], configs=configs)

    # # Charging storages with fossil fuels
    # # --------------------

    # if not configs['global_vars']['enable_fossil_charging']:
    #     lp_model, network = constraint_fossil_storage_charging(lp_model, network)

    # # solve
    # print('Beginning optimization...')

    # try:
    #     network.optimize.solve_model(
    #         solver_name=configs['global_vars']['solver'],
    #     )
    # except:
    #     network.optimize(
    #         solver_name=configs['global_vars']['solver'],
    #         #solver_options={ 'solver': 'pdlp' },
    #         #multi_year_investment=True,
    #     )
    
    # # save results
    # setup_dir(
    #     path_to_dir=configs['paths']['output_model_runs'] + run['name'] + '/solved_networks/'
    # )

    # network.export_to_netcdf(
    #     os.path.join(
    #         configs['paths']['output_model_runs'], run['name'], 'solved_networks', 'brownfield_' + str(configs['global_vars']['year']) + '.nc'
    #     )
    # )
    
    # return network