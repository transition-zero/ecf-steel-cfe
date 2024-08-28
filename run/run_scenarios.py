import os
import sys
sys.path.append('../')

import src.helpers as helpers
import src.postprocess as postprocess
import src.plotting as plotting

from src.brownfield import run_brownfield_scenario
from src.annual_matching import run_annual_matching_scenario
from src.hourly_matching import run_hourly_matching_scenario

if __name__ == '__main__':

    print('*'*100)
    print('BEGIN MODEL RUNS')
    print('')

    # get config file
    configs = helpers.load_configs('configs.yaml')

    # ----------------------------------------------------------------------
    # RUN SCENARIOS
    # ----------------------------------------------------------------------
    scenarios = {}
    for run in configs['model_runs']:

        print('Running: ' + run['name'])
        print('Compute brownfield scenario...')

        brownfield_network = (
            run_brownfield_scenario(
                run,
                configs,
            )
        )

        scenarios['brownfield'] = brownfield_network

        for cfe_score in run['cfe_score']:

            print(f'Computing annual matching scenario (CFE: {int(cfe_score*100)})...')

            annual_matching = (
                run_annual_matching_scenario(
                    run,
                    configs,
                    brownfield_network,
                    cfe_score,
                )
            )

            scenarios['annual_matching_' + str(cfe_score)] = annual_matching

            print(f'Computing hourly matching scenario (CFE: {int(cfe_score*100)})...')

            hourly_matching = (
                run_hourly_matching_scenario(
                    run,
                    configs,
                    brownfield_network,
                    cfe_score,
                )
            )

            scenarios['hourly_matching_' + str(cfe_score)] = hourly_matching

        # ----------------------------------------------------------------------
        # MAKE PLOTS FOR EACH SCENARIO
        # ----------------------------------------------------------------------
        
        # set path
        fig_path = os.path.join(configs['paths']['output_model_runs'], run['name'])
        
        # plot capacity
        capacity = postprocess.aggregate_capacity(scenarios).reset_index()

        fig = (
            plotting
            .plot_capacity_bar(
                capacity,
                carriers=brownfield_network.carriers,
                width=1000,
                height=400,
            )
        )


        fig.write_image( os.path.join(fig_path, 'capacity.png') )
        fig.write_html( os.path.join(fig_path, 'capacity.html') )

    
    print('*'*100)