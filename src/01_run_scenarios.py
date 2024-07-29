from tz_pypsa import (
    plotting,
    constraints,
    wrangle,
)

from tz_pypsa import constraints
from tz_pypsa.model import Model

network = (
    Model.load_model(
        'ASEAN', 
        frequency = '24h',
        #select_nodes=['SGPXX'], 
        years=[2023],
        backstop=False,
        set_global_constraints=False,
    )
)

# constraints.constr_hourly_matching(
#     network,
#     lhs_generators = 'SGP',
#     rhs_min_generation =
# )

try:
    network.optimize.solve_model(
        solver_name='gurobi',
    )
except:
    network.optimize(
        solver_name='gurobi',
        #solver_options={ 'solver': 'pdlp' },
        #multi_year_investment=True,
    )

network.generators_t.p.to_csv('../outputs/data_tables/timeseries_generation.csv', index=True)
network.export_to_netcdf('../outputs/solved_networks/test.nc')
