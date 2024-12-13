import os
import sys
sys.path.append('../')
import pypsa
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

from matplotlib.ticker import MaxNLocator

from src import (
    brownfield, 
    cfe,
    helpers,
    postprocess
)


def GetGridCFE(
        n : pypsa.Network, 
        # bus : str,
        ci_identifier : str,
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
        i for i in n.carriers.query(" co2_emissions <= 0").index.tolist() 
        if i in n.generators.carrier.tolist()
    ]

    # get clean generators in R
    R_clean_generators = (
        n.generators.loc[
            # clean carriers
            (n.generators.carrier.isin(global_clean_carriers)) &
            # exclude assets not in R
            #(n.generators.index.str.contains(bus)) &
            # exclude C&I assets
            (~n.generators.index.str.contains(ci_identifier))
        ]
        .index
    )
    
    # get all generators
    R_all_generators = (
        n.generators.loc[ 
            (~n.generators.index.str.contains(ci_identifier))
        ]
        .index
    )

    # calculate CFE sceore
    total_clean_generation = n.generators_t.p[R_clean_generators].sum(axis=1)
    total_generation = n.generators_t.p[R_all_generators].sum(axis=1)

    # return CFE score
    return ( total_clean_generation / total_generation).round(2).tolist()


def PostProcessBrownfield(n : pypsa.Network):
    '''
    This function post-processes the brownfield network to make it ready for the CFE and RES100 simulations.
    The logic is that we fix all optimised capacities in 2030 (brownfield) and only allow the C&I assets to be extendable, 
    representing the "additionality" of their PPA.
    '''
    components = ['generators', 'links', 'storage_units']
    for c in components:
        # Fix p_nom to p_nom_opt for each component in brownfield network
        getattr(n, c)['p_nom'] = getattr(n, c)['p_nom_opt']
        # make everything non-extendable
        getattr(n, c)['p_nom_extendable'] = False
        # ...besides the C&I assets
        getattr(n, c).loc[ getattr(n, c).index.str.contains(ci_identifier), 'p_nom_extendable' ] = True
    return n


def RunBrownfieldSimulation(run, configs):
    '''Setup and run the brownfield simulation
    '''
    N_BROWNFIELD = brownfield.SetupBrownfieldNetwork(run, configs)

    N_BROWNFIELD = (
        cfe.PrepareNetworkForCFE(
            N_BROWNFIELD, 
            buses_with_ci_load=run['nodes_with_ci_load'],
            ci_load_fraction=run['ci_load_fraction'],
            technology_palette=configs['technology_palette'][ run['palette'] ],
            p_nom_extendable=False,
        )
    )
    
    print('prepared network for CFE')
    print('Begin solving...')

    N_BROWNFIELD.optimize(solver_name=configs['global_vars']['solver'])

    N_BROWNFIELD.export_to_netcdf(
        os.path.join(
            configs['paths']['output_model_runs'], 
            run['name'], 
            'solved_networks', 
            'brownfield_' + str(configs['global_vars']['year']) + '.nc'
        )
    )

    return N_BROWNFIELD


def RunRES100(
        N_BROWNFIELD : pypsa.Network,
        #bus : str,
    ):
    '''Sets up the 100% RES (annual matching) simulation
    '''
    
    # make a copy of the brownfield
    N_RES_100 = N_BROWNFIELD#.copy()

    # post-process to set what is expandable and non-expandable
    N_RES_100 = PostProcessBrownfield(N_RES_100)

    # init linopy model
    N_RES_100.optimize.create_model()

    for bus in run['nodes_with_ci_load']:

        # get total C&I load (float)
        CI_Demand = (
            N_RES_100.loads_t.p_set
            .filter(regex=bus)
            .filter(regex=ci_identifier)
            .sum()
            .sum()
        )

        # get grid exports
        CI_GridExport = (
            N_RES_100.model.variables['Link-p'].sel(
                Link=[i for i in N_RES_100.links.index if ci_identifier in i and 'Export' in i and bus in i]
            )
            .sum(dims='Link')
        )

        # get total PPA procurement (linopy.Var)
        ci_ppa_generators = (
            N_RES_100.generators.loc[
                (N_RES_100.generators.bus.str.contains(bus)) &
                (N_RES_100.generators.bus.str.contains(ci_identifier))
            ]
            .index
            .tolist()
        ) # get c&i ppa generators

        CI_PPA = (
            N_RES_100
            .model
            .variables['Generator-p']
            .sel(
                Generator=ci_ppa_generators
            )
            .sum()
        )

        # get clean carriers in the regional grid
        clean_carriers = [
            i for i in N_RES_100.carriers.query(" co2_emissions <= 0").index.tolist() 
            if i in N_RES_100.generators.carrier.tolist()
        ]

        # clean generators
        clean_region_generators = [
            i for i in N_RES_100.generators.loc[ N_RES_100.generators.carrier.isin(clean_carriers) ].index
            if ci_identifier not in i and bus[0:3] in i
        ]

        # Constraint 1: Annual matching
        # ---------------------------------------------------------------
        N_RES_100.model.add_constraints(
            CI_PPA >= (RES_TARGET/100) * CI_Demand,
            name = f'{RES_TARGET}_RES_constraint_{bus}',
        )

        # Constraint 2: Excess (export from C&I system to grid)
        # ---------------------------------------------------------------
        N_RES_100.model.add_constraints(
            CI_GridExport.sum() <= CI_Demand * configs['global_vars']['maximum_excess_export'],
        )

    N_RES_100.optimize.solve_model(solver_name = configs['global_vars']['solver'])

    N_RES_100.export_to_netcdf(
        os.path.join(
            configs['paths']['output_model_runs'], 
            run['name'], 
            'solved_networks', 
            'annual_matching_' + 'RES' + str(RES_TARGET) + '_' + str(configs['global_vars']['year']) + '.nc'
        )
    )

    return N_RES_100


