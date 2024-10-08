import os
import sys
sys.path.append('../')
import pypsa

import src.helpers as helpers
import src.postprocess as postprocess
import src.plotting as plotting

from src.prepare_brownfield_network import SetupBrownfieldNetwork
from src.prepare_network_for_cfe import PrepareNetworkForCFE


def GetGridCFE(n : pypsa.Network):
    '''Compute "clean" score of a given grid
    '''
    # get dirty carraiers
    dirty_carriers = [
        i for i in n.carriers.query(" co2_emissions > 0").index.tolist() 
        if i in n.generators.carrier.tolist()
    ]

    # get clean carriers
    clean_carriers = [
        i for i in n.carriers.query(" co2_emissions <= 0").index.tolist() 
        if i in n.generators.carrier.tolist()
    ]

    # get total generation
    sum_generation = n.generators_t.p.T.groupby(n.generators.carrier).sum()

    # compute total clean and dirty generation
    sum_generation_clean = sum_generation.loc[clean_carriers].sum().sum()
    sum_generation_dirty = sum_generation.loc[dirty_carriers].sum().sum()

    return sum_generation_clean / (sum_generation_clean + sum_generation_dirty) # % of clean generation


def PostProcessBrownfield(n : pypsa.Network):
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
    N_BROWNFIELD = SetupBrownfieldNetwork(run, configs)

    N_BROWNFIELD = (
        PrepareNetworkForCFE(
            N_BROWNFIELD, 
            buses_with_ci_load=run['nodes_with_ci_load'],
            ci_load_fraction=run['ci_load_fraction'],
            technology_palette=configs['technology_palette'][ run['palette'] ],
            p_nom_extendable=False,
        )
    )
    
    print('prepared network for CFE')
    print('Begin solving...')

    N_BROWNFIELD.optimize(solver_name='gurobi')

    N_BROWNFIELD.export_to_netcdf(
        os.path.join(
            configs['paths']['output_model_runs'], 
            run['name'], 
            'solved_networks', 
            'brownfield_' + str(configs['global_vars']['year']) + '.nc'
        )
    )

    return N_BROWNFIELD


def RunRES100(N_BROWNFIELD : pypsa.Network):
    '''
    TODO: 
    Right now, this assumes that we apply 100% RES at each bus, but in reality this type 
    of procurement can happen at any bus. We need to think about how to implement this.
    '''
    
    # make a copy of the brownfield
    N_RES_100 = N_BROWNFIELD.copy()

    # post-process to set what is expandable and non-expandable
    N_RES_100 = PostProcessBrownfield(N_RES_100)

    # init linopy model
    N_RES_100.optimize.create_model()

    for bus in run['nodes_with_ci_load']:

        # get total C&I load (float)
        sum_ci_load = (
            N_RES_100.loads_t.p_set
            .filter(regex=bus)
            .filter(regex=ci_identifier)
            .sum()
            .sum()
        )

        # get generators
        ci_ppa_generators = (
            N_RES_100.generators.loc[
                (N_RES_100.generators.bus.str.contains(bus)) &
                (N_RES_100.generators.bus.str.contains(ci_identifier))
            ]
            .index
            .tolist()
        )

        # get total PPA procurement (linopy.Var)
        sum_ppa_procured = (
            N_RES_100
            .model
            .variables['Generator-p']
            .sel(
                Generator=ci_ppa_generators
            )
            .sum()
        )

        # add constraint
        N_RES_100.model.add_constraints(
            sum_ppa_procured >= (RES_TARGET/100) * sum_ci_load,
            name = f'{RES_TARGET}_RES_constraint_{bus}',
        )

    N_RES_100.optimize.solve_model(solver_name = 'gurobi')

    N_RES_100.export_to_netcdf(
        os.path.join(
            configs['paths']['output_model_runs'], 
            run['name'], 
            'solved_networks', 
            'annual_matching_' + 'RES' + str(RES_TARGET) + '_' + str(configs['global_vars']['year']) + '.nc'
        )
    )

    return N_RES_100


