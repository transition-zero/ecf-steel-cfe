import pypsa
import logging
import pandas as pd

logging.basicConfig(level=logging.CRITICAL + 1)
logging.getLogger("gurobipy").disabled = True
logging.getLogger("linopy").disabled = True
logging.getLogger("pypsa").disabled = True

def MakeNetwork():

    n = pypsa.Network()

    # snapshots
    n.set_snapshots(range(4))

    # carriers
    n.add("Carrier", "Dirty", co2_emissions=0.2)
    n.add("Carrier", "Clean", co2_emissions=0.0)

    # add bus
    n.add("Bus", "AnyTown Grid", v_nom=20.)
    n.add("Bus", "C&I Grid", v_nom=20.)
    n.add("Bus", "C&I Storage", v_nom=20.)

    # add demands
    n.add("Load", "AnyTown Load", bus="AnyTown Grid", p_set=[6,6,6,6])
    n.add("Load", "C&I Load", bus="C&I Grid", p_set=[2,5,3,1])

    # add generators
    n.add(
        "Generator", 
        "AnyTown Dirty Gen", 
        bus="AnyTown Grid", 
        carrier="Dirty",
        p_nom=10, 
        marginal_cost=10, 
        capital_cost=1e6, 
        p_nom_extendable=True
    )

    n.add(
        "Generator", 
        "AnyTown Clean Gen", 
        bus="AnyTown Grid", 
        carrier="Clean",
        p_nom=10, 
        marginal_cost=15, 
        capital_cost=1e6, 
        p_max_pu=[1,1,0,0], 
        p_nom_extendable=True
    )

    n.add(
        "Generator", 
        "C&I PPA", 
        bus="C&I Grid",
        carrier="Clean",
        p_nom=0, 
        marginal_cost=15, 
        capital_cost=1e6, 
        p_max_pu=[0.8,0.,0.3,0.7], 
        p_nom_extendable=True,
    )

    # add storage
    n.add(
        "StorageUnit",
        "C&I PPA Storage",
        bus="C&I Storage",
        p_nom=0,
        p_nom_extendable=True,
        cyclic_state_of_charge=True,
        capital_cost=1e9,
        marginal_cost=0,
        max_hours=4,
        efficiency_store=0.9,
        efficiency_dispatch=0.9,
    )

    # add links
    n.add(
        "Link",
        "C&I ImportFromAnyTown",
        bus0="AnyTown Grid", 
        bus1="C&I Grid", 
        p_nom=1e6,
        marginal_cost=1,
    )

    n.add(
        "Link",
        "C&I ExportToAnyTown",
        bus0="C&I Grid", 
        bus1="AnyTown Grid", 
        p_nom=1e6,
        marginal_cost=1,
    )

    n.add(
        "Link",
        "PPA_StorageCharge",
        bus0="C&I Grid", 
        bus1="C&I Storage", 
        p_nom=0,
        p_nom_extendable=True,
        marginal_cost=1,
    )

    n.add(
        "Link",
        "PPA_StorageDischarge",
        bus0="C&I Storage", 
        bus1="C&I Grid", 
        p_nom=0,
        p_nom_extendable=True,
        marginal_cost=1,
    )

    return n

brownfield = MakeNetwork()
# optimise
brownfield.optimize(solver_name='gurobi', solver_options={'log_to_console': False})

res_100 = MakeNetwork()

res_100.optimize.create_model()

# add 100% RES constraint
sum_ci_load = res_100.loads_t.p_set['C&I Load'].sum()

sum_ppa_procured = (
    res_100
    .model
    .variables['Generator-p']
    .sel(
        Generator='C&I PPA'
        )
    .sum()
)

res_100.model.add_constraints(
    sum_ppa_procured >= sum_ci_load,
    name = '100_RES_constraint',
)

res_100.optimize.solve_model(solver_name='gurobi', solver_options={'log_to_console': False})

cfe = MakeNetwork()

cfe.optimize.create_model()

CFE_TARGET = 0.9
MAXIMUM_EXCESS = 0.2

# Constraint 1: Hourly matching
#   CI_Demand[t] + PPA_StorageCharge[t] - PPA_StorageDischarge[t] = PPA[t] - Excess[t] + GridSupply[t]

CI_Demand = cfe.loads_t.p_set['C&I Load'].values
CI_StorageCharge = cfe.model.variables['Link-p'].sel(Link='PPA_StorageCharge')
CI_StorageDischarge = cfe.model.variables['Link-p'].sel(Link='PPA_StorageDischarge')
CI_PPA = cfe.model.variables['Generator-p'].sel(Generator='C&I PPA')
CI_Export = cfe.model.variables['Link-p'].sel(Link='C&I ExportToAnyTown')
CI_GridImport = cfe.model.variables['Link-p'].sel(Link='C&I ImportFromAnyTown')

cfe.model.add_constraints(
    ((CI_StorageCharge - CI_StorageDischarge) + CI_Demand) == CI_PPA - CI_Export + CI_GridImport,
    name = 'Hourly_matching_constraint',
)

# Constraint 2: CFE target
#   SUM( PPA[t] - Excess[t] + GridSupply[t]*GridCFE[t] ) / SUM( CI_Demand[t] ) >= CFE_target

GRID_CFE = (brownfield.generators_t.p['AnyTown Clean Gen'] / brownfield.generators_t.p['AnyTown Dirty Gen']).values

cfe.model.add_constraints(
    (CI_PPA - CI_Export + CI_GridImport * list(GRID_CFE)).sum() >= ((CI_StorageCharge - CI_StorageDischarge) + CI_Demand).sum() * CFE_TARGET,
    name = 'CFE_target_constraint',
)


# Constraint 3: Total excess
cfe.model.add_constraints(
    CI_Export.sum() <= sum(CI_Demand) * MAXIMUM_EXCESS,
    name = 'total_excess_constraint',
)

cfe.optimize.solve_model(solver_name='gurobi', solver_options={'log_to_console': False})