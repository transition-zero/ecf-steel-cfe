<div style="display: flex; justify-content: space-around; align-items: center;">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://github.com/transition-zero/tza-google-cfe/blob/main/img/logo.png">
    <img alt="TransitionZero Logo" width="800 px" src="https://github.com/transition-zero/tza-google-cfe/blob/main/img/logo.png">
  </picture>
</div>

<!-- height="50px" width="300px" -->

# System-level impacts of 24/7 Carbon Free Energy (CFE) in Asia

<!-- badges-begin -->

![Python][python badge]
![Status][status badge]

[python badge]: https://img.shields.io/badge/python_version-3.11-green
[status badge]: https://img.shields.io/badge/Status-Under_Construction-orange

<!-- badges-end -->

## Background
As climate change intensifies the push for global decarbonization of power systems, many organisations increasingly rely on renewable energy through Power Purchase Agreements (PPAs), which traditionally balance supply and demand over long periods. However, some energy buyers now seek 24/7 carbon-free electricity (also referred to as 24/7 CFE), ensuring every kilowatt-hour is continuously sourced from clean energy. Yet, more modelling studies are needed to explore the feasibility, costs, and impacts of 24/7 CFE at scale in the commercial and industrial (C&I) sector.

## Our study
The purpose of this project is to study the feasibility, costs, and impacts of 24/7 CFE in the commercial and industrial (C&I) sector in five distinct geographies. These are:

1. India
2. Japan
3. Taiwan
4. Malaysia
5. Singapore

Our study employs energy system modelling using the widely adopted [PyPSA](https://github.com/PyPSA/PyPSA) framework. In doing so, we create in almost all cases the first openly available PyPSA models for each of the geographies listed above. In addition, to emphasise transparency and reproducibility, we make our entire workflow accessible on Github, and provide all results, visualizations, and compiled analyses openly.

## Reproducing this work

### Getting started

You can clone the repository using the `git` command line

```bash
git clone https://github.com/transition-zero/tza-google-cfe
```

You can set up the project environment using either `uv` or `mamba`. Following the instructions below to get started. 

Using `uv`:

Create a virtual environment:
```bash
uv venv
```

Activate the virtual environment: 
On macOS/Linux: 
```bash 
source .venv/bin/activate
```
On Windows 
```bash 
.venv\Scripts\activate
```

Install depedencies: 
```bash 
uv sync
```

Using `mamba`: 
```bash
mamba env create -f environment.yaml
```

Activate the environment 
```bash
mamba activate tza-cfe
```

### Running CFE models
if using `uv`:
- To build brownfield models:
```bash 
uv run python main.py build-brownfield --config configs.yaml
```
- To solve the brownfield models:
```bash 
uv run python main.py solve-brownfield --config configs.yaml
```
- To run the full CFE scenarios:
```bash 
uv run python main.py run-full-cfe --config configs.yaml
```

if using `mamba`:
The same except ommit `uv run` 
```bash
python main.py build-brownfield --config configs.yaml
```

You can control which scenarios you want to run using the `configs.yaml` inside the `run` directory.
Example config files are provided for each country explored in this CFE project (e.g. for Japan an example for Hokkaido (JPN01) is provided and can be used as a template for running any/all other nodes in Japan).

In the config files provided, HiGHS - an open source linear optimisation solver - is currently set as the optimisation engine for solving each stock model. In the CFE project, Gurobi was also used and parameters are also provided in each config file.

### Want to use, develop or support this project?
We strongly welcome anyone interested in collaborating on this or future related projects. If you have any ideas, suggestions or encounter problems, feel invited to file issues or make pull requests on GitHub. To discuss ideas for the project, please contact [@Abhishek Shivakumar](mailto:abhishek@transitionzero.org).

## Acknowledgements

We gratefully acknowledge the contributions of colleagues across TransitionZero — both current and former — who supported this work through
communications, analysis, modelling infrastructure, and operational coordination. These include Alice Apsey, Ollie Bell, Duncan Byrne, Khandekar
Mahammad Galib, Matthew Gray, Michael Guzzardi, Tim Haines, Anna Hartley, John Heal, Simone Huber, Thomas Kouroughli, Alex Luta, Aman Majid, Grace Mitchell, Irfan Mohamed, Calvin Nesbitt, Joe O’Connor, Sabina Parvu, Handriyanti Diah Puspitarini, Abhishek Shivakumar, Stephanie Stevenson, Isabella Söldner-Rembold, Isabella Suarez, Dan Welsby, and Thu Vu.

This work was made possible through the funding from Google.org.

Our methodological approach is focused on the assessment of system-level costs and benefits of 24/7 Carbon-Free Electricity (CFE) procurement in Japan, India, Singapore, Taiwan, and Malaysia.

It builds on a robust body of literature and cutting-edge modelling tools. In particular we were influenced by,

- TU Berlin and affiliated researchers:
  - Riepin, I., & Brown, T. (2022). System-level impacts of 24/7 carbon-free electricity procurement in Europe. Zenodo. https://doi.org/10.5281/zenodo.7180098
  - Riepin, I., & Brown, T. (2023). The value of space-time load-shifting flexibility for 24/7 carbon-free electricity procurement. Zenodo. https://doi.org/10.5281/zenodo.8185850

- Princeton University (ZERO Lab):
  - Xu, Q.,Manocha, A.,Patankar, N., and Jenkins, J.D., System-level Impacts of 24/7 Carbon-free Electricity Procurement, Zero-carbon Energy Systems Research and Optimization Laboratory, Princeton University, Princeton, NJ, 16 November 2021.
  - Xu, Q., & Jenkins, J. D. (2022). Electricity System and Market Impacts of Time-based Attribute Trading and 24/7 Carbon-free Electricity Procurement. Zenodo. https://doi.org/10.5281/zenodo.7082212

- International Energy Agency (IEA):
  - Regional insights and sectoral analyses
  - IEA (2022), Advancing Decarbonisation through Clean Electricity Procurement, IEA, Paris. https://www.iea.org/reports/advancing-decarbonisation-through-clean-electricity-procurement

Our in-house modelling leverages PyPSA (Python for Power System Analysis), an open-source framework for simulating and optimizing energy systems. This platform enables high-resolution, hourly modelling of decarbonised power systems, adapted for our country-specific analyses. We are grateful to all contributors in the open modelling community, whose tools and insights strengthen the analytical foundation for achieving global CFE goals.

