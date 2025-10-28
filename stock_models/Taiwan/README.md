# TZ-Analysis-PyPSA: Taiwan
This folder contains the csv files used to create a PyPSA model for Taiwan.

PyPSA-Taiwan is an hourly-resolution power sector model. It can be used for:

- Dynamic dispatch modelling of power systems.
- Market pricing and intervention analysis.
- Power system capacity expansion planning.

## Overview
The PyPSA-Taiwan is a single-node model representing the national Taiwanese power grid, assuming electricity generated at any location can be transmitted seamlessly to any demand centre. This simplification is supported by the fully interconnected nature of the regional grids, with the central region serving as the primary hub for transmission across the island. 

The model is configured to run a 2030 dispatch year and calibrated using 2024 dispatch data.

## Model configuration

### Temporal resolution
PyPSA-Taiwan runs at an hourly resolution (i.e., 8760 timesteps). Other temporal resolutions are currently not supported.

### Data sources

- **Thermal, hydro and renewable plant capacities**: [Taiwan Ministry of Economic Affairs (MOEA) Energy Statistics database](https://www.esist.org.tw/). Pipeline plants for 2030 are projected based on MOEA’s announced targets, adjusted conservatively to reflect historical build rates.
- **Solar and hydro capacity factors**: Purchased from third-party vendor, [Electricity Maps](https://www.electricitymaps.com/). Historical 2024 factors used for 2024 calibration.
- **Onshore and offshore wind capacity factors**: Scraped from [Taiwan Department of Energy Official Tableau Dashboard](https://public.tableau.com/app/profile/doenergy/viz/22345/1_1). Any gap is supplemented by [Renewables.ninja]([https://public.tableau.com/app/profile/doenergy/viz/22345/1_1](https://www.renewables.ninja/)) and calibrated to the monthly capacity factor level observed in the same year from [Taiwan Energy Statistics](https://www.esist.org.tw/). Historical 2024 factors used for 2024 calibration.
- **Cogeneration capacity factors**: Purchased from third-party vendor, [Electricity Maps](https://www.electricitymaps.com/). Historical 2024 factors used for 2024 calibration
- **Biomass/geothermal capacity factors**: Purchased from third-party vendor, [Electricity Maps](https://www.electricitymaps.com/). Historical 2024 annual utilisation rates sued for biomass and geothermal, reflecting their relatively stable
generation patterns.
- **Technology costs**: Historical data sourced from the annual Feed-in Tariff (FiT) committee meetings, available [here](https://www.moeaea.gov.tw/ECW/renewable/content/ContentLink.aspx?menu_id=778) and MOEA MOEA 2023 Annual Business Plan, available [here](https://www.moea.gov.tw/mns/CNC/content/wHandMenuFile.ashx?file_id=34543). For the year 2030, Japanese government’s most recent technology cost projections are employed as proxy to Taiwanese cost estimates.
- **Commodity prices**: Historical commodity prices are sourced from [Taiwan’s MOEA Energy Statistics database](https://www.esist.org.tw/), while IEA coastal China cost projections are used as proxies for Taiwanese 2030 cost estimates.
- **2030 demand**: Total demand in 2030 is taken from [2023 National Power Resources Supply and Demand Report](https://www.moeaea.gov.tw/ECW/populace/news/News.aspx?kind=1&menu_id=41&news_id=33815) from the MOEA. Demand curves have been scaled up linearly, with the demand shape remaining the same.
