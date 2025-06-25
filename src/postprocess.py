import os

import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

from matplotlib.ticker import MaxNLocator

from . import plotting as cplt
from . import get as cget

def plot_results(path_to_run_dir: str, run: dict, nodes_with_ci_loads):
    '''Plot results for a given run
    '''

    # set tz plotting theme
    cplt.set_tz_theme()
    colors = cplt.tech_color_palette()

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

    # load list of C&I carriers to be plot
    ci_carriers = cget.get_ci_carriers(solved_networks['n_bf'])

    # Add Work Sans font to matplotlib
    work_sans_path_light = './assets/WorkSans-Light.ttf'
    work_sans_path_medium = './assets/WorkSans-Medium.ttf'
    work_sans_font = fm.FontProperties(fname=work_sans_path_light)
    work_sans_font_medium = fm.FontProperties(fname=work_sans_path_medium)
    # plt.rcParams['font.family'] = work_sans_font.get_name()
    
    plot_ci_portfolio_capacity(solved_networks=solved_networks,
                               path_to_run_dir=path_to_run_dir,
                               work_sans_font=work_sans_font)
    
    plot_ci_portfolio_procurement_cost(solved_networks=solved_networks,
                                       path_to_run_dir=path_to_run_dir,
                                       work_sans_font=work_sans_font)
    
    plot_ci_and_parent_generation(solved_networks=solved_networks,
                                  path_to_run_dir=path_to_run_dir,
                                  nodes_with_ci_loads=nodes_with_ci_loads,
                                  work_sans_font=work_sans_font)

    plot_ci_and_parent_capacity(solved_networks=solved_networks,
                                  path_to_run_dir=path_to_run_dir,
                                  nodes_with_ci_loads=nodes_with_ci_loads,
                                  work_sans_font=work_sans_font)
    
    plot_ci_energy_balance(solved_networks=solved_networks,
                                       path_to_run_dir=path_to_run_dir,
                                       work_sans_font=work_sans_font)

    plot_ci_unit_cost_of_electricity(solved_networks=solved_networks,
                                     path_to_run_dir=path_to_run_dir,
                                     work_sans_font=work_sans_font)
    
    plot_ci_unit_cost_of_electricity_alt(solved_networks=solved_networks,
                                        path_to_run_dir=path_to_run_dir,
                                        import_tariff=83.56, # in USD/MWh
                                        export_tariff=36.33, # in USD/MWh
                                        work_sans_font=work_sans_font)

    plot_relative_emissions_by_scenario(solved_networks=solved_networks,
                                        path_to_run_dir=path_to_run_dir,
                                        work_sans_font=work_sans_font)

    plot_system_emission_rate_by_scenario(solved_networks=solved_networks,
                                          path_to_run_dir=path_to_run_dir,
                                          work_sans_font=work_sans_font)
    
    plot_ci_emission_rate_by_scenario(solved_networks=solved_networks,
                                      path_to_run_dir=path_to_run_dir,
                                      nodes_with_ci_loads=nodes_with_ci_loads,
                                      run=run,
                                      work_sans_font=work_sans_font)

    plot_total_system_costs_by_scenario(solved_networks=solved_networks,
                                        path_to_run_dir=path_to_run_dir,
                                        work_sans_font=work_sans_font)

    plot_system_generation_mix(solved_networks=solved_networks,
                               path_to_run_dir=path_to_run_dir,
                               work_sans_font=work_sans_font)
    
    plot_system_capacity_mix(solved_networks=solved_networks,
                             path_to_run_dir=path_to_run_dir,
                             work_sans_font=work_sans_font)

    # plot_system_unit_cost_by_scenario(solved_networks=solved_networks,
    #                                   path_to_run_dir=path_to_run_dir,
    #                                   work_sans_font=work_sans_font)

    plot_system_costs_vs_benefits(solved_networks=solved_networks,
                                                path_to_run_dir=path_to_run_dir,
                                                work_sans_font=work_sans_font)
    
    plot_ci_curtailment(solved_networks=solved_networks,
                        path_to_run_dir=path_to_run_dir,
                        work_sans_font=work_sans_font)

    plot_cfe_score_heatmaps(solved_networks=solved_networks,
                            path_to_run_dir=path_to_run_dir,
                            run=run,
                            work_sans_font_medium=work_sans_font_medium)
    
    plot_monthly_cfe_score_heatmaps(solved_networks=solved_networks,
                                    path_to_run_dir=path_to_run_dir,
                                    run=run,
                                    work_sans_font_medium=work_sans_font_medium)


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

def plot_ci_portfolio_capacity(solved_networks, path_to_run_dir, work_sans_font):
    """
    Plot C&I Portfolio Capacity [GW] by scenario.
    """
    print('Creating C&I portfolio capacity plot')

    fig, ax0, ax1 = cplt.bar_plot_2row(width_ratios=[1,10], figsize=(6,4))

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
        .query("capacity != 0")
    )

    # pull out relevant data
    res = (
        expanded_capacity
        .loc[expanded_capacity['Scenario'] == '100% RES']
        .drop(['Scenario','CFE Score'], axis=1)
        .query(" ~carrier.isin(['Transmission','AC']) ")
        .pivot_table(columns='carrier', values='capacity')
        .div(1e3)
        .rename(index={'capacity':'100% RES'})
    )
    cfe = (
        expanded_capacity
        .query("Scenario.str.contains('CFE')")
        .sort_values('CFE Score')
        .query(" ~carrier.isin(['Transmission','AC']) ")
        .pivot_table(index='CFE Score', columns='carrier', values='capacity')
        .div(1e3)
    )
    
    # save df
    (pd.concat([res, cfe], axis=0)).to_csv(
        os.path.join(
            path_to_run_dir, 'results/01_ci_capacity.csv'
        ),
        index=True
    )

    colors = cplt.tech_color_palette()

    res.plot(kind='bar', stacked=True, ax=ax0, legend=False, color=[colors.get(x, '#333333') for x in res.columns])
    cfe.plot(kind='bar', stacked=True, ax=ax1, legend=True, color=[colors.get(x, '#333333') for x in cfe.columns])

    ax0.set_ylabel('C&I procured portfolio [GW]', fontproperties=work_sans_font)
    ax1.set_xlabel('CFE Score [%]', fontproperties=work_sans_font)

    for ax in [ax0, ax1]:
        ax.set_xticklabels(ax.get_xticklabels(), rotation=0, fontproperties=work_sans_font)
        ax.yaxis.grid(True, linestyle=':', linewidth=0.5)
        for label in ax.get_yticklabels():
            label.set_fontproperties(work_sans_font)
        sns.despine(ax=ax, left=False)

    # Remove legend title and box, make sure labels are displayed in the same order as in the plot
    handles, labels = ax1.get_legend_handles_labels()
    order = [cfe.columns.tolist().index(label) for label in labels if label in cfe.columns]
    sorted_handles_labels = sorted(zip(order, handles, labels), key=lambda x: -x[0])
    sorted_handles, sorted_labels = zip(*[(h, l) for _, h, l in sorted_handles_labels])

    legend = ax1.legend(sorted_handles, sorted_labels, bbox_to_anchor=(1, 0.5), ncol=1)
    legend.set_title(None)
    legend.get_frame().set_linewidth(0)

    # Set font of the legend
    for text in legend.get_texts():
        text.set_fontproperties(work_sans_font)

    # Adjust horizontal space between ax0 and ax1
    fig.subplots_adjust(wspace=0.1)

    # save
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/01_ci_capacity.png'
        ),
        bbox_inches='tight'
    )
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/01_ci_capacity.svg'
        ),
        bbox_inches='tight'
    )

