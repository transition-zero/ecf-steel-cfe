# A simple model to explain the methodology

## Overview

## System description

<div style="display: flex; justify-content: space-around; align-items: center;">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://github.com/transition-zero/tza-google-cfe/blob/implement-cfe-constr/demo/simple-model.png">
    <img alt="TransitionZero Logo" width="800 px" src="https://github.com/transition-zero/tza-google-cfe/blob/implement-cfe-constr/demo/simple-model.png">
  </picture>
</div>

## Mathematical formulation

### 100% Renewables (i.e., annual matching)

### 24/7 Carbon-free energy procurement (i.e., hourly matching)
There are **three fundamental constraints** that must be imposed in the model to ensure 24/7 CFE for a commercial and industrial customer. These are itemised below.

**Constraint 1: Hourly matching**

The hourly matching constraint ensures that the demand of the commercial and industrial consumer $i$ must be met by clean electricity at any given time step ($t \in T$), such that:

$$Demand_{(i,t)} + StorageCharge_{(r,t)} - StorageDischarge_{(r,t)} = CleanGenProcured_{(r,t)} - Excess_{(i,t)} + GridImport_{(i,t)}$$

where $r$ denotes generation and storage technologies procured by the C&I customer by their PPA ($r \in CFE$). In the above, an excess occurs when the the procured generation exceeeds the demand of the C&I customer, while grid imports occur when the demand of the C&I customer exceeds the supply by the procured portfolio. 

**Constraint 2: Impose CFE target**

The next constraint ensures that the total procurement by the C&I customer meets a defined CFE score ($S^{*}$). This constraint is set as: 

$$
\frac{\sum_{t} \left( CleanGenProcured_{(r,t)} - Excess_{(i,t)} + GridImportCFE_{(i,t)} . GridImport_{(i,t)} \right)}{\sum_{t} \left( Demand_{(i,t)} + StorageCharge_{(r,t)} - StorageDischarge_{(r,t)} \right)} \geq S^{*}
$$

**Constraint 3: Set a limit on the excess (exports to grid)**

An "excess" occurs when the total electricity generation from assets procured by participating consumers exceeds their demand in a given hour. In the model, we assume this excess can either be curtailed or sold to the regional electricity market at wholesale prices. A constraint is set, limiting the amount of excess generation sold to the regional grid to $u=20%$ of the participating consumers' annual demand, such that:

$$
\sum_t Excess_{(i,t)} \leq u . \left( \sum_t Demand_{(i,t)} \right)
$$

The wholesale market prices are based on the dual variables of a nodal energy balance constraint.