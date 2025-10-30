# TZ-Analysis-PyPSA: ASEAN
This folder contains the input data used to create PyPSA models for Malaysia and Singapore used in the 24/7 Carbon Free Electricity (CFE) modelling study.  

PyPSA-ASEAN is an hourly-resolution power sector model. It can be used for:

- Dynamic dispatch modelling of power systems.
- Market pricing and intervention analysis.
- Power system capacity expansion planning.

Due to interconnections between different countries in the ASEAN bloc, Malaysia and Singapore are modelled along with neighbouring countries (or grid zones of neighbouring countries). However each country (Malaysia and Singapore) can also be modelled in isolation. 

## Overview
The PyPSA-ASEAN model is comprised of 8 nodes and 8 links. Here, each node represents a balancing zone, while each link represents the interconnector capacity between balancing zones.

## Model configuration

### Geographical scope

The model covers a sub-set of the ASEAN region in 8 nodes and 8 links (represented as uni-directional hence 15 links in total given one is only one-way). The geographic and network coverage is shown in the table below.

Country       | Code    | Nodes
---           | ---     | ---
Indonesia     | IDN     | 1
Malaysia      | MYS     | 3
Singapore     | SGP     | 1
Thailand      | THA     | 3


### Temporal resolution
PyPSA-ASEAN runs at an hourly resolution (i.e., 8760 timesteps). 

### Data sources

TBD

### Policy targets
In addition, there is a `power_sector_targets.csv` file to define NDC targets such as emissions and minimum capacity targets for 2030. 