def plot_ci_and_parent_generation(solved_networks, path_to_run_dir, nodes_with_ci_loads, work_sans_font):
    """
    Plot generation mix by scenario for C&I and parent node.
    """
    print('Creating C&I and parent node generation plot')

    generation_mix = (
        pd.concat(
            [
                solved_networks[k].statistics(
                    groupby=['bus', 'carrier']
                )[['Supply']].assign(name=k)
                for k in solved_networks.keys()
            ],
            axis=0
        )
        .pipe(
            cget.split_scenario_col,
            'name'
        )
        .drop('name', axis=1)
        .reset_index()
        .query("level_0 in ['Generator', 'StorageUnit', 'Link']")
    )

    # get relevant data
    ref = (
        generation_mix
        .loc[
            (generation_mix['Scenario'] == 'Reference')
            &
            (generation_mix['level_1'].str.contains(nodes_with_ci_loads))
        ]
        .pivot_table(columns='level_2', index='Scenario', values='Supply', aggfunc='sum')
        .div(1e6)
    )

    res = (
        generation_mix
        .loc[
            (generation_mix['Scenario'] == '100% RES')
            &
            (generation_mix['level_1'].str.contains(nodes_with_ci_loads))
        ]
        .pivot_table(columns='level_2', index='Scenario', values='Supply', aggfunc='sum')
        .div(1e6)
    )

    cfe = (
        generation_mix
        .loc[(generation_mix['Scenario'].str.contains('CFE'))
                &
                (generation_mix['level_1'].str.contains(nodes_with_ci_loads))
                ]
        .pivot_table(columns='level_2', index='CFE Score', values='Supply', aggfunc='sum')
        .div(1e6)
    )

    # save df
    (pd.concat([ref, res, cfe], axis=0)).to_csv(
        os.path.join(
            path_to_run_dir, 'results/03_ci_parent_generation.csv'
        ),
        index=True
    )

    fig, ax0, ax1, ax2 = cplt.bar_plot_3row(width_ratios=[1, 1, 10], figsize=(6, 4))
    colors = cplt.tech_color_palette()

    ref.plot(kind='bar', stacked=True, ax=ax0, legend=False, color=[colors.get(x, '#333333') for x in ref.columns])
    res.plot(kind='bar', stacked=True, ax=ax1, legend=False, color=[colors.get(x, '#333333') for x in res.columns])
    cfe.plot(kind='bar', stacked=True, ax=ax2, legend=True, color=[colors.get(x, '#333333') for x in cfe.columns])

    for ax in [ax0, ax1, ax2]:
        ax.yaxis.grid(True, linestyle=':', linewidth=0.5)
        sns.despine(ax=ax, left=False)
        ax.set_xticklabels(ax.get_xticklabels(), rotation=0, fontproperties=work_sans_font)
        for label in ax.get_yticklabels():
            label.set_fontproperties(work_sans_font)

    ax0.set_ylabel('Generation [TWh]', fontproperties=work_sans_font)
    ax1.set_ylabel('')
    ax2.set_ylabel('')

    ax0.set_xlabel('')
    ax1.set_xlabel('')
    ax2.set_xlabel('CFE Score [%]', fontproperties=work_sans_font)

    # Move the legend to the right and outside the plot
    handles, labels = ax2.get_legend_handles_labels()
    order = [cfe.columns.tolist().index(label) for label in labels if label in cfe.columns]
    sorted_handles_labels = sorted(zip(order, handles, labels), key=lambda x: -x[0])
    sorted_handles, sorted_labels = zip(*[(h, l) for _, h, l in sorted_handles_labels])

    legend = ax2.legend(sorted_handles, sorted_labels, loc='center left', bbox_to_anchor=(1, 0.5), ncol=1)
    legend.set_title(None)
    legend.get_frame().set_linewidth(0)

    # Set font of the legend
    for text in legend.get_texts():
        text.set_fontproperties(work_sans_font)

    # save plot
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/03_ci_parent_generation.png'
        ),
        bbox_inches='tight'
    )
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/03_ci_parent_generation.svg'
        ),
        bbox_inches='tight'
    )

def plot_ci_and_parent_capacity(solved_networks, path_to_run_dir, nodes_with_ci_loads, work_sans_font):
    """
    Plot capacity mix by scenario for C&I and parent node.
    """
    print('Creating C&I and parent node capacity plot')

    capacity_mix = (
        pd.concat(
            [
                solved_networks[k].statistics(
                    groupby=['bus', 'carrier']
                )[["Optimal Capacity"]].assign(name=k)
                for k in solved_networks.keys()
            ],
            axis=0
        )
        .pipe(
            cget.split_scenario_col,
            'name'
        )
        .drop('name', axis=1)
        .reset_index()
        .query("level_0 in ['Generator', 'StorageUnit']")
    )

    # get relevant data
    ref = (
        capacity_mix
        .loc[
            (capacity_mix['Scenario'] == 'Reference')
            &
            (capacity_mix['level_1'].str.contains(nodes_with_ci_loads))
        ]
        .pivot_table(columns='level_2', index='Scenario', values='Optimal Capacity', aggfunc='sum')
        .div(1e3)
    )

    res = (
        capacity_mix
        .loc[
            (capacity_mix['Scenario'] == '100% RES')
            &
            (capacity_mix['level_1'].str.contains(nodes_with_ci_loads))
        ]
        .pivot_table(columns='level_2', index='Scenario', values='Optimal Capacity', aggfunc='sum')
        .div(1e3)
    )

    cfe = (
        capacity_mix
        .loc[(capacity_mix['Scenario'].str.contains('CFE'))
                &
                (capacity_mix['level_1'].str.contains(nodes_with_ci_loads))
        ]
        .pivot_table(columns='level_2', index='CFE Score', values='Optimal Capacity', aggfunc='sum')
        .div(1e3)
    )

    # save df
    (pd.concat([ref, res, cfe], axis=0)).to_csv(
        os.path.join(
            path_to_run_dir, 'results/04_ci_parent_capacity.csv'
        ),
        index=True
    )

    fig, ax0, ax1, ax2 = cplt.bar_plot_3row(width_ratios=[1, 1, 10], figsize=(6, 4))
    colors = cplt.tech_color_palette()

    ref.plot(kind='bar', stacked=True, ax=ax0, legend=False, color=[colors.get(x, '#333333') for x in ref.columns])
    res.plot(kind='bar', stacked=True, ax=ax1, legend=False, color=[colors.get(x, '#333333') for x in res.columns])
    cfe.plot(kind='bar', stacked=True, ax=ax2, legend=True, color=[colors.get(x, '#333333') for x in cfe.columns])

    for ax in [ax0, ax1, ax2]:
        ax.yaxis.grid(True, linestyle=':', linewidth=0.5)
        sns.despine(ax=ax, left=False)
        ax.set_xticklabels(ax.get_xticklabels(), rotation=0, fontproperties=work_sans_font)
        for label in ax.get_yticklabels():
            label.set_fontproperties(work_sans_font)

    ax0.set_ylabel('Capacity [GW]', fontproperties=work_sans_font)
    ax1.set_ylabel('')
    ax2.set_ylabel('')

    ax0.set_xlabel('')
    ax1.set_xlabel('')
    ax2.set_xlabel('CFE Score [%]', fontproperties=work_sans_font)

    # Move the legend to the right and outside the plot
    handles, labels = ax2.get_legend_handles_labels()
    order = [cfe.columns.tolist().index(label) for label in labels if label in cfe.columns]
    sorted_handles_labels = sorted(zip(order, handles, labels), key=lambda x: -x[0])
    sorted_handles, sorted_labels = zip(*[(h, l) for _, h, l in sorted_handles_labels])

    legend = ax2.legend(sorted_handles, sorted_labels, loc='center left', bbox_to_anchor=(1, 0.5), ncol=1)
    legend.set_title(None)
    legend.get_frame().set_linewidth(0)

    # Set font of the legend
    for text in legend.get_texts():
        text.set_fontproperties(work_sans_font)

    # save plot
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/04_ci_parent_capacity.png'
        ),
        bbox_inches='tight'
    )
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/04_ci_parent_capacity.svg'
        ),
        bbox_inches='tight'
    )

def plot_ci_portfolio_procurement_cost(solved_networks, path_to_run_dir, work_sans_font):
    """
    Plot C&I Portfolio Procurement cost [currency] by scenario.
    """
    print('Creating C&I portfolio procurement cost by scenario plot')

    fig, ax0, ax1 = cplt.bar_plot_2row(width_ratios=[1,10], figsize=(6,4))

     # load list of C&I carriers to be plot
    ci_carriers = cget.get_ci_carriers(solved_networks['n_bf'])

    ci_procurement_cost = (
        pd.concat(
            [
                cget.get_total_ci_procurement_cost(
                    solved_networks[k]
                )
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
    res_ci_costs = (
        ci_procurement_cost
        .loc[ci_procurement_cost['Scenario'] == '100% RES']
        .drop(['Scenario','CFE Score'], axis=1)
        .query(" ~carrier.isin(['Transmission','AC']) ")
        .query("carrier in @ci_carriers")
        .pivot_table(columns='carrier', values='annual_system_cost [M$]')
        .rename(index={'annual_system_cost [M$]':'100% RES'})
    )

    cfe_ci_costs = (
        ci_procurement_cost
        .query("Scenario.str.contains('CFE')")
        .sort_values('CFE Score')
        .query(" ~carrier.isin(['Transmission','AC']) ")
        .query("carrier in @ci_carriers")
        .pivot_table(index='CFE Score', columns='carrier', values='annual_system_cost [M$]')
    )

    # save df
    (pd.concat([res_ci_costs, cfe_ci_costs], axis=0)).to_csv(
        os.path.join(
            path_to_run_dir, 'results/02_ci_total_cost.csv'
        ),
        index=True
    )

    colors = cplt.tech_color_palette()

    res_ci_costs.plot(kind='bar', stacked=True, ax=ax0, legend=False, color=[colors.get(x, '#333333') for x in res_ci_costs.columns])
    cfe_ci_costs.plot(kind='bar', stacked=True, ax=ax1, legend=True, color=[colors.get(x, '#333333') for x in cfe_ci_costs.columns])

    ax0.set_ylabel('C&I procured portfolio cost [M$]', fontproperties=work_sans_font)
    ax1.set_xlabel('CFE Score [%]', fontproperties=work_sans_font)

    for ax in [ax0, ax1]:
        ax.set_xticklabels(ax.get_xticklabels(), rotation=0, fontproperties=work_sans_font)
        for label in ax.get_yticklabels():
            label.set_fontproperties(work_sans_font)
        ax.yaxis.grid(True, linestyle=':', linewidth=0.5)
        sns.despine(ax=ax, left=False)

    # Remove legend title and box, make sure labels are displayed in the same order as in the plot
    handles, labels = ax1.get_legend_handles_labels()
    order = [cfe_ci_costs.columns.tolist().index(label) for label in labels if label in cfe_ci_costs.columns]
    sorted_handles_labels = sorted(zip(order, handles, labels), key=lambda x: -x[0])
    sorted_handles, sorted_labels = zip(*[(h, l) for _, h, l in sorted_handles_labels])

    legend = ax1.legend(sorted_handles, sorted_labels, bbox_to_anchor=(1, 0.5), ncol=1)
    legend.set_title(None)
    legend.get_frame().set_linewidth(0)

    # Set font of the legend
    for text in legend.get_texts():
        text.set_fontproperties(work_sans_font)

    # Adjust horizontal space between ax0 and ax1
    fig.subplots_adjust(wspace=0.1)

    # save
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/02_ci_total_cost.png'
        ),
        bbox_inches='tight'
    )
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/02_ci_total_cost.svg'
        ),
        bbox_inches='tight'
    )

