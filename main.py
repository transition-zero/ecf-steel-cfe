import click
import os
from src import brownfield, helpers, postprocess
from run.run_scenarios import RunBrownfieldSimulation, RunCFE
import pypsa


def build_brownfield_network(run, configs) -> None:
    """
    Builds and exports a brownfield network based on the provided run configuration.
    Args:
        run (dict): A dictionary containing the run configuration, including the name of the run.
        configs (dict): A dictionary containing various configuration settings, including paths.
    Returns:
        None
    """

    brownfield_network = brownfield.SetupBrownfieldNetwork(run, configs)
    run_name = run["name"]
    output_dir = os.path.join(configs["paths"]["brownfield_models"])
    os.makedirs(output_dir, exist_ok=True)
    brownfield_network.export_to_netcdf(os.path.join(output_dir, f"{run_name}.nc"))


def solve_brownfield_network(run, configs) -> pypsa.Network:
    """
    Sets up and optimizes a brownfield network.
    Parameters:
    run (str): The identifier for the run configuration.
    configs (dict): A dictionary containing configuration parameters.
    Returns:
    pypsa.Network: The optimized brownfield network.
    """

    brownfield_network = brownfield.SetupBrownfieldNetwork(run, configs)
    brownfield_network.optimize()
    return brownfield_network


def run_scenarios(configs):
    for run in configs["model_runs"]:
        print(f"Running: {run['name']}")
        N_BROWNFIELD = RunBrownfieldSimulation(run, configs)
        for CFE_Score in run["cfe_score"]:
            print(f"Computing hourly matching scenario (CFE: {int(CFE_Score*100)}...")
            RunCFE(N_BROWNFIELD, CFE_Score=CFE_Score)
        path_to_run_dir = os.path.join(
            configs["paths"]["output_model_runs"], run["name"]
        )
        postprocess.plot_results(path_to_run_dir)
    print("*" * 100)


@click.group()
def cli():
    pass


@cli.command()
@click.option("--config", default="configs.yaml", help="Path to the configuration file")
def build_brownfield(config):
    """
    Builds brownfield models based on the provided configuration.
    This function loads the configuration settings, sets up the necessary directories,
    and builds the brownfield network for each model run specified in the configuration.
    Args:
        config (str): Path to the configuration file.
    Returns:
        None
    """

    configs = helpers.load_configs(config)
    for run in configs["model_runs"]:
        helpers.setup_dir(path_to_dir=configs["paths"]["brownfield_models"])
        build_brownfield_network(run, configs)


@cli.command()
@click.option("--config", default="configs.yaml", help="Path to the configuration file")
def solve_brownfield(config):
    """
    Solves the brownfield network problem based on the provided configuration.
    Args:
        config (str): Path to the configuration file.
    Returns:
        None
    """

    configs = helpers.load_configs(config)
    for run in configs["model_runs"]:
        run_name = run["name"]
        output_dir = os.path.join(configs["paths"]["output_model_runs"])
        os.makedirs(output_dir, exist_ok=True)
        solved_brownfield_network = solve_brownfield_network(run, configs)
        solved_brownfield_network.export_to_netcdf(
            os.path.join(output_dir, f"{run_name}.nc")
        )
        print(os.path.join(output_dir, f"{run_name}.nc"))


@cli.command()
@click.option("--config", default="configs.yaml", help="Path to the configuration file")
def run_full_cfe(config):
    configs = helpers.load_configs(config)
    run_scenarios(configs)


if __name__ == "__main__":
    cli()
