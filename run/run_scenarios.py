import sys
sys.path.append('../')

import src.helpers as helpers

from src.brownfield import run_brownfield_scenario
from src.annual_matching import run_annual_matching_scenario
from src.hourly_matching import run_hourly_matching_scenario

if __name__ == '__main__':

    print('*'*100)
    print('BEGIN MODEL RUNS')
    print('')

    # get config file
    configs = helpers.load_configs('configs.yaml')

    # run scenarios
    for run in configs['model_runs']:

        print('Running: ' + run['name'])
        print('Compute brownfield scenario...')

        brownfield_network = (
            run_brownfield_scenario(
                run,
                configs,
            )
        )

        print('Computing annual matching scenario...')

        run_annual_matching_scenario(
            run,
            configs,
            brownfield_network,
        )

        print('Computing hourly matching scenario...')

        run_hourly_matching_scenario(
            run,
            configs,
            brownfield_network,
        )

        #print('\n'*2)
        print('*'*100)