def plot_relative_emissions_by_scenario(solved_networks, path_to_run_dir, work_sans_font):
    """
    Plot relative emissions reduction by scenario compared to baseline.
    """
    # ------------------------------------------------------------------
    # EMISSIONS

    print('Creating relative emissions reduction by scenario plot')

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

    fig, ax0, ax1 = cplt.bar_plot_2row(width_ratios=[1,10], figsize=(6,4))

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

    # save df
    (pd.concat([res, cfe], axis=0)).to_csv(
        os.path.join(
            path_to_run_dir, 'results/07_system_emissions_reduction.csv'
        ),
        index=True
    )

    res.plot(kind='scatter', x='Scenario', y='relative_emission', ax=ax0, s=50)
    cfe.plot(kind='scatter', x='CFE Score', y='relative_emission', ax=ax1, s=50)

    for ax in [ax0, ax1]:
        ax.yaxis.grid(True, linestyle=':', linewidth=0.5)
        ax.set_xticklabels(ax.get_xticklabels(), fontproperties=work_sans_font)
        for label in ax.get_yticklabels():
            label.set_fontproperties(work_sans_font)
        sns.despine(ax=ax, left=False)

    ax0.set_ylabel('Emission Reduction [%]', fontproperties=work_sans_font)
    ax1.set_ylabel('')

    ax0.set_xlabel('')
    ax1.set_xlabel('CFE Score [%]', fontproperties=work_sans_font)
    
    # save plot
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/07_system_emissions_reduction.png'
        ),
        bbox_inches='tight'
    )
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/07_system_emissions_reduction.svg'
        ),
        bbox_inches='tight'
    )

def plot_system_emission_rate_by_scenario(solved_networks, path_to_run_dir, work_sans_font):
    """
    Plot system emission rate [gCO2/kWh] by scenario.
    """
    # ------------------------------------------------------------------
    # SYSTEM EMISSION RATE

    print('Creating system emission rate by scenario plot')

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

    fig, ax0, ax1, ax2 = cplt.bar_plot_3row(width_ratios=[1,1,10], figsize=(6,4))

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

    # save df
    (pd.concat([ref, res, cfe], axis=0)).to_csv(
        os.path.join(
            path_to_run_dir, 'results/08_system_emissions.csv'
        ),
        index=True
    )

    ref.plot(kind='bar', x='Scenario', y='emission_rate', ax=ax0, legend=False)
    res.plot(kind='bar', x='Scenario', y='emission_rate', ax=ax1, legend=False)
    cfe.plot(kind='bar', x='CFE Score', y='emission_rate', ax=ax2, legend=False)

    for ax in [ax0, ax1, ax2]:
        ax.yaxis.grid(True, linestyle=':', linewidth=0.5)
        sns.despine(ax=ax, left=False)
        ax.set_xticklabels(ax.get_xticklabels(), rotation=0, fontproperties=work_sans_font)
        for label in ax.get_yticklabels():
            label.set_fontproperties(work_sans_font)

    ax0.set_ylabel('System Emission Rate [gCO$_2$ kWh$^{-1}$]', fontproperties=work_sans_font)
    ax1.set_ylabel('')
    ax2.set_ylabel('')

    ax0.set_xlabel('')
    ax1.set_xlabel('')
    ax2.set_xlabel('CFE Score [%]', fontproperties=work_sans_font)

    # save plot
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/08_system_emissions.png'
        ),
        bbox_inches='tight'
    )
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/08_system_emissions.svg'
        ),
        bbox_inches='tight'
    )

def plot_ci_emission_rate_by_scenario(solved_networks, path_to_run_dir, nodes_with_ci_loads, run, work_sans_font):
    """
    Plot C&I emission rate [gCO2/kWh] by scenario.
    """
    # ------------------------------------------------------------------
    # C&I EMISSION RATE

    print('Creating C&I emission rate by scenario plot')

    ci_emissions = (
        pd
        .DataFrame({
            'name' : [k for k in solved_networks.keys()],
            'load' : [solved_networks[k].loads_t.p_set.filter(regex='C&I').sum().sum() for k in solved_networks.keys()],
            'emissions' : [
                np.sum(
                    solved_networks[k].links_t.p0.filter(regex='C&I').filter(regex='Import').values.flatten() @ np.array(cget.get_ci_parent_emissions(solved_networks[k], nodes_with_ci_loads))
                ) 
                for k in solved_networks.keys()
            ],
            # 'emissions' : [
            #     np.sum(
            #         solved_networks[k].links_t.p0.filter(regex='C&I').filter(regex='Import').values.flatten() @ np.array(cget.GetGridCFE(solved_networks[k], ci_identifier='C&I', run=run))
            #     ) 
            #     for k in solved_networks.keys()
            # ],
        })
        .pipe(
            cget.split_scenario_col,
            'name',
        )
    )

    ci_emissions['emission_rate'] = (ci_emissions['emissions'] / ci_emissions['load']) * 1000 # tCO2 / MWh -> gCO2 / kWh

    fig, ax0, ax1 = cplt.bar_plot_2row(width_ratios=[1,10], figsize=(6,4))

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

    # save df
    (pd.concat([res, cfe], axis=0)).to_csv(
        os.path.join(
            path_to_run_dir, 'results/09_ci_emissions_rate.csv'
        ),
        index=True
    )

    res.plot(kind='bar', x='Scenario', y='emission_rate', ax=ax0, legend=False)
    cfe.plot(kind='bar', x='CFE Score', y='emission_rate', ax=ax1, legend=False)

    for ax in [ax0, ax1]:
        ax.yaxis.grid(True, linestyle=':', linewidth=0.5)
        sns.despine(ax=ax, left=False)
        ax.set_xticklabels(ax.get_xticklabels(), rotation=0, fontproperties=work_sans_font)
        for label in ax.get_yticklabels():
            label.set_fontproperties(work_sans_font)

    ax0.set_ylabel('C&I Emission Rate [gCO$_2$ kWh$^{-1}$]', fontproperties=work_sans_font)
    ax1.set_ylabel('')

    ax0.set_xlabel('')
    ax1.set_xlabel('CFE Score [%]', fontproperties=work_sans_font)

    # save plot
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/09_ci_emissions_rate.png'
        ),
        bbox_inches='tight'
    )
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/09_ci_emissions_rate.svg'
        ),
        bbox_inches='tight'
    )

