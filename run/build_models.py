import sys

sys.path.append("../")


from src import brownfield, helpers


def build_brownfield_network(run, configs) -> None:
    brownfield_network = brownfield.SetupBrownfieldNetwork(run, configs)
    run_name = run["name"]
    brownfield_network.export_to_netcdf(f"networks/brownfield/{run_name}.nc")


if __name__ == "__main__":
    # get config file
    configs = helpers.load_configs("configs.yaml")
    ci_identifier = configs["global_vars"]["ci_label"]
    scenarios = {}
    for run in configs["model_runs"]:

        # setup a directory for brownfield models
        helpers.setup_dir(path_to_dir=configs["paths"]["brownfield_models"])

        print("Running: " + run["name"])
        build_brownfield_network(run, configs)
