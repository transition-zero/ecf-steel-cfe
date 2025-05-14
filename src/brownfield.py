
import pypsa

from tz_pypsa.model import Model
from tz_pypsa.constraints import (
    constr_cumulative_p_nom,
    constr_bus_self_sufficiency,
    constr_bus_individual_self_sufficiency,
    constr_min_annual_generation,
    constr_policy_targets,
    constr_max_annual_utilisation,
    constr_min_annual_utilisation_links,
    constr_max_annual_utilisation_links,
    constr_min_annual_utilisation_generator,
    constr_max_annual_utilisation_generator,
    constr_cofiring_ccs_generation_join_plant
)

def SetupBrownfieldNetwork(run, configs) -> pypsa.Network:
    """
    
    Sets up the brownfield network based on the provided run configuration and global variables.

    Parameters:
    -----------
    run (dict): A dictionary containing run-specific configurations such as 'stock_model', 'select_nodes', 'backstop', and 'allow_grid_expansion'.
    configs (dict): A dictionary containing global configuration variables including 'frequency', 'timesteps', 'year', and 'set_global_constraints'.

    Returns:
    -----------
    pypsa.Network: A PyPSA Network object with the brownfield system set up according to the provided configurations.

    """
    
    
    if configs["model_runs"][0]["stock_model"] == "ASEAN":
    # load the stock model from tza-pypsa 
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
    else: 
        network = (
        Model.load_csv_from_dir(
            configs['paths']['path_to_model'], 
            #run['stock_model'], 
            frequency = configs['global_vars']['frequency'],
            timesteps = configs['global_vars']['timesteps'],
            #select_nodes=configs['global_vars']['select_nodes'], 
            year=[ configs['global_vars']['year'] ],
            #backstop=run['backstop'],
            set_global_constraints=configs['global_vars']['set_global_constraints'],
        )
    )

    # if expansion is set to True, set p_nom_extendable to True for generators and storage units
    # otherwise if False, leaves propreties as they are (in case some are already set to True and others to False)
    if run["allow_generation_expansion"]:
        network.generators['p_nom_extendable'] = run["allow_generation_expansion"]
    if run["allow_storage_expansion"]:
        network.storage_units['p_nom_extendable']   = run["allow_storage_expansion"]
    if run["allow_grid_expansion"]:
        network.links['p_nom_extendable']   = run["allow_grid_expansion"]
    network.storage_units.p_nom_extendable.loc[network.storage_units.index.str.contains('lithium')] = True
    network.storage_units.p_nom_extendable.loc[network.storage_units.index.str.contains('pumped')] = False

    # set p_nom_min to prevent early decommissioning of assets
    network.generators['p_nom_min']      = network.generators['p_nom']
    network.storage_units['p_nom_min']   = network.storage_units['p_nom']
    network.links['p_nom_min']           = network.links['p_nom']

    return network

def ApplyBrownfieldConstraints(network, run, configs) -> pypsa.Network:
    """
    
    Applies brownfield constraints to the network based on the provided run configuration and global variables.
    These constraints are used regardless of the annual matching or CFE scenario.

    Parameters:
    -----------
    network (pypsa.Network): A PyPSA Network object that represents the brownfield system.
    run (dict): A dictionary containing run-specific configurations such as 'stock_model', 'select_nodes', 'backstop', and 'allow_grid_expansion'.
    configs (dict): A dictionary containing global configuration variables including 'frequency', 'timesteps', 'year', and 'set_global_constraints'.

    Returns:
    -----------
    pypsa.Network: A PyPSA Network object with the brownfield constraints applied.

    """

    # Implement all the constraints, as defined in the configs
    # Bus self-sufficiency constraint
    if configs["constraints"]["bus_self_sufficiency"]["enable"]:
        constr_bus_self_sufficiency(network, 
                                    min_self_sufficiency = configs["constraints"]["bus_self_sufficiency"]["fraction"])
    
    # Bus self-sufficiency constraint, individually set
    if configs["constraints"]["bus_individual_self_sufficiency"]["enable"]:
        constr_bus_individual_self_sufficiency(network)
    
    # Policy constraints
    if configs["constraints"]["policy_targets"]["enable"]:
        constr_policy_targets(network, 
                              stock_model = run["stock_model"])
        
    # Minimum annual generation constraint
    if configs["constraints"]["min_annual_generation"]["enable"]:
        constr_min_annual_generation(network, 
                                    lhs_generator = configs["constraints"]["min_annual_generation"]["generator"],
                                    rhs_min_generation = configs["constraints"]["min_annual_generation"]["fraction"])
    
    # Minimum annual link utlisation constraint
    if configs["constraints"]["min_utilisation_links"]["enable"]:
        constr_min_annual_utilisation_links(network,
                                            carriers = configs["constraints"]["min_utilisation_links"]["carriers"])
    
    # Maximum annual link utlisation constraint
    if configs["constraints"]["max_utilisation_links"]["enable"]:
        constr_max_annual_utilisation_links(network,
                                            carriers = configs["constraints"]["max_utilisation_links"]["carriers"])

    # Minimum annual utilisation constraint on a generator level
    if configs["constraints"]["min_utilisation_generator"]["enable"]:
        constr_min_annual_utilisation_generator(network,
                                                carriers = configs["constraints"]["min_utilisation_generator"]["carriers"])
    
    # Maximum annual utilisation constraint on a generator level
    if configs["constraints"]["max_utilisation_generator"]["enable"]:
        constr_max_annual_utilisation_generator(network,
                                                carriers = configs["constraints"]["max_utilisation_generator"]["carriers"])

    # Maximum annual utilisation constraint
    if configs["constraints"]["max_utilisation"]["enable"]:
        constr_max_annual_utilisation(network, 
                                      max_utilisation = configs["constraints"]["max_utilisation"]["fraction"],
                                      carriers = configs["constraints"]["max_utilisation"]["carriers"])

    # Cofiring CCS generation constraint
    if configs["constraints"]["cofiring_ccs_gen"]["enable"]:
        constr_cofiring_ccs_generation_join_plant(network, 
                                                clean_generator = configs["constraints"]["cofiring_ccs_gen"]["clean_generator"],
                                                fossil_generator = configs["constraints"]["cofiring_ccs_gen"]["fossil_generator"])
    
    return network