# TZ-Analysis-PyPSA: Japan
This folder contains the csv files used to create a PyPSA model for Japan.

PyPSA-Japan is an hourly-resolution power sector model. It can be used for:

- Dynamic dispatch modelling of power systems.
- Market pricing and intervention analysis.
- Power system capacity expansion planning.

## Overview
The PyPSA-Japan model is comprised of 9 nodes and 10 inter grid-zone links (represented as individual uni-directional interconnectors, therefore resulting in 20 links). Here, each node represents a regional power grid in the Japan National Grid, while each link represents the aggregated transmissions capacity between grid regions.

The model is setup to run a 2030 dispatch and capacity expansion model for a reference (brownfield) scenario and a set of CFE (carbon-free electricity) scenarios. The model was calibrated for 2023 before these 2030 scenarios were explored and some of those constraints are in place to a certain degree (e.g. maximum utilisation rates on coal plants informed by historical generation levels). 

## Model configuration

### Geographical scope
The 9 grid zones are as follows:

Grid zone       | Code
---             | ---                  
Hokkaido        | JPN01     
Tohoku          | JPN02   
Tokyo           | JPN03   
Chubu           | JPN04   
Hokuriku        | JPN05
Kansai          | JPN06
Chugoku         | JPN07
Shikoku         | JPN08
Kyushu          | JPN09                      

### Temporal resolution
PyPSA-Japan runs at an hourly resolution (i.e., 8760 timesteps). Other temporal resolutions are currently not supported.

### Data sources

For input data sources included in the PyPSA-Japan model please refer to the main Japan CFE modelling report by Transition Zero: Modelling 24/7 Carbon Free
Electricity (CFE) in Asia - Results for Japan (https://blog.transitionzero.org/hubfs/Analysis/CFE%20Reports/TransitionZero%20-%2024-7%20CFE%20-%20Report%20-%20Japan%20(English).pdf).

### Policy targets
In the Japan model used in the CFE project we do not include any policy targets (whether that be RE targets or emissions budgets as part of the Nationally Determined Contributions (NDCs))