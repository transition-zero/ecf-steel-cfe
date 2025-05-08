import os

import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

from matplotlib.ticker import MaxNLocator

from . import plotting as cplt
from . import get as cget

def plot_results(path_to_run_dir: str, nodes_with_ci_loads):
    '''Plot results for a given run
    '''

    # set tz plotting theme
    cplt.set_tz_theme()
    # cplt.set_tz_theme()

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
    
    # ------------------------------------------------------------------
    # C&I Portfolio Capacity [GW]

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
    
    # save df
    (pd.concat([res, cfe], axis=0)).to_csv(
        os.path.join(
            path_to_run_dir, 'results/ci_capacity_by_scenario.csv'
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
            path_to_run_dir, 'results/ci_capacity_by_scenario.png'
        ),
        bbox_inches='tight'
    )
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/ci_capacity_by_scenario.svg'
        ),
        bbox_inches='tight'
    )
    
    # ------------------------------------------------------------------
    # Generation mix by scenario for C&I and parent node

    generation_mix = (
        pd.concat(
            [
                solved_networks[k].statistics(
                    groupby = ['bus','carrier']
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
            path_to_run_dir, 'results/ci_and_parent_generation.csv'
        ),
        index=True
    )

    fig, ax0, ax1, ax2 = cplt.bar_plot_3row(width_ratios=[1,1,10], figsize=(6,4))

    ref.plot(kind='bar', stacked=True, ax=ax0, legend=False, color=[colors.get(x, '#333333') for x in res.columns])
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
            path_to_run_dir, 'results/ci_and_parent_generation.png'
        ),
        bbox_inches='tight'
    ) 
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/ci_and_parent_generation.svg'
        ),
        bbox_inches='tight'
    )

    # ------------------------------------------------------------------
    # Capacity mix by scenario for C&I and parent node

    capacity_mix = (
        pd.concat(
            [
                solved_networks[k].statistics(
                    groupby = ['bus','carrier']
                    )
                    [['Optimal Capacity']].assign(name=k) 
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

    # fig, ax0, ax1, ax2 = cplt.bar_plot_3row(figsize=(6,4), width_ratios=[1,1,10])

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
            path_to_run_dir, 'results/ci_and_parent_capacity.csv'
        ),
        index=True
    )

    fig, ax0, ax1, ax2 = cplt.bar_plot_3row(width_ratios=[1,1,10], figsize=(6,4))

    ref.plot(kind='bar', stacked=True, ax=ax0, legend=False, color=[colors.get(x, '#333333') for x in res.columns])
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
            path_to_run_dir, 'results/ci_and_parent_capacity.png'
        ),
        bbox_inches='tight'
    )
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/ci_and_parent_capacity.svg'
        ),
        bbox_inches='tight'
    )

    # ------------------------------------------------------------------
    # C&I Portfolio Procurement cost [currency]

    print('Creating C&I portfolio procurement cost by scenario plot')

    fig, ax0, ax1 = cplt.bar_plot_2row(width_ratios=[1,10], figsize=(6,4))

    ci_procurement_cost = (
        pd.concat(
            [
                cget.get_total_ci_procurement_cost(
                    solved_networks[k],
                    solved_networks['n_bf']
                )
                # for k, n in solved_networks.items()
                # solved_networks[k]
                # .statistics.expanded_capacity()
                # .reset_index()
                # .rename(columns={0:'capacity'})
                .assign(name=k)
                for k, n in solved_networks.items()
            ]
        )
        .pipe(
            cget.split_scenario_col,
            'name',
        )
        .drop('name', axis=1)
        # .query("capacity != 0")
    )

    # pull out relevant data
    res_ci_costs = (
        ci_procurement_cost
        .loc[ci_procurement_cost['Scenario'] == '100% RES']
        .drop(['Scenario','CFE Score'], axis=1)
        .query(" ~carrier.isin(['Transmission']) ")
        .query("carrier in @ci_carriers")
        .pivot_table(columns='carrier', values='annual_system_cost [M$]')
        .rename(index={'annual_system_cost [M$]':'100% RES'})
    )

    cfe_ci_costs = (
        ci_procurement_cost
        .query("Scenario.str.contains('CFE')")
        .sort_values('CFE Score')
        .query(" ~carrier.isin(['Transmission']) ")
        .query("carrier in @ci_carriers")
        .pivot_table(index='CFE Score', columns='carrier', values='annual_system_cost [M$]')
    )

    # save df
    (pd.concat([res_ci_costs, cfe_ci_costs], axis=0)).to_csv(
        os.path.join(
            path_to_run_dir, 'results/ci_capacity_costs_by_scenario.csv'
        ),
        index=True
    )

    # save df
    (pd.concat([res_ci_costs, cfe_ci_costs], axis=0)).to_csv(
        os.path.join(
            path_to_run_dir, 'results/ci_capacity_costs_by_scenario.csv'
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
            path_to_run_dir, 'results/ci_capacity_costs_by_scenario.png'
        ),
        bbox_inches='tight'
    )
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/ci_capacity_costs_by_scenario.svg'
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
            path_to_run_dir, 'results/emissions_by_scenario.csv'
        ),
        index=True
    )

     # save df
    (pd.concat([res, cfe], axis=0)).to_csv(
        os.path.join(
            path_to_run_dir, 'results/emissions_by_scenario.csv'
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
            path_to_run_dir, 'results/emissions_by_scenario.png'
        ),
        bbox_inches='tight'
    )
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/emissions_by_scenario.svg'
        ),
        bbox_inches='tight'
    )

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
            path_to_run_dir, 'results/emissions_rate_by_scenario.csv'
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
            path_to_run_dir, 'results/emission_rate_by_scenario.png'
        ),
        bbox_inches='tight'
    )
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/emission_rate_by_scenario.svg'
        ),
        bbox_inches='tight'
    )

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
            path_to_run_dir, 'results/ci_emissions_rate_by_scenario.csv'
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
            path_to_run_dir, 'results/ci_emission_rate_by_scenario.png'
        ),
        bbox_inches='tight'
    )
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/ci_emission_rate_by_scenario.svg'
        ),
        bbox_inches='tight'
    )


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
            path_to_run_dir, 'results/cost_vs_cfe_tradeoff.csv'
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
            path_to_run_dir, 'results/cost_vs_cfe_tradeoff_stacked.png'
        ),
        bbox_inches='tight'
    )
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/cost_vs_cfe_tradeoff_stacked.svg'
        ),
        bbox_inches='tight'
    )

    # ------------------------------------------------------------------
    # Generation mix by scenario
    print('Creating generation mix plot')

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
            path_to_run_dir, 'results/generation_mix.csv'
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
            path_to_run_dir, 'results/generation_mix.png'
        ),
        bbox_inches='tight'
    )
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/generation_mix.svg'
        ),
        bbox_inches='tight'
    )

    # ------------------------------------------------------------------
    # Capacity mix by scenario
    print('Creating capacity maix plot')

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
            path_to_run_dir, 'results/capacity_mix.csv'
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
            path_to_run_dir, 'results/capacity_mix.png'
        ),
        bbox_inches='tight'
    )
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/capacity_mix.svg'
        ),
        bbox_inches='tight'
    )

    # # ------------------------------------------------------------------
    # # C&I costs vs benefits relative to reference scenario

    # cost_results = (
    #     pd.concat(
    #         [
    #             solved_networks[k].statistics()[['Capital Expenditure', 'Operational Expenditure']].assign(name=k) 
    #             for k in solved_networks.keys()
    #         ], 
    #     axis=0
    #     )
    #     .pipe(
    #         cget.split_scenario_col,
    #         'name'
    #     )
    #     .drop('name', axis=1)
    # )

    # # get results for reference scenario
    # ref = cost_results.query("Scenario == 'Reference'")

    # # loop through each scenario and calculate cost delta
    # cost_delta = pd.concat(
    #     [
    #         cost_results.query(f"Scenario == '{s}'")
    #         .assign(
    #             **{
    #                 'Capital Expenditure': lambda x: x['Capital Expenditure'] - ref['Capital Expenditure'].values,
    #                 'Operational Expenditure': lambda x: x['Operational Expenditure'] - ref['Operational Expenditure'].values
    #             }
    #         )
    #         for s in cost_results.Scenario.unique().tolist() if s != 'Reference'
    #     ],
    #     axis=0
    # )

    # cost_delta = (
    #     cost_delta
    #     .rename(columns={'Capital Expenditure': 'CapEx', 'Operational Expenditure': 'OpEx'})
    #     .reset_index()
    #     .rename(columns={'level_0' : 'Component', 'level_1' : 'Technology'})
    #     .melt(
    #         id_vars=['Scenario', 'Component', 'Technology'], 
    #         value_vars=['CapEx', 'OpEx']
    #     )
    #     .query(" ~Technology.isin(['Transmission', '-'])")
    #     .pivot_table(
    #         index='Scenario', 
    #         columns=['Technology','variable'], 
    #         values='value', 
    #         aggfunc='sum'
    #     )
    # )

    # cost_delta = cost_delta.loc[:, (cost_delta.sum(axis=0) != 0)]

    # fig, ax0, ax1 = cplt.bar_plot_2row(figsize=(10,4), width_ratios=[1, 10])

    # # set theme
    # cplt.set_tz_theme()

    # # plot 100% RES
    # res = cost_delta.loc[['100% RES']].div(1e9)
    # res.plot(kind='bar', stacked=True, ax=ax0, legend=False)
    # # add net cost marker
    # # ax0.scatter(x=res.index, y=[res.sum(axis=1)] * len(res.index), color='red', marker='s', edgecolors='black', linewidths=1)

    # # plot cfe
    # cfe = cost_delta.loc[cost_delta.index != '100% RES'].div(1e9).copy()
    # cfe.index = [int(i.replace('CFE-', '')) for i in cfe.index]
    # cfe.sort_index(inplace=True)
    # cfe.plot(kind='bar', stacked=True, ax=ax1, legend=True)

    # # formatting
    # for ax in [ax0, ax1]:
    #     ax.yaxis.grid(True, linestyle=':', linewidth=0.5)
    #     ax.axhline(0, color='white', linewidth=0.8, linestyle='-')
    #     ax.set_xticklabels(ax.get_xticklabels(), rotation=0, fontproperties=work_sans_font)
    #     for label in ax.get_yticklabels():
    #         label.set_fontproperties(work_sans_font)

    # ax0.set_xlabel('')
    # ax0.set_ylabel('C&I Cost and Benefits\n[billion USD]', fontproperties=work_sans_font)

    # ax1.set_xlabel('CFE Score [%]', fontproperties=work_sans_font)

    # # Remove legend title and box
    # legend = ax1.legend(ncol=2)
    # legend.set_title(None)
    # legend.get_frame().set_linewidth(0)

    # # Set font of the legend
    # for text in legend.get_texts():
    #     text.set_fontproperties(work_sans_font)

    # # save plot
    # fig.savefig(
    #     os.path.join(
    #         path_to_run_dir, 'results/cost_vs_benefit_by_scenario.png'
    #     ),
    #     bbox_inches='tight'
    # )

    # # ------------------------------------------------------------------
    # # System costs ($/MWh) by scenario

    # # stacked bar plot
    # costs = (
    #     pd.concat(
    #         [
    #             cget
    #             .get_unit_cost(solved_networks[k])
    #             .assign(name=k)
    #             for k, n in solved_networks.items()
    #         ]
    #     )
    #     .pipe(
    #         cget.split_scenario_col,
    #         'name',
    #     )
    #     .drop('name', axis=1)
    # )

    # costs = costs.query(" ~carrier.isin(['Transmission', '-']) ").reset_index(drop=True)

    # fig, ax0, ax1 = cplt.bar_plot_2row(figsize=(10,4), width_ratios=[1,10])

    # # get relevant data
    # ref = (
    #     costs
    #     .loc[costs['Scenario'] == 'Reference']
    #     .pivot_table(columns='carrier', index='Scenario', values='System Cost [$/MWh]')
    # )

    # res = (
    #     costs
    #     .loc[costs['Scenario'] == '100% RES']
    #     .pivot_table(columns='carrier', index='Scenario', values='System Cost [$/MWh]')
    # )

    # cfe = (
    #     costs
    #     .loc[costs['Scenario'].str.contains('CFE')]
    #     .pivot_table(columns='carrier', index='CFE Score', values='System Cost [$/MWh]')
    # )

    # # ---
    # # plot

    # colors = cplt.tech_color_palette()

    # #ref.plot(kind='bar', stacked=True, ax=ax0, legend=False, color=[colors.get(x, '#333333') for x in res.columns])
    # res.plot(kind='bar', stacked=True, ax=ax0, legend=False, color=[colors.get(x, '#333333') for x in res.columns])
    # cfe.plot(kind='bar', stacked=True, ax=ax1, legend=True, color=[colors.get(x, '#333333') for x in res.columns])

    # ax0.set_ylabel('C&I Electricity Cost [$/MWh]', fontproperties=work_sans_font)

    # ax0.set_xlabel('')
    # ax1.set_xlabel('CFE Score [%]', fontproperties=work_sans_font)

    # for ax in [ax0, ax1]:
    #     # set y-axis grid
    #     ax.yaxis.grid(True, linestyle=':', linewidth=0.5)
    #     # Rotate x-ticks
    #     ax.set_xticklabels(ax.get_xticklabels(), rotation=0, fontproperties=work_sans_font)
    #     for label in ax.get_yticklabels():
    #         label.set_fontproperties(work_sans_font)
    #     # despine
    #     sns.despine(ax=ax, left=False)

    # # Adjust horizontal space between ax0 and ax1
    # fig.subplots_adjust(wspace=0.1)

    # # Remove legend title and box
    # legend = ax1.legend(loc='center left', bbox_to_anchor=(1, 0.5), ncol=1)
    # legend.set_title(None)
    # legend.get_frame().set_linewidth(0)

    # # Set font of the legend
    # for text in legend.get_texts():
    #     text.set_fontproperties(work_sans_font)

    # # save plot
    # fig.savefig(
    #     os.path.join(
    #         path_to_run_dir, 'results/unit_cost_by_scenario.png'
    #     ),
    #     bbox_inches='tight'
    # )

    # ------------------------------------------------------------------
    # Unit cost of CFE generation (currency/MWh)
    # This is still a WIP, requires function to amortise capital costs

    # fig, ax0, ax1 = cplt.bar_plot_2row(width_ratios=[1,10], figsize=(6,4))

    # ci_procurement_cost = (
    #     pd.concat(
    #         [
    #             cget.get_total_ci_procurement_cost(
    #                 solved_networks[k],
    #                 solved_networks['n_bf']
    #             )
    #             # for k, n in solved_networks.items()
    #             # solved_networks[k]
    #             # .statistics.expanded_capacity()
    #             # .reset_index()
    #             # .rename(columns={0:'capacity'})
    #             .assign(name=k)
    #             for k, n in solved_networks.items()
    #         ]
    #     )
    #     .pipe(
    #         cget.split_scenario_col,
    #         'name',
    #     )
    #     .drop('name', axis=1)
    #     # .query("capacity != 0")
    # )

    # # pull out cost data
    # res_ci_costs = (
    #     ci_procurement_cost
    #     .loc[ci_procurement_cost['Scenario'] == '100% RES']
    #     .drop(['Scenario','CFE Score'], axis=1)
    #     .query(" ~carrier.isin(['Transmission']) ")
    #     .query("carrier in @ci_carriers")
    #     .pivot_table(columns='carrier', values='annual_system_cost [M$]')
    #     .rename(index={'annual_system_cost [M$]':'100% RES'})
    #     .assign(Total=lambda df: df.sum(axis=1))
    # )
    # cfe_ci_costs = (
    #     ci_procurement_cost
    #     .query("Scenario.str.contains('CFE')")
    #     .sort_values('CFE Score')
    #     .query(" ~carrier.isin(['Transmission']) ")
    #     .query("carrier in @ci_carriers")
    #     .pivot_table(index='CFE Score', columns='carrier', values='annual_system_cost [M$]')
    #     .assign(Total=lambda df: df.sum(axis=1))
    # )

    # # pull out C%I bus generation data
    # ci_gen = (
    #     pd.concat(
    #         [
    #             cget.get_ci_generation(
    #                 solved_networks[k]
    #             )
    #             # for k, n in solved_networks.items()
    #             # solved_networks[k]
    #             # .statistics.expanded_capacity()
    #             # .reset_index()
    #             # .rename(columns={0:'capacity'})
    #             .assign(name=k)
    #             for k, n in solved_networks.items()
    #         ]
    #     )
    #     .pipe(
    #         cget.split_scenario_col,
    #         'name',
    #     )
    #     .drop('name', axis=1)
    # )

    # # Merge res_ci_costs with ci_gen
    # res_ci_costs_merged = (
    #     res_ci_costs
    #     .merge(
    #         ci_gen.set_index('Scenario'),
    #         left_index=True,
    #         right_index=True,
    #         suffixes=('_costs', '_gen')
    #     )
    #     .assign(Unit_Cost=lambda df: df['Total'] / df['ci_generation'])
    # )

    # # Merge cfe_ci_costs with ci_gen
    # cfe_ci_costs_merged = (
    #     cfe_ci_costs
    #     .merge(
    #         ci_gen.set_index('CFE Score'),
    #         left_index=True,
    #         right_index=True,
    #         suffixes=('_costs', '_gen')
    #     )
    #     .assign(Unit_Cost=lambda df: df['Total'] / df['ci_generation'])
    # )

    # Concatenate res_ci_costs and cfe_ci_costs
    # all_ci_costs = pd.concat([res_ci_costs, cfe_ci_costs], axis=0).reset_index()
    # print(all_ci_costs)

    # Merge all_ci_costs on its index with ci_gen on the 'Scenario' column
    # merged_data = (
    #     all_ci_costs
    #     .set_index('index')
    #     .merge(
    #         ci_gen.set_index('Scenario'),
    #         left_index=True,
    #         right_index=True,
    #         suffixes=('_costs', '_gen')
    #     )
    # )
    # print(merged_data)

    # ------------------------------------------------------------------
    # C&I ENERGY BALANCE
    print('Creating C&I energy balance plot')

    fig, ax0, ax1 = cplt.bar_plot_2row(figsize=(6,4), width_ratios=[1,10])
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

    # save df
    (pd.concat([res, cfe], axis=0)).to_csv(
        os.path.join(
            path_to_run_dir, 'results/ci_energy_balance_by_scenario.csv'
        ),
        index=True
    )

    res.plot(kind='bar', stacked=True, ax=ax0, legend=False)
    cfe.plot(kind='bar', stacked=True, ax=ax1, legend=True)

    ax0.set_ylabel('C&I Procurement Mix\n[% of load]', fontproperties=work_sans_font)
    ax1.set_xlabel('CFE Score [%]', fontproperties=work_sans_font)

    for ax in [ax0, ax1]:
        ax.set_xticklabels(ax.get_xticklabels(), rotation=0, fontproperties=work_sans_font)
        for label in ax.get_yticklabels():
            label.set_fontproperties(work_sans_font)
        ax.yaxis.grid(True, linestyle=':', linewidth=0.5)
        sns.despine(ax=ax, left=False)

    # Remove legend title and box
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
            path_to_run_dir, 'results/ci_energy_balance_by_scenario.png'
        ),
        bbox_inches='tight'
    )
    fig.savefig(
        os.path.join(
            path_to_run_dir, 'results/ci_energy_balance_by_scenario.svg'
        ),
        bbox_inches='tight'
    )

    # ------------------------------------------------------------------
    # HEATMAP OF CFE SCORE
    print('Creating heatmap of CFE score')
    ymax = cget.get_total_ci_procurement_cost(solved_networks['n_hm_CFE100_2030'],solved_networks['n_bf']).query("carrier.isin(@ci_carriers)")['annual_system_cost [M$]'].sum() / 1e3
    for k in solved_networks.keys():
        # get networks
        n_reference = solved_networks['n_bf'].copy()
        n = solved_networks[k].copy()
        # init fig
        fig, ax0, ax1 = cplt.plot_cfe_hmap(n, n_reference, ymax=ymax, fields_to_plot=ci_carriers, ci_identifier='C&I')

        # set fname
        if 'n_bf' in k:
            fname = '2030 Reference Scenario'
            ax0.set_title(f'{fname}', loc='center', fontsize=14)
        elif 'n_am' in k:
            fname = '100% Annual Matching'
            ax0.set_title(f'{fname}', loc='center', fontsize=14)
        elif 'n_hm' in k:
            fname = k.split('_')[2]
            cfe_score = int( fname.replace('CFE','') )
            ax0.set_title(f'{cfe_score}% clean procurement: hour-by-hour\n\n', loc='left', fontproperties=work_sans_font_medium, fontsize=14)
        
        print(f'Plotting {fname} heatmap...')

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