def plot_total_system_costs_by_scenario(solved_networks, path_to_run_dir, work_sans_font):
    """
    Plot total system costs by scenario (Reference, 100% RES, CFE).
    """
    # ------------------------------------------------------------------
    # TOTAL SYSTEM COSTS BY SCENARIO 
    # > REF, 100% RES, CFE

    print('Creating total system costs by scenario plot')

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

    fig, ax0, ax1, ax2 = cplt.bar_plot_3row(figsize=(6,4), width_ratios=[1,1,10])

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

        # save df
    (pd.concat([ref, res, cfe], axis=0)).to_csv(
        os.path.join(
            path_to_run_dir, 'results/10_system_costs.csv'
        ),
        index=True
    )

    # ---
    # plot

    colors = cplt.tech_color_palette()

    ref.plot(kind='bar', stacked=True, ax=ax0, legend=False, color=[colors.get(x, '#333333') for x in res.columns])
    res.plot(kind='bar', stacked=True, ax=ax1, legend=False, color=[colors.get(x, '#333333') for x in res.columns])
    cfe.plot(kind='bar', stacked=True, ax=ax2, legend=True, color=[colors.get(x, '#333333') for x in res.columns])

    ax0.set_ylabel('Total System Cost\n[$ billion]', fontproperties=work_sans_font)

    ax0.set_xlabel('')
    ax1.set_xlabel('')
    ax2.set_xlabel('CFE Score [%]', fontproperties=work_sans_font)

    for ax in [ax0, ax1, ax2]:
        # set y-axis grid
        ax.yaxis.grid(True, linestyle=':', linewidth=0.5)
        for label in ax.get_yticklabels():
            label.set_fontproperties(work_sans_font)
        # Rotate x-ticks
        ax.set_xticklabels(ax.get_xticklabels(), rotation=0, fontproperties=work_sans_font)
        # despine
        sns.despine(ax=ax, left=False)

    # Adjust horizontal space between ax0 and ax1
    fig.subplots_adjust(wspace=0.1)
    # Remove legend title and box
    handles, labels = ax2.get_legend_handles_labels()
    order = [res.columns.tolist().index(label) for label in labels if label in res.columns]
    sorted_handles_labels = sorted(zip(order, handles, labels), key=lambda x: -x[0])
    sorted_handles, sorted_labels = zip(*[(h, l) for _, h, l in sorted_handles_labels])

    legend = ax2.legend(sorted_handles, sorted_labels, loc='center left', bbox_to_anchor=(1, 0.5), ncol=1)
    legend.set_title(None)
    legend.get_frame().set_linewidth(0)

    # Set font of the legend
    for text in legend.get_texts():
        text.set_fontproperties(work_sans_font)

    # save plot
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/10_system_costs.png'
        ),
        bbox_inches='tight'
    )
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/10_system_costs.svg'
        ),
        bbox_inches='tight'
    )

def plot_system_generation_mix(solved_networks, path_to_run_dir, work_sans_font):
    """
    Plot system generation mix by scenario.
    """
    # ------------------------------------------------------------------
    # System generation mix by scenario
    print('Creating system generation mix plot')

    generation_mix = (
        pd.concat(
            [
                solved_networks[k].statistics()[['Supply']].assign(name=k) 
                for k in solved_networks.keys()
            ], 
        axis=0
        )
        .pipe(
            cget.split_scenario_col,
            'name'
        )
        .drop('name', axis=1)
        .reset_index()
        .query("level_0 in ['Generator', 'StorageUnit']")
    )

    fig, ax0, ax1, ax2 = cplt.bar_plot_3row(figsize=(6,4), width_ratios=[1,1,10])

    # get relevant data
    ref = (
        generation_mix
        .loc[generation_mix['Scenario'] == 'Reference']
        .pivot_table(columns='level_1', index='Scenario', values='Supply')
        .div(1e6)
    )

    res = (
        generation_mix
        .loc[generation_mix['Scenario'] == '100% RES']
        .pivot_table(columns='level_1', index='Scenario', values='Supply')
        .div(1e6)
    )

    cfe = (
        generation_mix
        .loc[generation_mix['Scenario'].str.contains('CFE')]
        .pivot_table(columns='level_1', index='CFE Score', values='Supply')
        .div(1e6)
    )

    # save df
    (pd.concat([ref, res, cfe], axis=0)).to_csv(
        os.path.join(
            path_to_run_dir, 'results/11_system_generation.csv'
        ),
        index=True
    )

    # ---
    # plot

    colors = cplt.tech_color_palette()

    ref.plot(kind='bar', stacked=True, ax=ax0, legend=False, color=[colors.get(x, '#333333') for x in res.columns])
    res.plot(kind='bar', stacked=True, ax=ax1, legend=False, color=[colors.get(x, '#333333') for x in res.columns])
    cfe.plot(kind='bar', stacked=True, ax=ax2, legend=True, color=[colors.get(x, '#333333') for x in res.columns])

    ax0.set_ylabel('Generation [TWh]', fontproperties=work_sans_font)

    ax0.set_xlabel('')
    ax1.set_xlabel('')
    ax2.set_xlabel('CFE Score [%]', fontproperties=work_sans_font)

    for ax in [ax0, ax1, ax2]:
        # set y-axis grid
        ax.yaxis.grid(True, linestyle=':', linewidth=0.5)
        for label in ax.get_yticklabels():
            label.set_fontproperties(work_sans_font)
        # Rotate x-ticks
        ax.set_xticklabels(ax.get_xticklabels(), rotation=0, fontproperties=work_sans_font)
        # despine
        sns.despine(ax=ax, left=False)

    # Adjust horizontal space between ax0 and ax1
    fig.subplots_adjust(wspace=0.1)
    # Remove legend title and box
    handles, labels = ax2.get_legend_handles_labels()
    order = [cfe.columns.tolist().index(label) for label in labels if label in cfe.columns]
    sorted_handles_labels = sorted(zip(order, handles, labels), key=lambda x: -x[0])
    sorted_handles, sorted_labels = zip(*[(h, l) for _, h, l in sorted_handles_labels])

    legend = ax2.legend(sorted_handles, sorted_labels, loc='center left', bbox_to_anchor=(1, 0.5), ncol=1)
    legend.set_title(None)
    legend.get_frame().set_linewidth(0)

    # Set font of the legend
    for text in legend.get_texts():
        text.set_fontproperties(work_sans_font)

    # save plot
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/11_system_generation.png'
        ),
        bbox_inches='tight'
    )
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/11_system_generation.svg'
        ),
        bbox_inches='tight'
    )

def plot_system_capacity_mix(solved_networks, path_to_run_dir, work_sans_font):
    """
    Plot system capacity mix by scenario.
    """
    # ------------------------------------------------------------------
    # System capacity mix by scenario
    print('Creating system capacity mix plot')

    capacity_mix = (
        pd.concat(
            [
                solved_networks[k].statistics()[['Optimal Capacity']].assign(name=k) 
                for k in solved_networks.keys()
            ], 
        axis=0
        )
        .pipe(
            cget.split_scenario_col,
            'name'
        )
        .drop('name', axis=1)
        .reset_index()
        .query("level_0 in ['Generator', 'StorageUnit']")
    )

    fig, ax0, ax1, ax2 = cplt.bar_plot_3row(figsize=(6,4), width_ratios=[1,1,10])

    # get relevant data
    ref = (
        capacity_mix
        .loc[capacity_mix['Scenario'] == 'Reference']
        .pivot_table(columns='level_1', index='Scenario', values='Optimal Capacity')
        .div(1e3)
    )

    res = (
        capacity_mix
        .loc[capacity_mix['Scenario'] == '100% RES']
        .pivot_table(columns='level_1', index='Scenario', values='Optimal Capacity')
        .div(1e3)
    )

    cfe = (
        capacity_mix
        .loc[capacity_mix['Scenario'].str.contains('CFE')]
        .pivot_table(columns='level_1', index='CFE Score', values='Optimal Capacity')
        .div(1e3)
    )

    # save df
    (pd.concat([ref, res, cfe], axis=0)).to_csv(
        os.path.join(
            path_to_run_dir, 'results/12_system_capacity.csv'
        ),
        index=True
    )

    # ---
    # plot

    colors = cplt.tech_color_palette()

    ref.plot(kind='bar', stacked=True, ax=ax0, legend=False, color=[colors.get(x, '#333333') for x in res.columns])
    res.plot(kind='bar', stacked=True, ax=ax1, legend=False, color=[colors.get(x, '#333333') for x in res.columns])
    cfe.plot(kind='bar', stacked=True, ax=ax2, legend=True, color=[colors.get(x, '#333333') for x in res.columns])

    ax0.set_ylabel('Capacity [GW]', fontproperties=work_sans_font)

    ax0.set_xlabel('')
    ax1.set_xlabel('')
    ax2.set_xlabel('CFE Score [%]', fontproperties=work_sans_font)

    for ax in [ax0, ax1, ax2]:
        # set y-axis grid
        ax.yaxis.grid(True, linestyle=':', linewidth=0.5)
        for label in ax.get_yticklabels():
            label.set_fontproperties(work_sans_font)
        # Rotate x-ticks
        ax.set_xticklabels(ax.get_xticklabels(), rotation=0, fontproperties=work_sans_font)
        # despine
        sns.despine(ax=ax, left=False)

    # Adjust horizontal space between ax0 and ax1
    fig.subplots_adjust(wspace=0.1)
    # Remove legend title and box
    handles, labels = ax2.get_legend_handles_labels()
    order = [cfe.columns.tolist().index(label) for label in labels if label in cfe.columns]
    sorted_handles_labels = sorted(zip(order, handles, labels), key=lambda x: -x[0])
    sorted_handles, sorted_labels = zip(*[(h, l) for _, h, l in sorted_handles_labels])

    legend = ax2.legend(sorted_handles, sorted_labels, loc='center left', bbox_to_anchor=(1, 0.5), ncol=1)
    legend.set_title(None)
    legend.get_frame().set_linewidth(0)

    # Set font of the legend
    for text in legend.get_texts():
        text.set_fontproperties(work_sans_font)

    # save plot
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/12_system_capacity.png'
        ),
        bbox_inches='tight'
    )
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/12_system_capacity.svg'
        ),
        bbox_inches='tight'
    )