def RunCFE(N_BROWNFIELD : pypsa.Network, GridCFE, CFE_Score):
    '''
    '''

    N_CFE = N_BROWNFIELD.copy()
    N_CFE = PostProcessBrownfield(N_CFE)

    # init linopy model
    N_CFE.optimize.create_model()

    for bus in run['nodes_with_ci_load']:
        
        # ---
        # fetch necessary variables to implement CFE

        # C&I demand
        CI_Demand = (
            N_CFE.loads_t.p_set.filter(regex=bus).filter(regex=ci_identifier).values.flatten()
        )

        CI_StorageCharge = (
            N_CFE.model.variables['Link-p'].sel(
                Link=[i for i in N_CFE.links.index if ci_identifier in i and 'Charge' in i]
            )
        )

        CI_StorageDischarge = (
            N_CFE.model.variables['Link-p'].sel(
                Link=[i for i in N_CFE.links.index if ci_identifier in i and 'Discharge' in i]
            )
        )

        CI_GridExport = (
            N_CFE.model.variables['Link-p'].sel(
                Link=[i for i in N_CFE.links.index if ci_identifier in i and 'Export' in i]
            )
        )

        CI_GridImport = (
            N_CFE.model.variables['Link-p'].sel(
                Link=[i for i in N_CFE.links.index if ci_identifier in i and 'Import' in i]
            )
        )

        CI_PPA = (
            N_CFE.model.variables['Generator-p'].sel(
                Generator=[i for i in N_CFE.generators.index if ci_identifier in i and 'PPA' in i]
            )
        )

        # Constraint 1: Hourly matching
        # ---------------------------------------------------------------

        N_CFE.model.add_constraints(
            ((CI_StorageCharge - CI_StorageDischarge) + CI_Demand) == CI_PPA - CI_GridExport + CI_GridImport,
            name = f'hourly_matching_constraint_{bus}',
        )

        # Constraint 2: CFE target
        # ---------------------------------------------------------------

        N_CFE.model.add_constraints(
            (CI_PPA - CI_GridExport + CI_GridImport * GridCFE).sum() >= ((CI_StorageCharge - CI_StorageDischarge) + CI_Demand).sum() * CFE_Score,
            name = 'CFE_target_constraint',
        )

        # Constraint 3: Excess
        # ---------------------------------------------------------------
        N_CFE.model.add_constraints(
            CI_GridExport.sum() <= sum(CI_Demand) * configs['global_vars']['maximum_excess_export'],
            name = 'total_excess_constraint',
        )


    N_CFE.optimize.solve_model(solver_name = 'gurobi')

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

    # setup params
    RES_TARGET = 100
    ci_identifier = 'C&I'

    # get config file
    configs = helpers.load_configs('configs.yaml')

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
        print(f'Computing annual matching scenario (RES Target: {int(RES_TARGET)}%)...')
        RunRES100(N_BROWNFIELD)

        # Compute hourly matching scenarios
        GridCFE = GetGridCFE(N_BROWNFIELD)
        for CFE_Score in run['cfe_score']:
            print(f'Computing hourly matching scenario (CFE: {int(CFE_Score*100)} | GridCFE: {round(GridCFE,2)})...')
            RunCFE(N_BROWNFIELD, GridCFE=0.3, CFE_Score=CFE_Score)
            
        
        #     scenarios['hourly_matching_' + str(cfe_score)] = hourly_matching

        # ----------------------------------------------------------------------
        # MAKE PLOTS FOR EACH SCENARIO
        # ----------------------------------------------------------------------
        
        # # set path
        # fig_path = os.path.join(configs['paths']['output_model_runs'], run['name'])
        
        # # plot capacity
        # capacity = postprocess.aggregate_capacity(scenarios).reset_index()

        # fig = (
        #     plotting
        #     .plot_capacity_bar(
        #         capacity,
        #         carriers=brownfield_network.carriers,
        #         width=1000,
        #         height=400,
        #     )
        # )


        # fig.write_image( os.path.join(fig_path, 'capacity.png') )
        # fig.write_html( os.path.join(fig_path, 'capacity.html') )

    
    print('*'*100)