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
There are three fundamental constraints for 24/7 CFE. These are itemised below.

**Constraint 1: Hourly matching**

<!-- $$\left( \sum_{k=1}^n a_k b_k \right)^2 \leq \left( \sum_{k=1}^n a_k^2 \right) \left( \sum_{k=1}^n b_k^2 \right)$$ -->

$$D_{i,t} + s_{r,t} - s_{r,t} = g_{r,t} - e_{i,t} + u_{i,t}$$

The hourly matching constraint ensures that the demand $D$ of the commercial and industrial consumer $i$ must be met by clean electricity at any given time step, such that:

<!-- $D_{i,t} + \bar{s}_{r,t} - \underline{s}_{r,t} = g_{r,t} - e_{i,t} + u_{i,t}$ -->

<!-- Demand_t + DemandResponseUp_t - DemandResponseDown_t + ContractedStorageCharge_t - ContractedStorageDispatch_t = TotalContractedCFE_t - Excess_t + GridSupply_t -->

**Constraint 2: Impose CFE target**

**Constraint 3: Set a limit on the excess (exports to grid)**

This sentence uses $\` and \`$ delimiters to show math inline:  $`\sqrt{3x-1}+(1+x)^2`$