def plot_ci_energy_balance(solved_networks, path_to_run_dir, work_sans_font):
    """
    Plot C&I energy balance by scenario.
    """
    # ------------------------------------------------------------------
    # C&I ENERGY BALANCE
    print('Creating C&I energy balance plot')

    fig, ax0, ax1 = cplt.bar_plot_2row(figsize=(6,4), width_ratios=[1,10])

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
        .mul(1e-6)
        .rename(index={0:'100% RES'})
    )

    cfe = (
        ci_procurement
        .query("Scenario.str.contains('CFE')")
        .sort_values('CFE Score')
        .drop(['Scenario'], axis=1)
        .set_index('CFE Score')
        .mul(1e-6)
    )

    # save df
    (pd.concat([res, cfe], axis=0)).to_csv(
        os.path.join(
            path_to_run_dir, 'results/05_ci_energy_balance.csv'
        ),
        index=True
    )

    # also save for later use
    energy_balance_df = pd.DataFrame(pd.concat([res, cfe], axis=0))
    energy_balance_df.index.name = 'Scenario'
    energy_balance_df.index = [
        idx if idx == '100% RES' else f"CFE-{int(round(float(idx), 0))}"
        for idx in energy_balance_df.index
    ]
    
    res.plot(kind='bar', stacked=True, ax=ax0, legend=False)
    cfe.plot(kind='bar', stacked=True, ax=ax1, legend=True)

    ax0.set_ylabel('C&I Procurement Mix (TWh)', fontproperties=work_sans_font)
    ax1.set_xlabel('CFE Score [%]', fontproperties=work_sans_font)

    for ax in [ax0, ax1]:
        ax.set_xticklabels(ax.get_xticklabels(), rotation=0, fontproperties=work_sans_font)
        for label in ax.get_yticklabels():
            label.set_fontproperties(work_sans_font)
        ax.yaxis.grid(True, linestyle=':', linewidth=0.5)
        sns.despine(ax=ax, left=False)

    # Remove legend title and box
    legend = ax1.legend(loc='center left', bbox_to_anchor=(1, 0.5), ncol=1)
    legend.set_title(None)
    legend.get_frame().set_linewidth(0)

    # Set font of the legend
    for text in legend.get_texts():
        text.set_fontproperties(work_sans_font)

    # Adjust horizontal space between ax0 and ax1
    fig.subplots_adjust(wspace=0.1)

    # save plot
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/05_ci_energy_balance.png'
        ),
        bbox_inches='tight'
    )
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/05_ci_energy_balance.svg'
        ),
        bbox_inches='tight'
    )

