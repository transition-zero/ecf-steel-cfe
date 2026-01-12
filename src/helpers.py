import os
import yaml
import pypsa
import pandas as pd


def setup_dir(path_to_dir):
    """
    Creates a directory if it does not already exist.

    Parameters:
    path_to_dir (str): The path to the directory to be created.

    Returns:
    None
    """
    if not os.path.exists(path_to_dir):
        os.makedirs(path_to_dir)


def load_configs(path):
    """
    Load configuration settings from a YAML file.

    Args:
        path (str): The file path to the YAML configuration file.

    Returns:
        dict: A dictionary containing the configuration settings.

    Raises:
        FileNotFoundError: If the specified file does not exist.
        yaml.YAMLError: If there is an error parsing the YAML file.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"The file at {path} does not exist.")
    
    try:
        with open(path, 'r') as file:
            configs = yaml.safe_load(file)
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Error parsing YAML file: {e}")
    
    return configs

def load_brownfield_network(run, configs):
    """
    Load a brownfield network from a specified path for use in the CFE run iterations
    This is to prevent:
        a) modifying the brownfield network in each iteration
        b) avoiding re-solving the brownfield network in each iteration
    """

    brownfield_path = os.path.join(
        configs["paths"]["output_model_runs"],
        run["name"],
        "solved_networks",
        "brownfield_" + str(configs["global_vars"]["year"]) + ".nc",
    )

    brownfield_original = pypsa.Network()
    brownfield_original.import_from_netcdf(brownfield_path)

    return brownfield_original

def calculate_annuity(
        n : int, 
        r : float,
) -> float:
    '''

    Calculate the annuity factor for an asset with lifetime n years and
    discount rate of r, e.g. annuity(20, 0.05) * 20 = 1.6
    
    Inputs:
    -----------------------------------

        n : asset lifetime (years)
        r : discount rate (%, decimal point [e.g., 0.04])

    '''

    if isinstance(r, pd.Series):
        return pd.Series(1/n, index=r.index).where(r == 0, r/(1. - 1./(1.+r)**n))
    elif r > 0:
        return r/(1. - 1./(1.+r)**n)
    else:
        return 1/n