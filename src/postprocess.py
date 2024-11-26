import os

import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

from matplotlib.ticker import MaxNLocator

from . import plotting as cplt
from . import get as cget

from . import postprocess_plotting

def plot_results(path_to_run_dir: str):
    '''Plot results for a given run
    '''

    # set tz plotting theme
    cplt.set_tz_theme()
    cplt.set_tz_theme()

    # make results dir if it doesn't exist
    if not os.path.exists(os.path.join(path_to_run_dir, 'results')):
        os.makedirs(os.path.join(path_to_run_dir, 'results'))

    # load solved networks
    solved_networks = (
        cget.load_from_dir(
            os.path.join(
                path_to_run_dir, 'solved_networks'
            )
        )
    )

    # ------------------------------------------------------------------
    # C&I Portfolio Capacity [GW]

    fig, ax0, ax1 = cplt.bar_plot_2row(width_ratios=[1,10], figsize=(10,4))

    expanded_capacity = (
        pd.concat(
            [
                solved_networks[k]
                .statistics.expanded_capacity()
                .reset_index()
                .rename(columns={0:'capacity'})
                .assign(name=k) 
                for k, n in solved_networks.items()
            ]
        )
        .pipe(
            cget.split_scenario_col,
            'name',
        )
        .drop('name', axis=1)
    )

    # pull out relevant data
    res = (
        expanded_capacity
        .loc[expanded_capacity['Scenario'] == '100% RES']
        .drop(['Scenario','CFE Score'], axis=1)
        .query(" ~carrier.isin(['Transmission']) ")
        .pivot_table(columns='carrier', values='capacity')
        .div(1e3)
        .rename(index={'capacity':'100% RES'})
    )

    cfe = (
        expanded_capacity
        .query("Scenario.str.contains('CFE')")
        .sort_values('CFE Score')
        .query(" ~carrier.isin(['Transmission']) ")
        .pivot_table(index='CFE Score', columns='carrier', values='capacity')
        .div(1e3)
    )

    colors = cplt.tech_color_palette()

    res.plot(kind='bar', stacked=True, ax=ax0, legend=False, color=[colors.get(x, '#333333') for x in res.columns])
    cfe.plot(kind='bar', stacked=True, ax=ax1, legend=True, color=[colors.get(x, '#333333') for x in cfe.columns])

    ax0.set_ylabel('C&I procured portfolio [GW]')
    ax1.set_xlabel('CFE Score [%]')

    for ax in [ax0, ax1]:
        ax.set_xticklabels(ax.get_xticklabels(), rotation=0)
        ax.yaxis.grid(True, linestyle=':', linewidth=0.5)
        sns.despine(ax=ax, left=False)

    # Remove legend title and box
    legend = ax1.legend()
    legend.set_title(None)
    legend.get_frame().set_linewidth(0)

    # Adjust horizontal space between ax0 and ax1
    fig.subplots_adjust(wspace=0.1)

    # save
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/ci_capacity_by_scenario.png'
        ),
        bbox_inches='tight'
    )

    # ------------------------------------------------------------------
    # EMISSIONS

    emissions = (
        pd
        .DataFrame({
            'name' : [k for k in solved_networks.keys()],
            'emission' : [cget.get_emissions(n) for n in solved_networks.values()]
        })
        .pipe(
            cget.split_scenario_col,
            'name',
        )
    )

    baseline = emissions.loc[emissions['name'] == 'n_bf', 'emission'].values[0]
    emissions['relative_emission'] = ( (emissions['emission'] - baseline) / baseline)*100

    fig, ax0, ax1 = cplt.bar_plot_2row(width_ratios=[1,10], figsize=(10,4))

    res = (
        emissions
        .loc[emissions['Scenario'] == '100% RES']
        .pivot_table(index='Scenario', values='relative_emission')
        .reset_index()
    )

    cfe = (
        emissions
        .loc[emissions['Scenario'].str.contains('CFE')]
        .pivot_table(index='CFE Score', values='relative_emission')
        .reset_index()
    )

    res.plot(kind='scatter', x='Scenario', y='relative_emission', ax=ax0, s=50)
    cfe.plot(kind='scatter', x='CFE Score', y='relative_emission', ax=ax1, s=50)

    for ax in [ax0, ax1]:
        ax.yaxis.grid(True, linestyle=':', linewidth=0.5)
        sns.despine(ax=ax, left=False)

    ax0.set_ylabel('Emission Reduction [%]')
    ax1.set_ylabel('')

    ax0.set_xlabel('')
    ax1.set_xlabel('CFE Score [%]')
    
    # save plot
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/emissions_by_scenario.png'
        ),
        bbox_inches='tight'
    )

    # ------------------------------------------------------------------
    # EMISSION RATE

    emissions = (
        pd
        .DataFrame({
            'name' : [k for k in solved_networks.keys()],
            'emission' : [cget.get_emissions(n) for n in solved_networks.values()],
            'generation' : [solved_networks[k].statistics.energy_balance().loc['Generator'].sum() for k in solved_networks.keys()],
        })
        .pipe(
            cget.split_scenario_col,
            'name',
        )
    )

    emissions['emission_rate'] = (emissions['emission'] / emissions['generation']) * 1000 # tCO2 / MWh -> gCO2 / kWh

    fig, ax0, ax1, ax2 = cplt.bar_plot_3row(width_ratios=[1,1,10], figsize=(10,4))

    ref = (
        emissions
        .loc[emissions['Scenario'] == 'Reference']
        .pivot_table(index='Scenario', values='emission_rate')
        .reset_index()
    )

    res = (
        emissions
        .loc[emissions['Scenario'] == '100% RES']
        .pivot_table(index='Scenario', values='emission_rate')
        .reset_index()
    )

    cfe = (
        emissions
        .loc[emissions['Scenario'].str.contains('CFE')]
        .pivot_table(index='CFE Score', values='emission_rate')
        .reset_index()
    )

    ref.plot(kind='bar', x='Scenario', y='emission_rate', ax=ax0, legend=False)
    res.plot(kind='bar', x='Scenario', y='emission_rate', ax=ax1, legend=False)
    cfe.plot(kind='bar', x='CFE Score', y='emission_rate', ax=ax2, legend=False)

    for ax in [ax0, ax1, ax2]:
        ax.yaxis.grid(True, linestyle=':', linewidth=0.5)
        sns.despine(ax=ax, left=False)
        ax.set_xticklabels(ax.get_xticklabels(), rotation=0)

    ax0.set_ylabel('Emission Rate [gCO$_2$ kWh$^{-1}$]')
    ax1.set_ylabel('')
    ax2.set_ylabel('')

    ax0.set_xlabel('')
    ax1.set_xlabel('')
    ax2.set_xlabel('CFE Score [%]')

    # save plot
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/emission_rate_by_scenario.png'
        ),
        bbox_inches='tight'
    )

    # ------------------------------------------------------------------
    # C&I EMISSION RATE

    ci_emissions = (
        pd
        .DataFrame({
            'name' : [k for k in solved_networks.keys()],
            'load' : [solved_networks[k].loads_t.p_set.filter(regex='C&I').sum().sum() for k in solved_networks.keys()],
            'emissions' : [
                np.sum(
                    solved_networks[k].links_t.p0.filter(regex='C&I').filter(regex='Import').values.flatten() @ np.array(cget.GetGridCFE(solved_networks[k], ci_identifier='C&I'))
                ) 
                for k in solved_networks.keys()
            ],
        })
        .pipe(
            cget.split_scenario_col,
            'name',
        )
    )

    ci_emissions['emission_rate'] = (ci_emissions['emissions'] / ci_emissions['load']) * 1000 # tCO2 / MWh -> gCO2 / kWh

    fig, ax0, ax1 = cplt.bar_plot_2row(width_ratios=[1,10], figsize=(10,4))

    res = (
        ci_emissions
        .loc[ci_emissions['Scenario'] == '100% RES']
        .pivot_table(index='Scenario', values='emission_rate')
        .reset_index()
    )

    cfe = (
        ci_emissions
        .loc[ci_emissions['Scenario'].str.contains('CFE')]
        .pivot_table(index='CFE Score', values='emission_rate')
        .reset_index()
    )

    res.plot(kind='bar', x='Scenario', y='emission_rate', ax=ax0, legend=False)
    cfe.plot(kind='bar', x='CFE Score', y='emission_rate', ax=ax1, legend=False)

    for ax in [ax0, ax1]:
        ax.yaxis.grid(True, linestyle=':', linewidth=0.5)
        sns.despine(ax=ax, left=False)
        ax.set_xticklabels(ax.get_xticklabels(), rotation=0)

    ax0.set_ylabel('Emission Rate [gCO$_2$ kWh$^{-1}$]')
    ax1.set_ylabel('')

    ax0.set_xlabel('')
    ax1.set_xlabel('CFE Score [%]')

    # save plot
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/ci_emission_rate_by_scenario.png'
        ),
        bbox_inches='tight'
    )


    # ------------------------------------------------------------------
    # TOTAL SYSTEM COSTS BY SCENARIO 
    # > REF, 100% RES, CFE

    # stacked bar plot
    costs = (
        pd.concat(
            [
                cget
                .get_total_annual_system_cost(solved_networks[k])
                .assign(name=k)
                for k, n in solved_networks.items()
            ]
        )
        .pipe(
            cget.split_scenario_col,
            'name',
        )
        .drop('name', axis=1)
    )

    costs = costs.query(" ~carrier.isin(['Transmission', '-']) ").reset_index(drop=True)

    fig, ax0, ax1, ax2 = cplt.bar_plot_3row(figsize=(10,4), width_ratios=[1,1,10])

    # get relevant data
    ref = (
        costs
        .loc[costs['Scenario'] == 'Reference']
        .pivot_table(columns='carrier', index='Scenario', values='annual_system_cost [M$]')
        .div(1e3)
    )

    res = (
        costs
        .loc[costs['Scenario'] == '100% RES']
        .pivot_table(columns='carrier', index='Scenario', values='annual_system_cost [M$]')
        .div(1e3)
    )

    cfe = (
        costs
        .loc[costs['Scenario'].str.contains('CFE')]
        .pivot_table(columns='carrier', index='CFE Score', values='annual_system_cost [M$]')
        .div(1e3)
    )

    # ---
    # plot

    colors = cplt.tech_color_palette()

    ref.plot(kind='bar', stacked=True, ax=ax0, legend=False, color=[colors.get(x, '#333333') for x in res.columns])
    res.plot(kind='bar', stacked=True, ax=ax1, legend=False, color=[colors.get(x, '#333333') for x in res.columns])
    cfe.plot(kind='bar', stacked=True, ax=ax2, legend=True, color=[colors.get(x, '#333333') for x in res.columns])

    ax0.set_ylabel('Total System Cost\n[$ billion]')

    ax0.set_xlabel('')
    ax1.set_xlabel('')
    ax2.set_xlabel('CFE Score [%]')

    for ax in [ax0, ax1, ax2]:
        # set y-axis grid
        ax.yaxis.grid(True, linestyle=':', linewidth=0.5)
        # Rotate x-ticks
        ax.set_xticklabels(ax.get_xticklabels(), rotation=0)
        # despine
        sns.despine(ax=ax, left=False)

    # Adjust horizontal space between ax0 and ax1
    fig.subplots_adjust(wspace=0.1)

    # Remove legend title and box
    legend = ax2.legend(ncol=99)
    legend.set_title(None)
    legend.get_frame().set_linewidth(0)

    # save plot
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/cost_vs_cfe_tradeoff_stacked.png'
        ),
        bbox_inches='tight'
    )

    # ------------------------------------------------------------------
    # Costs vs benefits relative to reference scenario

    cost_results = (
        pd.concat(
            [
                solved_networks[k].statistics()[['Capital Expenditure', 'Operational Expenditure']].assign(name=k) 
                for k in solved_networks.keys()
            ], 
        axis=0
        )
        .pipe(
            cget.split_scenario_col,
            'name'
        )
        .drop('name', axis=1)
    )

    # get results for reference scenario
    ref = cost_results.query("Scenario == 'Reference'")

    # loop through each scenario and calculate cost delta
    cost_delta = pd.concat(
        [
            cost_results.query(f"Scenario == '{s}'")
            .assign(
                **{
                    'Capital Expenditure': lambda x: x['Capital Expenditure'] - ref['Capital Expenditure'].values,
                    'Operational Expenditure': lambda x: x['Operational Expenditure'] - ref['Operational Expenditure'].values
                }
            )
            for s in cost_results.Scenario.unique().tolist() if s != 'Reference'
        ],
        axis=0
    )

    cost_delta = (
        cost_delta
        .rename(columns={'Capital Expenditure': 'CapEx', 'Operational Expenditure': 'OpEx'})
        .reset_index()
        .rename(columns={'level_0' : 'Component', 'level_1' : 'Technology'})
        .melt(
            id_vars=['Scenario', 'Component', 'Technology'], 
            value_vars=['CapEx', 'OpEx']
        )
        .query(" ~Technology.isin(['Transmission', '-'])")
        .pivot_table(
            index='Scenario', 
            columns=['Technology','variable'], 
            values='value', 
            aggfunc='sum'
        )
    )

    cost_delta = cost_delta.loc[:, (cost_delta.sum(axis=0) != 0)]

    fig, ax0, ax1 = cplt.bar_plot_2row(figsize=(10,4), width_ratios=[1, 10])

    # set theme
    cplt.set_tz_theme()

    # plot 100% RES
    res = cost_delta.loc[['100% RES']].div(1e9)
    res.plot(kind='bar', stacked=True, ax=ax0, legend=False)
    # add net cost marker
    # ax0.scatter(x=res.index, y=[res.sum(axis=1)] * len(res.index), color='red', marker='s', edgecolors='black', linewidths=1)

    # plot cfe
    cfe = cost_delta.loc[cost_delta.index != '100% RES'].div(1e9).copy()
    cfe.index = [int(i.replace('CFE-', '')) for i in cfe.index]
    cfe.sort_index(inplace=True)
    cfe.plot(kind='bar', stacked=True, ax=ax1, legend=True)

    # formatting
    for ax in [ax0, ax1]:
        ax.yaxis.grid(True, linestyle=':', linewidth=0.5)
        ax.axhline(0, color='white', linewidth=0.8, linestyle='-')
        ax.set_xticklabels(ax.get_xticklabels(), rotation=0)

    ax0.set_xlabel('')
    ax0.set_ylabel('System Cost and Benefits\n[billion USD]')

    ax1.set_xlabel('CFE Score [%]')

    # Remove legend title and box
    legend = ax1.legend(ncol=2)
    legend.set_title(None)
    legend.get_frame().set_linewidth(0)

    # save plot
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/cost_vs_benefit_by_scenario.png'
        ),
        bbox_inches='tight'
    )

    # ------------------------------------------------------------------
    # System costs ($/MWh) by scenario

    # stacked bar plot
    costs = (
        pd.concat(
            [
                cget
                .get_unit_cost(solved_networks[k])
                .assign(name=k)
                for k, n in solved_networks.items()
            ]
        )
        .pipe(
            cget.split_scenario_col,
            'name',
        )
        .drop('name', axis=1)
    )

    costs = costs.query(" ~carrier.isin(['Transmission', '-']) ").reset_index(drop=True)

    fig, ax0, ax1 = cplt.bar_plot_2row(figsize=(10,4), width_ratios=[1,10])

    # get relevant data
    ref = (
        costs
        .loc[costs['Scenario'] == 'Reference']
        .pivot_table(columns='carrier', index='Scenario', values='System Cost [$/MWh]')
    )

    res = (
        costs
        .loc[costs['Scenario'] == '100% RES']
        .pivot_table(columns='carrier', index='Scenario', values='System Cost [$/MWh]')
    )

    cfe = (
        costs
        .loc[costs['Scenario'].str.contains('CFE')]
        .pivot_table(columns='carrier', index='CFE Score', values='System Cost [$/MWh]')
    )

    # ---
    # plot

    colors = cplt.tech_color_palette()

    #ref.plot(kind='bar', stacked=True, ax=ax0, legend=False, color=[colors.get(x, '#333333') for x in res.columns])
    res.plot(kind='bar', stacked=True, ax=ax0, legend=False, color=[colors.get(x, '#333333') for x in res.columns])
    cfe.plot(kind='bar', stacked=True, ax=ax1, legend=True, color=[colors.get(x, '#333333') for x in res.columns])

    ax0.set_ylabel('System Cost [$/MWh]')

    ax0.set_xlabel('')
    ax1.set_xlabel('CFE Score [%]')

    for ax in [ax0, ax1]:
        # set y-axis grid
        ax.yaxis.grid(True, linestyle=':', linewidth=0.5)
        # Rotate x-ticks
        ax.set_xticklabels(ax.get_xticklabels(), rotation=0)
        # despine
        sns.despine(ax=ax, left=False)

    # Adjust horizontal space between ax0 and ax1
    fig.subplots_adjust(wspace=0.1)

    # Remove legend title and box
    legend = ax1.legend(ncol=99)
    legend.set_title(None)
    legend.get_frame().set_linewidth(0)

    # save plot
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/unit_cost_by_scenario.png'
        ),
        bbox_inches='tight'
    )

    # ------------------------------------------------------------------
    # C&I ENERGY BALANCE

    fig, ax0, ax1 = cplt.bar_plot_2row(figsize=(10,4), width_ratios=[1,10])

    ci_procurement = (
        pd.concat(
            [cget.get_ci_procurement(n, 'C&I').assign(name=k) for k, n in solved_networks.items()]
        )
        .pipe(
            cget.split_scenario_col,
            'name',
        )
        .drop('name', axis=1)
    )

    # plot 100% RES for reference
    res = (
        ci_procurement
        .loc[ci_procurement['Scenario'] == '100% RES']
        .drop(['Scenario','CFE Score'], axis=1)
        .mul(100)
        .rename(index={0:'100% RES'})
    )

    cfe = (
        ci_procurement
        .query("Scenario.str.contains('CFE')")
        .sort_values('CFE Score')
        .drop(['Scenario'], axis=1)
        .set_index('CFE Score')
        .mul(100)
    )

    res.plot(kind='bar', stacked=True, ax=ax0, legend=False)
    cfe.plot(kind='bar', stacked=True, ax=ax1, legend=True)

    ax0.set_ylabel('C&I Procurement Mix\n[% of load]')
    ax1.set_xlabel('CFE Score [%]')

    for ax in [ax0, ax1]:
        ax.set_xticklabels(ax.get_xticklabels(), rotation=0)
        ax.yaxis.grid(True, linestyle=':', linewidth=0.5)
        sns.despine(ax=ax, left=False)

    # Remove legend title and box
    # Remove legend title and box
    legend = ax1.legend(ncol=99, loc='upper center', bbox_to_anchor=(0.5, 1.1))
    legend.set_title(None)
    legend.get_frame().set_linewidth(0)

    # Adjust horizontal space between ax0 and ax1
    fig.subplots_adjust(wspace=0.1)

    # save plot
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/ci_energy_balance_by_scenario.png'
        ),
        bbox_inches='tight'
    )

    # ------------------------------------------------------------------
    # HEATMAP OF CFE SCORE
    fields_to_plot = ['Battery', 'Solar', 'Wind']
    ymax = cget.get_total_annual_system_cost(solved_networks['n_hm_CFE100_2030']).query("carrier.isin(@fields_to_plot)")['annual_system_cost [M$]'].sum() / 1e3
    for k in solved_networks.keys():
        # get network
        n = solved_networks[k].copy()
        # init fig
        fig, ax0, ax1 = cplt.plot_cfe_hmap(n, ymax=ymax, ci_identifier='C&I')

        # set fname
        if 'n_bf' in k:
            fname = 'reference'
            ax.set_title(f'{fname}', loc='center', fontsize=10)
        elif 'n_am' in k:
            fname = 'RES100'
            ax.set_title(f'{fname}', loc='center', fontsize=10)
        elif 'n_hm' in k:
            fname = k.split('_')[2]
            cfe_score = int( fname.replace('CFE','') )
            ax0.set_title(f'{cfe_score}% clean procurement: hour-by-hour\n\n', loc='left', fontsize=14, fontweight='bold')
        
        # save plot
        fig.savefig(
            os.path.join(
                path_to_run_dir, f'results/hmap_score_{fname}.png'
            ),
            bbox_inches='tight'
        )


def aggregate_capacity(
        scenarios,
        components = ['generators', 'storage_units', 'links'],
        groupby=['carrier'], 
        attrs=['p_nom', 'p_nom_opt']
    ):
    '''Aggregates the capacity of components across a set of scenarios.
    '''
    def get_capacity(
            data, 
            scenario_name
        ):

        capacity_frames = []
        for component in components:
            if hasattr(data, component):
                capacity_frame = (
                    getattr(data, component)
                    .groupby(by=groupby)
                    .sum(numeric_only=True)[attrs]
                    .fillna(0)
                    .assign(scenario=scenario_name)
                )
                capacity_frames.append(capacity_frame)
        
        return pd.concat(capacity_frames)

    return (
        pd
        .concat(
            [
                get_capacity(scenario_data, scenario_name) for scenario_name, scenario_data in scenarios.items()
            ]
        )
    )