def plot_ci_unit_cost_of_electricity(solved_networks, path_to_run_dir, work_sans_font):
    """
    Plot unit cost of electricity (USD/MWh) for C&I by scenario.
    This is calculated assuming that import and export costs are as per the model marginal price.

    PPA unit costs are equal to (PPA costs + PPA revenue)/PPA generation. This includes export revenue.
    Import unit costs are equal to (import costs)/import generation.

    Each unit cost is weighted by the proportion of C&I load met by PPA generators, 
    and the proportion met by energy imported, and then added together.
    """
    # ------------------------------------------------------------------
    # Unit cost of electricity (currency/MWh)
    print('Creating unit cost of electricity plot with marginal prices')

    fig, ax0, ax1 = cplt.bar_plot_2row(figsize=(6,4), width_ratios=[1,10])

    ci_carriers = cget.get_ci_carriers(solved_networks['n_bf'])

    cost_summary = (
        pd.concat(
            [
                cget.get_ci_cost_summary(
                    solved_networks[k]
                )
                .assign(name=k)
                .assign(ci_load = n.loads_t.p.filter(regex='C&I').sum().sum())
                for k, n in solved_networks.items()
            ]
        )
        .pipe(
            cget.split_scenario_col,
            'name',
        )
        .drop('name', axis=1)
        .sort_values('CFE Score')
        .merge(ci_carriers, left_on='carrier', right_index=True, how='left')
        .assign(carrier=lambda df: df['nice_name'].combine_first(df['carrier']))
    )
    cost_summary['CFE Score'] = cost_summary['CFE Score'].fillna(0)

    unit_cost_denominator = (
        cost_summary[cost_summary.index.str.contains('Grid Imports|Grid Exports')]
        .loc[:, ['dispatch', 'ci_load', 'Scenario', 'CFE Score']]
        .reset_index()
        .rename(columns={'index': 'flow'})
        .pivot_table(index=['CFE Score', 'Scenario', 'ci_load'], columns='flow', values='dispatch')
        .reset_index()
        .rename(columns=lambda x: 'grid_exports' if 'Grid Exports' in str(x) else x)
        .rename(columns=lambda x: 'grid_imports' if 'Grid Imports' in str(x) else x)
        .rename_axis(columns=None)
        .assign(ppa_weighting=lambda df: (df['ci_load'] - df['grid_imports'])/df['ci_load'])
        .assign(import_weighting=lambda df: df['grid_imports'] / df['ci_load'])
    )

    unit_cost = (
        cost_summary[~cost_summary.index.str.contains('Charge|Discharge')]
        .assign(carrier=lambda df: df['carrier'].where(~df.index.str.contains('Grid Exports'), 'Grid Exports'))
        .assign(carrier=lambda df: df['carrier'].where(~df.index.str.contains('Grid Imports'), 'Grid Imports'))
        .groupby(['carrier', 'CFE Score', 'Scenario'], dropna=False)[['capex', 'opex', 'import_cost', 'export_revenue']].sum()
        .assign(total_costs=lambda df: df[['capex', 'opex', 'import_cost', 'export_revenue']].sum(axis=1))
        .reset_index()
        .merge(unit_cost_denominator, left_on = ['Scenario','CFE Score'], right_on = ['Scenario','CFE Score'])
        .sort_values(['CFE Score','Scenario','carrier'])
        .assign(
            import_unit_cost=lambda df: np.where(
                df['carrier'] == 'Grid Imports',
                df['import_weighting'] * (1/df['grid_imports']) * df['import_cost'],
                0
            ),
            ppa_unit_cost=lambda df: np.where(
                df['carrier'] != 'Grid Imports',
                (1/(df['ci_load'] - df['grid_imports'] + df['grid_exports'])) * df['ppa_weighting'] * df['total_costs'],
                0
            ),
            export_unit_cost=lambda df: np.where(
                df['carrier'] == 'Grid Exports',
                (1/(df['ci_load'] - df['grid_imports'] + df['grid_exports'])) * df['ppa_weighting'] * df['export_revenue'],
                0
            )
        )
        .fillna(0)
        # We calculate unit costs in two ways:
        # unit cost a (i.e. where the PPA manager handles PPA supply and export revenue, and the C&I consumer manages imports and import costs themselves)
        # unit cost b (where the PPA manager handles everything on behalf of the C&I consumer, with all costs divided by all electricity delivered)
        .assign(unit_cost_a=lambda df: df['ppa_unit_cost'] + df['import_unit_cost'] + df['export_unit_cost'])
        .assign(unit_cost_b=lambda df: (df['capex'] + df['opex'] + df['import_cost'] + df['export_revenue'])/(df['ci_load'] + df['grid_exports']))
    )

    ### Plot unit cost a
    res_unit_cost = (
        unit_cost
        .loc[unit_cost['unit_cost_a'] != 0]
        .loc[unit_cost['Scenario'] == '100% RES']
        .loc[:, ['CFE Score', 'carrier', 'unit_cost_a']]
        .pivot_table(index='CFE Score', columns='carrier', values='unit_cost_a')
        .assign(**{'Net Cost': lambda df: df.sum(axis=1)})
        .rename(index={0:'100% RES'})
        # .set_index('100% RES')
    )
    print(res_unit_cost)

    cfe_unit_cost = (
        unit_cost
        .loc[unit_cost['unit_cost_a'] != 0]
        .query("Scenario.str.contains('CFE')")
        .sort_values('CFE Score')
        .loc[:, ['CFE Score', 'carrier', 'unit_cost_a']]
        .pivot_table(index='CFE Score', columns='carrier', values='unit_cost_a')
        .assign(**{'Net Cost': lambda df: df.sum(axis=1)})
    )

    # save df
    (pd.concat([res_unit_cost, cfe_unit_cost], axis=0)).to_csv(os.path.join(path_to_run_dir, 'results/06a_unit_cost.csv'), index=True)

    colors = cplt.tech_color_palette()
    res_unit_cost.drop(columns=['Net Cost'], errors='ignore').plot(
        kind='bar', stacked=True, ax=ax0, legend=False,
        color=[colors.get(x, '#333333') for x in res_unit_cost.columns if x != 'Net Cost']
    )
    cfe_unit_cost.drop(columns=['Net Cost'], errors='ignore').plot(
        kind='bar', stacked=True, ax=ax1, legend=True,
        color=[colors.get(x, '#333333') for x in cfe_unit_cost.columns if x != 'Net Cost']
    )
    
    ax0.scatter(
        x=res_unit_cost.index,
        y=res_unit_cost['Net Cost'],
        color='black',
        marker='x',
        s=40,
        label='Net Cost'
    )

    ax1.scatter(
        x=np.arange(len(cfe_unit_cost)),
        y=cfe_unit_cost['Net Cost'],
        color='black',
        marker='x',
        s=40,
        label='Net Cost'
    )
    
    ax0.set_ylabel('Unit Cost (USD/MWh)', fontproperties=work_sans_font)
    ax1.set_xlabel('CFE Score [%]', fontproperties=work_sans_font)
    ax0.set_xlabel('')

    for ax in [ax0, ax1]:
        ax.set_xticklabels(ax.get_xticklabels(), rotation=0, fontproperties=work_sans_font)
        for label in ax.get_yticklabels():
            label.set_fontproperties(work_sans_font)
        ax.yaxis.grid(True, linestyle=':', linewidth=0.5)
        sns.despine(ax=ax, left=False)

    # Remove legend title and box, make sure labels are displayed in the same order as in the plot
    handles, labels = ax1.get_legend_handles_labels()
    order = [cfe_unit_cost.columns.tolist().index(label) for label in labels if label in cfe_unit_cost.columns]
    sorted_handles_labels = sorted(zip(order, handles, labels), key=lambda x: -x[0])
    sorted_handles, sorted_labels = zip(*[(h, l) for _, h, l in sorted_handles_labels])

    legend = ax1.legend(sorted_handles, sorted_labels, bbox_to_anchor=(1, 0.5), ncol=1)
    legend.set_title(None)
    legend.get_frame().set_linewidth(0)

    # Set font of the legend
    for text in legend.get_texts():
        text.set_fontproperties(work_sans_font)

    # Adjust horizontal space between ax0 and ax1
    fig.subplots_adjust(wspace=0.1)

    # save plot
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/06a_unit_cost.png'
        ),
        bbox_inches='tight'
    )

     # save plot
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/06a_unit_cost.svg'
        ),
        bbox_inches='tight'
    )

     ### Plot unit cost b
    fig, ax0, ax1 = cplt.bar_plot_2row(figsize=(6,4), width_ratios=[1,10])

    res_unit_cost = (
        unit_cost
        .loc[unit_cost['unit_cost_b'] != 0]
        .loc[unit_cost['Scenario'] == '100% RES']
        .loc[:, ['CFE Score', 'carrier', 'unit_cost_b']]
        .pivot_table(index='CFE Score', columns='carrier', values='unit_cost_b')
        .assign(**{'Net Cost': lambda df: df.sum(axis=1)})
        .rename(index={0:'100% RES'})
        # .set_index('100% RES')
    )
    print(res_unit_cost)

    cfe_unit_cost = (
        unit_cost
        .loc[unit_cost['unit_cost_b'] != 0]
        .query("Scenario.str.contains('CFE')")
        .sort_values('CFE Score')
        .loc[:, ['CFE Score', 'carrier', 'unit_cost_b']]
        .pivot_table(index='CFE Score', columns='carrier', values='unit_cost_b')
        .assign(**{'Net Cost': lambda df: df.sum(axis=1)})
    )

    # save df
    (pd.concat([res_unit_cost, cfe_unit_cost], axis=0)).to_csv(os.path.join(path_to_run_dir, 'results/06b_unit_cost.csv'), index=True)

    colors = cplt.tech_color_palette()
    res_unit_cost.drop(columns=['Net Cost'], errors='ignore').plot(
        kind='bar', stacked=True, ax=ax0, legend=False,
        color=[colors.get(x, '#333333') for x in res_unit_cost.columns if x != 'Net Cost']
    )
    cfe_unit_cost.drop(columns=['Net Cost'], errors='ignore').plot(
        kind='bar', stacked=True, ax=ax1, legend=True,
        color=[colors.get(x, '#333333') for x in cfe_unit_cost.columns if x != 'Net Cost']
    )
    
    ax0.scatter(
        x=res_unit_cost.index,
        y=res_unit_cost['Net Cost'],
        color='black',
        marker='x',
        s=40,
        label='Net Cost'
    )

    ax1.scatter(
        x=np.arange(len(cfe_unit_cost)),
        y=cfe_unit_cost['Net Cost'],
        color='black',
        marker='x',
        s=40,
        label='Net Cost'
    )
    
    ax0.set_ylabel('Unit Cost (USD/MWh)', fontproperties=work_sans_font)
    ax1.set_xlabel('CFE Score [%]', fontproperties=work_sans_font)
    ax0.set_xlabel('')

    for ax in [ax0, ax1]:
        ax.set_xticklabels(ax.get_xticklabels(), rotation=0, fontproperties=work_sans_font)
        for label in ax.get_yticklabels():
            label.set_fontproperties(work_sans_font)
        ax.yaxis.grid(True, linestyle=':', linewidth=0.5)
        sns.despine(ax=ax, left=False)

    # Remove legend title and box, make sure labels are displayed in the same order as in the plot
    handles, labels = ax1.get_legend_handles_labels()
    order = [cfe_unit_cost.columns.tolist().index(label) for label in labels if label in cfe_unit_cost.columns]
    sorted_handles_labels = sorted(zip(order, handles, labels), key=lambda x: -x[0])
    sorted_handles, sorted_labels = zip(*[(h, l) for _, h, l in sorted_handles_labels])

    legend = ax1.legend(sorted_handles, sorted_labels, bbox_to_anchor=(1, 0.5), ncol=1)
    legend.set_title(None)
    legend.get_frame().set_linewidth(0)

    # Set font of the legend
    for text in legend.get_texts():
        text.set_fontproperties(work_sans_font)

    # Adjust horizontal space between ax0 and ax1
    fig.subplots_adjust(wspace=0.1)

    # save plot
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/06b_unit_cost.png'
        ),
        bbox_inches='tight'
    )

     # save plot
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/06b_unit_cost.svg'
        ),
        bbox_inches='tight'
    )


