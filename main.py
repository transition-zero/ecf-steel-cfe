import os

import click
import pypsa

from tz_pypsa.constraints import (
    constr_cumulative_p_nom,
    constr_bus_self_sufficiency,
    constr_policy_targets,
    constr_max_annual_utilisation
)

from run.run_scenarios import RunBrownfieldSimulation, RunCFE, RunRES100
from src import brownfield, cfe, helpers, postprocess


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


def solve_brownfield_network(run, configs, with_cfe: bool) -> pypsa.Network:
    """
    Sets up and optimizes a brownfield network.
    Parameters:
    run (str): The identifier for the run configuration.
    configs (dict): A dictionary containing configuration parameters.
    Returns:
    pypsa.Network: The optimized brownfield network.
    """

    tza_brownfield_network = brownfield.SetupBrownfieldNetwork(run, configs)
    if with_cfe:
        final_brownfield = cfe.PrepareNetworkForCFE(
            tza_brownfield_network,
            buses_with_ci_load=run["nodes_with_ci_load"],
            ci_load_fraction=run["ci_load_fraction"],
            technology_palette=configs["technology_palette"][run["palette"]],
            p_nom_extendable=False,
        )
    else:
        final_brownfield = tza_brownfield_network
    # final_brownfield.optimize(solver_name=configs["global_vars"]["solver"])

    # lp_model = final_brownfield.optimize.create_model()

    final_brownfield.optimize.create_model()

    # BUS SELF SUFFICIENCY CONSTRAINT
    constr_bus_self_sufficiency(final_brownfield, 
                                min_self_sufficiency = 0.6)

    # FOSSIL FUEL UTILIZATION RATE CONSTRAINT (AVAILABILITY FACTOR)
    constr_max_annual_utilisation(final_brownfield, 
                                  max_utilisation_rate = 0.85, 
                                  carriers = ['coal','gas','oil','geothermal'])

    # CONSTRAINTS FROM TARGETS AND POLICIES SHEET
    constr_policy_targets(final_brownfield, 
                          stock_model = run["stock_model"])

    final_brownfield.optimize.solve_model(solver_name=configs["global_vars"]["solver"])

    return final_brownfield


def run_scenarios(configs):
    for run in configs["model_runs"]:
        helpers.setup_dir(
            path_to_dir=configs["paths"]["output_model_runs"]
            + run["name"]
            + "/solved_networks/"
        )
        print(f"Running: {run['name']}")
        ci_identifier = configs["global_vars"]["ci_label"]
        N_BROWNFIELD = RunBrownfieldSimulation(run, configs)
        RES_TARGET = 100
        print(f"Computing annual matching scenario (RES Target: {int(RES_TARGET)}%)...")
        RunRES100(
            N_BROWNFIELD,
            ci_identifier=ci_identifier,
            run=run,
            res_target=RES_TARGET,
            configs=configs,
        )
        for CFE_Score in run["cfe_score"]:
            print(f"Computing hourly matching scenario (CFE: {int(CFE_Score*100)}...")
            N_BROWNFIELD_original = helpers.load_brownfield_network(run, configs)
            RunCFE(
                N_BROWNFIELD_original,
                CFE_Score=CFE_Score,
                ci_identifier=ci_identifier,
                run=run,
                configs=configs,
            )
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
@click.option("--with_cfe", default=False, help="Include CFE components in the model")
def build_brownfield(config, with_cfe: bool):
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
@click.option("--with-cfe", default=True, help="Include CFE components in the model")
def solve_brownfield(config, with_cfe: bool):
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
        solved_brownfield_network = solve_brownfield_network(run, configs, with_cfe)
        solved_brownfield_network.export_to_netcdf(
            os.path.join(output_dir, f"{run_name}.nc")
        )
        print(os.path.join(output_dir, f"{run_name}.nc"))


@cli.command()
@click.option("--config", default="configs.yaml", help="Path to the configuration file")
def solve_brownfield_cfe(config):
    """
    Solves the brownfield network problem based on the provided configuration with the added CFE components.
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


@cli.command()
@click.option("--config", default="configs.yaml", help="Path to the configuration file")
def run_plots(
    config,
):
    config = helpers.load_configs(config)
    for run in config["model_runs"]:
        path_to_run_dir = os.path.join(
            config["paths"]["output_model_runs"], run["name"]
        )
        postprocess.plot_results(path_to_run_dir)


if __name__ == "__main__":
    cli()
