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

The model covers a sub-set of the ASEAN region in 8 nodes and 8 links (represented as uni-directional hence 15 links in total given one does not flow in both directions). The geographic and network coverage is shown in the table below.

Grid zone/nodes                 | Code    
---                     | ---     
Kalimantan Indonesia    | IDNKA     
Malaysia Peninsular     | MYSPE
Malaysia Sarawak        | MYSSK
Malaysia Sabah          | MYSSH    
Singapore               | SGPXX     
Thailand South          | THASO
Thailand North          | THANO
Thailand Central        | THACE


### Temporal resolution
PyPSA-ASEAN runs at an hourly resolution (i.e., 8760 timesteps). Other temporal resolutions are currently not supported.

### Data sources

- **Thermal, hydro and renewable plant capacities**: Existing capacity is pulled from the official reports per country. Pipeline plants for 2030 are compiled from announced projects. 
- **Solar capacity factors**: Historical profile in 2023 from [GSO](https://www.gso.org.my/SystemData/SystemDemand.aspx/) and [NEMS](http://nems.emcsg.com/nems-prices) are used for Malaysia Peninsular and Singapore. [Transition Zero in-house methodology](https://www.transitionzero.org/insights/from-vision-to-voltage-with-tz-apg) is used for other nodes. We assume that future profiles do not change.  
- **Hydro capacity factors**: Historical profile in 2023 from [GSO](https://www.gso.org.my/SystemData/SystemDemand.aspx/) is used for Malaysia Peninsular. [Transition Zero in-house methodology](https://www.transitionzero.org/insights/from-vision-to-voltage-with-tz-apg) is used for other nodes. We assume that future profiles do not change.  
- **Wind capacity factors**: [Transition Zero in-house methodology](https://www.transitionzero.org/insights/from-vision-to-voltage-with-tz-apg) is used for all nodes. We assume that future profiles do not change.
- **Technology costs and technology-specific parameters**: Intensive analysis is done based on Danish Energy Agency Technology Catalogue for [Indonesia](https://gatrik.esdm.go.id/assets/uploads/download_index/files/c4d42-technology-data-for-the-indonesian-power-sector-2024-annoteret-af-kb-.pdf) and for [Vietnam](https://ens.dk/en/global-coorporation/energy-partnerships/vietnam), [Malaysia Technology Cost by BNEF](https://assets.bbhub.io/professional/sites/24/Malaysia-A-Techno-Economic-Analysis-of-Power-Generation.pdf) and [The 8th ASEAN Energy Outlook by ACE](https://aseanenergy.org/wp-content/uploads/2024/09/8th-ASEAN-Energy-Outlook.pdf) to determine costs per technology in 2030. Due to limited information for Gas-CCS in ASEAN, technology cost projection from Japanese government is employed. 
- **Coal prices**: Compiled from quarterly analyst briefings of Tenaga Nasional Berhad, annual report of Sarawak Energy Berhad official reports and projections and [Transition Zero in-house methodology](https://www.transitionzero.org/insights/from-vision-to-voltage-with-tz-apg). 
- **Gas and oil prices**: Pulled from Transition Zero in-house methodology done for [TZ-APG](https://www.transitionzero.org/insights/from-vision-to-voltage-with-tz-apg).
- **Hydrogen prices**: Determined based on [IEA STEPS supply cost curve](https://iea.blob.core.windows.net/assets/89c1e382-dc59-46ca-aa47-9f7d41531ab5/GlobalHydrogenReview2024.pdf).
- **Ammonia prices**: Determined based on [Malaysia Technology Cost by BNEF](https://assets.bbhub.io/professional/sites/24/Malaysia-A-Techno-Economic-Analysis-of-Power-Generation.pdf).
- **2030 demand**: Demand growth assumptions differ by region, considering the pace of economic expansion and targeted increases in C&I. Growth rates of 3-8% are used specifically for Malaysia and Singapore nodes in line with national projections. [Transition Zero in-house methodology](https://www.transitionzero.org/insights/from-vision-to-voltage-with-tz-apg) is used for projecting 2030 demand. 
- **Transmission capacity**: Compiled from existing capacity and announced projects listed for all nodes. 

### Policy targets
In addition, there is a `power_sector_targets.csv` file to define NDC targets such as emissions and minimum capacity targets for 2030. 