def plot_ci_unit_cost_of_electricity_alt(solved_networks, 
                                         path_to_run_dir, 
                                         import_tariff, 
                                         export_tariff,
                                         work_sans_font):
    """
    Plot unit cost of electricity (USD/MWh) for C&I by scenario.
    This uses an alternative calculation, where the import and export cost are user inputs
    This reflects real world tariffs instead of marginal pricing as calculated by the model

    PPA unit costs are equal to (PPA costs + PPA revenue)/PPA generation. This includes export revenue.
    Import unit costs are equal to (import costs)/import generation.

    Each unit cost is weighted by the proportion of C&I load met by PPA generators, 
    and the proportion met by energy imported, and then added together.
    """
    # ------------------------------------------------------------------
    # Unit cost of electricity (currency/MWh)
    print('Creating unit cost of electricity plot with user-defined tariffs')

    ci_carriers = cget.get_ci_carriers(solved_networks['n_bf'])

    cost_summary = (
        pd.concat(
            [
                cget.get_ci_cost_summary(
                    solved_networks[k]
                )
                .assign(name=k)
                .assign(ci_load = n.loads_t.p.filter(regex='C&I').sum().sum())
                for k, n in solved_networks.items()
            ]
        )
        .pipe(
            cget.split_scenario_col,
            'name',
        )
        .drop('name', axis=1)
        .sort_values('CFE Score')
        .merge(ci_carriers, left_on='carrier', right_index=True, how='left')
        .assign(carrier=lambda df: df['nice_name'].combine_first(df['carrier']))
    )
    cost_summary['CFE Score'] = cost_summary['CFE Score'].fillna(0)

    unit_cost_denominator = (
        cost_summary[cost_summary.index.str.contains('Grid Imports|Grid Exports')]
        .loc[:, ['dispatch', 'ci_load', 'Scenario', 'CFE Score']]
        .reset_index()
        .rename(columns={'index': 'flow'})
        .pivot_table(index=['CFE Score', 'Scenario', 'ci_load'], columns='flow', values='dispatch')
        .reset_index()
        .rename(columns=lambda x: 'grid_exports' if 'Grid Exports' in str(x) else x)
        .rename(columns=lambda x: 'grid_imports' if 'Grid Imports' in str(x) else x)
        .rename_axis(columns=None)
        .assign(ppa_weighting=lambda df: (df['ci_load'] - df['grid_imports'])/df['ci_load'])
        .assign(import_weighting=lambda df: df['grid_imports'] / df['ci_load'])
    )

    unit_cost = (
        cost_summary[~cost_summary.index.str.contains('Charge|Discharge')]
        .assign(carrier=lambda df: df['carrier'].where(~df.index.str.contains('Grid Exports'), 'Grid Exports'))
        .assign(carrier=lambda df: df['carrier'].where(~df.index.str.contains('Grid Imports'), 'Grid Imports'))
        .groupby(['carrier', 'CFE Score', 'Scenario'], dropna=False)[['dispatch', 'capex', 'opex', 'import_cost', 'export_revenue']].sum()
        .assign(total_costs=lambda df: df[['capex', 'opex']].sum(axis=1))
        .reset_index()
        .merge(unit_cost_denominator, left_on = ['Scenario','CFE Score'], right_on = ['Scenario','CFE Score'])
        .sort_values(['CFE Score','Scenario','carrier'])
        .assign(
            import_unit_cost=lambda df: np.where(
                df['carrier'] == 'Grid Imports',
                df['import_weighting'] * import_tariff,
                0
            ),
            ppa_unit_cost=lambda df: np.where(
                ~df['carrier'].isin(['Grid Imports', 'Grid Exports']),
                ((1/(df['ci_load'] - df['grid_imports'] + df['grid_exports']))
                * df['ppa_weighting'] 
                * df['total_costs']),
                # + grid_charges,
                0
            ),
            export_unit_cost=lambda df: np.where(
                df['carrier'] == 'Grid Exports',
                (1/(df['ci_load'] - df['grid_imports'] + df['grid_exports'])) * df['ppa_weighting'] * df['grid_exports'] * -1 * export_tariff,
                0
            )
        )
        .fillna(0)
        .assign(unit_cost=lambda df: df['ppa_unit_cost'] + df['import_unit_cost'] + df['export_unit_cost'])
    )

    res_unit_cost = (
        unit_cost
        .loc[unit_cost['unit_cost'] != 0]
        .loc[unit_cost['Scenario'] == '100% RES']
        .loc[:, ['CFE Score', 'carrier', 'unit_cost']]
        .pivot_table(index='CFE Score', columns='carrier', values='unit_cost')
        .assign(**{'Net Cost': lambda df: df.sum(axis=1)})
        .rename(index={0:'100% RES'})
        # .set_index('100% RES')
    )

    cfe_unit_cost = (
        unit_cost
        .loc[unit_cost['unit_cost'] != 0]
        .query("Scenario.str.contains('CFE')")
        .sort_values('CFE Score')
        .loc[:, ['CFE Score', 'carrier', 'unit_cost']]
        .pivot_table(index='CFE Score', columns='carrier', values='unit_cost')
        .assign(**{'Net Cost': lambda df: df.sum(axis=1)})
    )

    # save df
    (pd.concat([res_unit_cost, cfe_unit_cost], axis=0)).round(2).to_csv(os.path.join(path_to_run_dir, 'results/06c_unit_cost.csv'), index=True)

    fig, ax0, ax1 = cplt.bar_plot_2row(figsize=(6,4), width_ratios=[1,10])
    colors = cplt.tech_color_palette()
    res_unit_cost.drop(columns=['Net Cost'], errors='ignore').plot(
        kind='bar', stacked=True, ax=ax0, legend=False,
        color=[colors.get(x, '#333333') for x in res_unit_cost.columns if x != 'Net Cost']
    )
    cfe_unit_cost.drop(columns=['Net Cost'], errors='ignore').plot(
        kind='bar', stacked=True, ax=ax1, legend=True,
        color=[colors.get(x, '#333333') for x in cfe_unit_cost.columns if x != 'Net Cost']
    )
    
    ax0.scatter(
        x=res_unit_cost.index,
        y=res_unit_cost['Net Cost'],
        color='black',
        marker='x',
        s=40,
        label='Net Cost'
    )

    ax1.scatter(
        x=np.arange(len(cfe_unit_cost)),
        y=cfe_unit_cost['Net Cost'],
        color='black',
        marker='x',
        s=40,
        label='Net Cost'
    )
    
    ax0.set_ylabel('Unit Cost (USD/MWh)', fontproperties=work_sans_font)
    ax1.set_xlabel('CFE Score [%]', fontproperties=work_sans_font)
    ax0.set_xlabel('')

    for ax in [ax0, ax1]:
        ax.set_xticklabels(ax.get_xticklabels(), rotation=0, fontproperties=work_sans_font)
        for label in ax.get_yticklabels():
            label.set_fontproperties(work_sans_font)
        ax.yaxis.grid(True, linestyle=':', linewidth=0.5)
        sns.despine(ax=ax, left=False)

    # Remove legend title and box, make sure labels are displayed in the same order as in the plot
    handles, labels = ax1.get_legend_handles_labels()
    order = [cfe_unit_cost.columns.tolist().index(label) for label in labels if label in cfe_unit_cost.columns]
    sorted_handles_labels = sorted(zip(order, handles, labels), key=lambda x: -x[0])
    sorted_handles, sorted_labels = zip(*[(h, l) for _, h, l in sorted_handles_labels])

    legend = ax1.legend(sorted_handles, sorted_labels, bbox_to_anchor=(1, 0.5), ncol=1)
    legend.set_title(None)
    legend.get_frame().set_linewidth(0)

    # Set font of the legend
    for text in legend.get_texts():
        text.set_fontproperties(work_sans_font)

    # Adjust horizontal space between ax0 and ax1
    fig.subplots_adjust(wspace=0.1)

    # save plot
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/06c_unit_cost.png'
        ),
        bbox_inches='tight'
    )

     # save plot
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/06c_unit_cost.svg'
        ),
        bbox_inches='tight'
    )

def plot_system_costs_vs_benefits(solved_networks, path_to_run_dir, work_sans_font):
    """
    Plot C&I costs vs benefits relative to reference scenario.
    """
    # ------------------------------------------------------------------
    # C&I costs vs benefits relative to reference scenario

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
    # save df
    cost_delta.round(1).to_csv(os.path.join(path_to_run_dir, 'results/13b_system_costs_benefits_raw.csv'), index=True)

    # Sum together columns with the same name under the 'variable' column index
    cost_delta = cost_delta.groupby(level=1, axis=1).sum()
    # cost_delta['Net Cost'] = cost_delta.sum(axis=1)
    cost_delta = cost_delta.loc[:, (cost_delta.sum(axis=0) != 0)]

    fig, ax0, ax1 = cplt.bar_plot_2row(figsize=(6,4), width_ratios=[1, 10])

    # set theme
    cplt.set_tz_theme()

    # plot 100% RES
    res = cost_delta.loc[['100% RES']].drop(columns=['Net Cost'], errors='ignore').div(1e9)
    res.plot(kind='bar', stacked=True, ax=ax0, legend=False)
    # add net cost marker
    ax0.scatter(x=res.index, y=[res.sum(axis=1)] * len(res.index), color='black', marker='x', linewidths=1)

    # plot cfe
    cfe = cost_delta.loc[cost_delta.index != '100% RES'].drop(columns=['Net Cost'], errors='ignore').div(1e9).copy()
    cfe.index = [int(i.replace('CFE-', '')) for i in cfe.index]
    cfe.sort_index(inplace=True)
    cfe.plot(kind='bar', stacked=True, ax=ax1, legend=True)
    # add net cost marker
    ax1.scatter(
        x=np.arange(len(cfe)),
        y=[cfe.sum(axis=1)],
        color='black',
        marker='x',
        linewidths=1,
        label='Net Cost'
    )

    # save df
    combined_df = pd.concat([res, cfe], axis=0).assign(**{'Net Cost': lambda df: df.sum(axis=1)}).round(2)
    combined_df.to_csv(os.path.join(path_to_run_dir, 'results/13a_system_costs_benefits.csv'), index=True)

    # formatting
    for ax in [ax0, ax1]:
        ax.yaxis.grid(True, linestyle=':', linewidth=0.5)
        ax.axhline(0, color='white', linewidth=0.8, linestyle='-')
        ax.set_xticklabels(ax.get_xticklabels(), rotation=0, fontproperties=work_sans_font)
        for label in ax.get_yticklabels():
            label.set_fontproperties(work_sans_font)

    ax0.set_xlabel('')
    ax0.set_ylabel('C&I Cost and Benefits\n[billion USD]', fontproperties=work_sans_font)

    ax1.set_xlabel('CFE Score [%]', fontproperties=work_sans_font)

    # Remove legend title and box, move legend to the right and outside the plot
    legend = ax1.legend(loc='center left', bbox_to_anchor=(1, 0.5), ncol=1)
    legend.set_title(None)
    legend.get_frame().set_linewidth(0)

    # Set font of the legend
    for text in legend.get_texts():
        text.set_fontproperties(work_sans_font)

    # save plot
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/13_system_costs_benefits.png'
        ),
        bbox_inches='tight'
    )

    # save plot
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/13_system_costs_benefits.svg'
        ),
        bbox_inches='tight'
    )