def RunCFE(N_BROWNFIELD : pypsa.Network, CFE_Score):
    '''Run 24/7 CFE scenario
    '''

    N_CFE = N_BROWNFIELD#.copy()
    N_CFE = PostProcessBrownfield(N_CFE)

    # init linopy model
    N_CFE.optimize.create_model()

    # ---------------------------------------------------------------
    #
    #   ITERATIVELY SOLVE FOR GRID CFE
    #
    #   Following Xu and Jenkins (2021), here we iteratively solve 
    #   for the grid supply CFE score. We have to do this to avoid a 
    #   a non-convex problem, where two dynamic decision variables 
    #   (grid supply and grid CFE) are being multiplied by one another. 
    #   This approach allows us to compute the grid CFE "a priori" and
    #   then feed it as a parameter into the model.
    #
    #   The process is as follows:
    #       1. Set the grid CFE to 0 and run the model
    #       2. Calculate the real grid CFE from (1)
    #       3. Now, fix the grid CFE to (2) and re-run the model
    #       4. Calculate the grid CFE from (3) and compare against (2)
    #       5. If the difference is less than 0.01, stop. Otherwise, repeat from (3)
    # 
    # ---------------------------------------------------------------

    # start a counter and initialise a dataframe to store the results
    count = 1
    GridSupplyCFE = pd.DataFrame({})

    # [Step 1] Run the model with grid supply CFE set to 0
    GridCFE = [0 for i in range(N_CFE.snapshots.size)]
    GridSupplyCFE[f'iteration_{count}'] = GridCFE

    # apply the CFE constraint
    N_CFE = (
        cfe
        .apply_cfe_constraint(
            N_CFE, 
            GridCFE, 
            run['nodes_with_ci_load'], 
            ci_identifier, 
            CFE_Score,
            configs['global_vars']['maximum_excess_export'],
        )
    )

    # optimise
    N_CFE.optimize.solve_model(solver_name = configs['global_vars']['solver'])

    # get GridCFE
    GridCFE = GetGridCFE(N_CFE, ci_identifier)
    count += 1
    GridSupplyCFE[f'iteration_{count}'] = GridCFE

    # calculate difference between iterations with a maximum of 100 loops
    max_iterations = 100
    while (GridSupplyCFE[f'iteration_{count}'].sum() - GridSupplyCFE[f'iteration_{count-1}'].sum()) > 0.01 and count < max_iterations:
        N_CFE = cfe.apply_cfe_constraint(
            N_CFE, 
            GridCFE, 
            run['nodes_with_ci_load'], 
            ci_identifier, 
            CFE_Score,
            configs['global_vars']['maximum_excess_export'],
        )
        N_CFE.optimize.solve_model(solver_name=configs['global_vars']['solver'])
        GridCFE = GetGridCFE(N_CFE, ci_identifier)
        count += 1
        GridSupplyCFE[f'iteration_{count}'] = GridCFE

    # save iteration results
    helpers.setup_dir(
        path_to_dir=os.path.join(configs['paths']['output_model_runs'], run['name'], 'grid_supply_cfe_iterations')
    )

    GridSupplyCFE.to_csv(
        os.path.join(
            configs['paths']['output_model_runs'], run['name'], 'grid_supply_cfe_iterations',
            'cfe' + str(int(CFE_Score*100)) + '.csv'
        )
    )

    N_CFE.export_to_netcdf(
        os.path.join(
            configs['paths']['output_model_runs'], 
            run['name'], 
            'solved_networks', 
            'hourly_matching_' + 'CFE' + str(int(CFE_Score*100)) + '_' + str(configs['global_vars']['year']) + '.nc'
        )
    )


if __name__ == '__main__':

    print('*'*100)
    print('BEGIN MODEL RUNS')
    print('')

    # get config file
    configs = helpers.load_configs('configs.yaml')
    ci_identifier = configs['global_vars']['ci_label']

    # ----------------------------------------------------------------------
    # RUN SCENARIOS
    # ----------------------------------------------------------------------
    scenarios = {}
    for run in configs['model_runs']:

        # setup a directory for outputs
        helpers.setup_dir(
            path_to_dir=configs['paths']['output_model_runs'] + run['name'] + '/solved_networks/'
        )

        print('Running: ' + run['name'])

        # Run brownfield
        print('Compute brownfield scenario...')
        N_BROWNFIELD = RunBrownfieldSimulation(run, configs)

        # 100% RES SIMULATION
        RES_TARGET = 100
        print(f'Computing annual matching scenario (RES Target: {int(RES_TARGET)}%)...')
        RunRES100(N_BROWNFIELD)

        # Compute hourly matching scenarios
        for CFE_Score in run['cfe_score']:
            print(f'Computing hourly matching scenario (CFE: {int(CFE_Score*100)}...')
            RunCFE(N_BROWNFIELD, CFE_Score=CFE_Score)

    # ----------------------------------------------------------------------
    # MAKE PLOTS FOR EACH SCENARIO
    # ----------------------------------------------------------------------

    # def summarise_results():
    #     pass
    
    for run in configs['model_runs']:

        path_to_run_dir = (
            os.path.join(
                configs['paths']['output_model_runs'], run['name'],
            )
        )

        postprocess.plot_results(path_to_run_dir)

    print('*'*100)