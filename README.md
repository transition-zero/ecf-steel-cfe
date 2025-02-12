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
You can set up the project environment using either `uv` or `mamba`. Following the instructions below to get started. 

Using `uv`:

Create a virtual environment:
```bash
uv create .venv
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
uv add -r pyproject.toml
```

Using `mamba`: 
```bash
mamba env create -f environment.yaml
```

Activate the environment 
```bash
mamba activate tza-cfe
```

### Running a scenario
To run a scenario you need to: 
```bash
cd run
```
if using `uv`:
```bash 
uv run run_scenario.py
```

if using `mamba`: 
```bash
python run_scenario.py
```

You can control which scenarios you want to run using the `configs.yaml` inside the `run` directory.

### Want to use, develop or support this project?
We strongly welcome anyone interested in collaborating on this or future related projects. If you have any ideas, suggestions or encounter problems, feel invited to file issues or make pull requests on GitHub. To discuss ideas for the project, please contact [@Abhishek Shivakumar](mailto:abhishek@transitionzero.org).

## Similar works
We relied on several excellent previous analyses to do this work. In particular, we were influenced by: 

- Riepin and Brown (2024) On the means, costs, and system-level impacts of 24/7 carbon-free energy procurement ([link](https://doi.org/10.1016/j.esr.2024.101488)).
- TU Berlin's study of 24/7 Carbon-Free Energy procurement in Europe ([link](https://github.com/PyPSA/247-cfe)).
- The Zero Lab's (Princeton University) analysis of electricity System and market impacts of time-based attribute trading and 24/7 carbon-free electricity procurement in the USA ([link](https://acee.princeton.edu/24-7/))

## Licence
TODO