def plot_system_unit_cost_by_scenario(solved_networks, path_to_run_dir, work_sans_font):
    """
    Plot system costs ($/MWh) by scenario.
    """
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

    ax0.set_ylabel('C&I Electricity Cost [$/MWh]', fontproperties=work_sans_font)

    ax0.set_xlabel('')
    ax1.set_xlabel('CFE Score [%]', fontproperties=work_sans_font)

    for ax in [ax0, ax1]:
        # set y-axis grid
        ax.yaxis.grid(True, linestyle=':', linewidth=0.5)
        # Rotate x-ticks
        ax.set_xticklabels(ax.get_xticklabels(), rotation=0, fontproperties=work_sans_font)
        for label in ax.get_yticklabels():
            label.set_fontproperties(work_sans_font)
        # despine
        sns.despine(ax=ax, left=False)

    # Adjust horizontal space between ax0 and ax1
    fig.subplots_adjust(wspace=0.1)

    # Remove legend title and box
    legend = ax1.legend(loc='center left', bbox_to_anchor=(1, 0.5), ncol=1)
    legend.set_title(None)
    legend.get_frame().set_linewidth(0)

    # Set font of the legend
    for text in legend.get_texts():
        text.set_fontproperties(work_sans_font)

    # save plot
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/unit_cost_by_scenario.png'
        ),
        bbox_inches='tight'
    )

def plot_ci_curtailment(solved_networks, path_to_run_dir, work_sans_font):
    """
    Plot C&I curtailment for each scenario.
    """
    # ------------------------------------------------------------------
    # C&I CURTAILMENT
    print('Creating C&I curtailment plot')

    fig, ax0, ax1 = cplt.bar_plot_2row(figsize=(6,4), width_ratios=[1,10])
    colors = cplt.tech_color_palette()
    ci_carriers = cget.get_ci_carriers(solved_networks['n_bf'])

    curtailment_summary = (
        pd.concat(
            [
                cget.get_ci_cost_summary(
                    solved_networks[k]
                    )
                .assign(name=k)
                .assign(ci_load = n.loads_t.p.filter(regex='C&I').sum().sum())
                for k, n in solved_networks.items()
            ]
        )
        .pipe(
            cget.split_scenario_col,
            'name',
        )
        .drop('name', axis=1)
        .sort_values('CFE Score')
        .merge(ci_carriers, left_on='carrier', right_index=True, how='left')
        .assign(carrier=lambda df: df['nice_name'].combine_first(df['carrier']))
        .query("carrier != 'AC'")
        .query("potential_dispatch > 0")
        .loc[:, ['Scenario', 'CFE Score', 'carrier', 'dispatch', 'potential_dispatch', 'curtailment_perc']]
    )

    curtailment_summary.to_csv(
        os.path.join(
            path_to_run_dir, 'results/14_ci_curtailment.csv'
        ),
        index=False
    )

    curtailment_summary = curtailment_summary.loc[:, ['Scenario', 'CFE Score', 'carrier', 'curtailment_perc']]

    res = (
        curtailment_summary
        .loc[curtailment_summary['Scenario'] == '100% RES']
        .pivot_table(columns='carrier', index='Scenario', values='curtailment_perc')
        .multiply(100)
    )

    cfe = (
        curtailment_summary
        .loc[curtailment_summary['Scenario'].str.contains('CFE')]
        .pivot_table(columns='carrier', index='CFE Score', values='curtailment_perc')
        .multiply(100)
    )

    res.plot(kind='bar', ax=ax0, legend=True, color=[colors.get(x, '#333333') for x in res.columns])
    cfe.plot(kind='bar', ax=ax1, legend=True, color=[colors.get(x, '#333333') for x in cfe.columns])

    ax0.set_ylabel('Curtailment of C&I PPA generators [%]', fontproperties=work_sans_font)
    ax1.set_xlabel('CFE Score [%]', fontproperties=work_sans_font)
    ax0.set_xlabel('')

    for ax in [ax0, ax1]:
        ax.set_xticklabels(ax.get_xticklabels(), rotation=0, fontproperties=work_sans_font)
        for label in ax.get_yticklabels():
            label.set_fontproperties(work_sans_font)
        ax.yaxis.grid(True, linestyle=':', linewidth=0.5)
        sns.despine(ax=ax, left=False)

    # Remove legend title and box, make sure labels are displayed in the same order as in the plot
    handles, labels = ax1.get_legend_handles_labels()
    order = [cfe.columns.tolist().index(label) for label in labels if label in cfe.columns]
    sorted_handles_labels = sorted(zip(order, handles, labels), key=lambda x: -x[0])
    sorted_handles, sorted_labels = zip(*[(h, l) for _, h, l in sorted_handles_labels])
    ax0.legend_.remove() if ax0.legend_ is not None else None

    legend = ax1.legend(sorted_handles, sorted_labels, bbox_to_anchor=(1, 0.5), ncol=1)
    legend.set_title(None)
    legend.get_frame().set_linewidth(0)

    # Set font of the legend
    for text in legend.get_texts():
        text.set_fontproperties(work_sans_font)

    # Adjust horizontal space between ax0 and ax1
    fig.subplots_adjust(wspace=0.1)

    # save plot
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/14_ci_curtailment.png'
        ),
        bbox_inches='tight'
    )
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/14_ci_curtailment.svg'
        ),
        bbox_inches='tight'
    )


def plot_cfe_score_heatmaps(solved_networks, path_to_run_dir, run, work_sans_font_medium):
    """
    Plot heatmaps of CFE score for each scenario.
    """
    # ------------------------------------------------------------------
    # HEATMAP OF CFE SCORE
    print('Creating heatmap of CFE score')
    
    ci_carriers = cget.get_ci_carriers(solved_networks['n_bf'])
    ymax = cget.get_total_ci_procurement_cost(solved_networks['n_hm_CFE100_2030']).query("carrier.isin(@ci_carriers)")['annual_system_cost [M$]'].sum() / 1e3
    for k in solved_networks.keys():
        # get networks
        n_reference = solved_networks['n_bf'].copy()
        n = solved_networks[k].copy()
        # init fig
        fig, ax0, ax1 = cplt.plot_cfe_hmap(n, n_reference, ymax=ymax, fields_to_plot=ci_carriers, run=run, ci_identifier='C&I')

        # set fname
        if 'n_bf' in k:
            fname = '2030 Reference Scenario'
            ax0.set_title(f'{fname}', loc='left', fontproperties=work_sans_font_medium, fontsize=14)
        elif 'n_am' in k:
            fname = '100% Annual Matching'
            ax0.set_title(f'{fname}', loc='left', fontproperties=work_sans_font_medium, fontsize=14)
        elif 'n_hm' in k:
            fname = k.split('_')[2]
            cfe_score = int(fname.replace('CFE', ''))
            ax0.set_title(f'{cfe_score}% clean procurement: hour-by-hour\n\n', loc='left', fontproperties=work_sans_font_medium, fontsize=14)
        
        print(f'Plotting {fname} heatmap...')

        # save plot
        fig.savefig(
            os.path.join(
                path_to_run_dir, f'results/hmap_score_{fname}.png'
            ),
            bbox_inches='tight'
        )

def plot_monthly_cfe_score_heatmaps(solved_networks, path_to_run_dir, run, work_sans_font_medium):
    """
    Plot monthly heatmaps of CFE score for each scenario.
    """
    # ------------------------------------------------------------------
    # MONTHLY HEATMAP OF CFE SCORE
    print('Creating monthly heatmap of CFE score')
    for k in solved_networks.keys():
        n = solved_networks[k].copy()

        fig, ax = cplt.plot_monthly_cfe_hmap(n, run=run, ci_identifier='C&I')

        # set fname
        if 'n_bf' in k:
            fname = '2030 Reference Scenario'
            fig.suptitle(f'{fname}', y=0.95, fontsize=14)
        elif 'n_am' in k:
            fname = '100% Annual Matching'
            fig.suptitle(f'{fname}', y=0.95, fontsize=14)
        elif 'n_hm' in k:
            fname = k.split('_')[2]
            cfe_score = int(fname.replace('CFE',''))
            fig.suptitle(f'{cfe_score}% clean procurement: hour-by-hour\n\n', y=0.95, fontproperties=work_sans_font_medium, fontsize=14)

        # save plot
        fig.savefig(
            os.path.join(
                path_to_run_dir, f'results/monthly_hmap_score_{fname}.png'
            ),
            bbox_inches='tight'
        )