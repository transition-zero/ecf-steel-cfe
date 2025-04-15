import pandas as pd
import seaborn as sns
import plotly.express as px
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.font_manager as fm

from . import get as cget
from . import plotting as cplt

def plot_cfe_hmap(n, n_reference, ymax, ci_identifier='C&I'):
    '''Plot the CFE score as a heatmap
    '''

    # Add Work Sans font to matplotlib
    work_sans_path_light = './assets/WorkSans-Light.ttf'
    work_sans_path_medium = './assets/WorkSans-Medium.ttf'
    work_sans_font = fm.FontProperties(fname=work_sans_path_light)
    work_sans_font_medium = fm.FontProperties(fname=work_sans_path_medium)

    cfe_t = cget.get_cfe_score_ts(n, ci_identifier)
    cfe_t.index = cfe_t.index #.tz_localize('UTC').tz_convert('Asia/Singapore')
    cfe_t['Hour'] = cfe_t.index.hour + 1
    cfe_t['Day'] = cfe_t.index.day
    cfe_t['Month'] = cfe_t.index.month

    f = plt.figure(figsize=(9, 6))
    gs = gridspec.GridSpec(1, 5, figure=f, wspace=0)
    ax0 = f.add_subplot(gs[0, 0])
    ax1 = f.add_subplot(gs[0, 1:])

    # total system cost
    cmap_dict = cplt.tech_color_palette()
    fields_to_plot = ['Battery', 'Solar', 'Onshore Wind']

    cost = (
        cget
        .get_total_ci_procurement_cost(n, n_reference)
        .pivot_table(
            columns='carrier', 
            values='annual_system_cost [M$]'
        )
        .drop([i for i in cget.get_total_ci_procurement_cost(n, n_reference).carrier.unique() if i not in fields_to_plot], axis=1)
        .div(1e3)
    )

    cost.plot(
        kind='bar', 
        stacked=True,
        ax=ax0,
        color=[cmap_dict[carrier] for carrier in cost.columns],
    )
    

    ax0.set_xticklabels([''])
    ax0.tick_params(axis='both', which='both', length=0, pad=8)
    # ax0.set_title('Cost', loc='left', fontsize=9, fontweight='bold', fontproperties=work_sans_font_medium)
    ax0.set_ylabel('Cost of Procurement ($ billion)', fontproperties=work_sans_font)
    ax0.legend(loc='upper left', frameon=False, fontsize='small')
    ax0.set_ylim([0, round(ymax * 1.2, 1)])
    sns.despine(ax=ax0, bottom=False, right=True, top=True)

    # heatmap
    cfe_t.pivot_table(
        index='Day',
        columns='Hour',
        values='CFE Score',
        aggfunc='mean'
    ).pipe(
        sns.heatmap,
        cmap=sns.color_palette("blend:#000000,#c4ffdc", as_cmap=True),
        ax=ax1,
        cbar_kws={
            'orientation':'vertical', 
            'shrink':0.5,
            'pad':0.03,
            'ticks': [0, 1],
            'format': '%.0f'
        },
        square=True,
        xticklabels=11,
        yticklabels=15,
        linecolor='white',
        linewidths=0.1,
        vmin=0,
        vmax=1,
    )
    colorbar = ax1.collections[0].colorbar
    colorbar.set_ticks([0, 1])
    colorbar.set_ticklabels(['100%\nDirty', '100%\nClean'], fontproperties = work_sans_font)

    ax1.set_xlabel('\nTime of Day (Hour)', fontproperties=work_sans_font)
    ax1.set_ylabel('')
    ax1.set_xticklabels(['Morning', 'Noon', 'Evening'], fontproperties=work_sans_font)
    ax1.set_yticklabels(['Day 01', 'Day 15', 'Day 30'], rotation=0, fontsize=9, fontproperties=work_sans_font)
    ax1.tick_params(axis='both', which='both', length=0, pad=8)
    return f, ax0, ax1


def bar_plot_2row(
        width_ratios=[1,8],
        figsize=(10, 5),
):
    '''Create a 3-row bar plot with 3 subplots
    '''
    
    #set_tz_theme()

    # Create a figure
    fig = plt.figure(figsize=figsize)

    # Create a GridSpec with 1 row and 2 columns, setting the width ratios
    gs = gridspec.GridSpec(1, 2, width_ratios=width_ratios)

    # create subplots
    ax0 = fig.add_subplot(gs[0])
    ax1 = fig.add_subplot(gs[1], sharey=ax0)

    return fig, ax0, ax1


def bar_plot_3row(
        width_ratios=[1, 1, 8],
        figsize=(10, 5),
):
    '''Create a 3-row bar plot with 3 subplots
    '''
    
    #set_tz_theme()

    # Create a figure
    fig = plt.figure(figsize=figsize)

    # Create a GridSpec with 1 row and 2 columns, setting the width ratios
    gs = gridspec.GridSpec(1, 3, width_ratios=width_ratios)

    # create subplots
    ax0 = fig.add_subplot(gs[0])
    ax1 = fig.add_subplot(gs[1], sharey=ax0)
    ax2 = fig.add_subplot(gs[2], sharey=ax0)

    return fig, ax0, ax1, ax2


def set_tz_theme():
    '''Set the plotting theme for to match TransitionZero colour palette
    '''

    plt.rcParams.update({
        'figure.facecolor': 'white',    # Background color of the entire figure (outer area)
        'axes.facecolor': 'white',      # Background color of the plot (inside axes)
        'axes.edgecolor': 'black',      # Color of the axes/box edges
        'axes.labelcolor': 'black',     # Color of the axis labels
        'xtick.color': 'black',         # Color of the x-tick labels
        'ytick.color': 'black',         # Color of the y-tick labels
        'axes.spines.top': False,       # Remove the top spine (optional)
        'axes.spines.right': False,     # Remove the right spine (optional)
        # 'font.family': 'Work Sans',     # Font family set to Work Sans (TZ brand font)
        'axes.prop_cycle': plt.cycler(color=['#00C0B0', '#FE8348', '#008DCE', '#FFB405']),  # Custom color cycle
        'grid.color': 'black',          # Gridline color (if enabled)
        'grid.linestyle': ':',          # Gridline style (if enabled)
        'grid.linewidth': 0.5,          # Gridline width (if enabled)
        'grid.alpha': 0.5,              # Gridline transparency (if enabled)
        'text.color': 'black',          # Default text color
    })

    sns.set_context(rc = {'patch.linewidth': 0.0})


def tech_color_palette():
    return {
        "Generation": "#2e374e",
        "FossilThermal": "#202020",
        "Coal": "#322f34",
        "Subcritical": "#3a3538",
        "Supercritical": "#4f4444",
        "Ultrasupercritical": "#5d4e4c",
        "IGCC": "#6b5853",
        "Gas": "#bababa",
        "CCGT": "#999999",
        "OCGT": "#777777",
        "Oil": "#5d407c",
        "Nuclear": "#ee9dda",
        "Renewables": "#00c0b0",
        "Firmrenewables": "#b7492d",
        "Biomass": "#e25329",
        "Geothermal": "#f75726",
        "Tidal": "#25367b",
        "Marine": "#2e4ad9",
        "Hydro": "#8292e8",
        "Variablerenewables": "#ffb405",
        "Solar": "#ffce5d",
        "Utility": "#ffe19b",
        "Rooftop": "#fff0cd",
        "Wind": "#06a299",
        "Offshore Wind": "#66dad0",
        "Onshore Wind": "#99e6df",
        "Innovativethermal": "#fe8348",
        "CoalCCS": "#b18873",
        "GasCCS": "#d9d9d9",
        "BECCS": "#fa9474",
        "Ammonia": "#d9a88b",
        "Hydrogen": "#f3f3f3",
        "Storage": "#69b2f5",
        "Pumped Hydro": "#a5d1f9",
        "Battery": "#c3e0fb",
        "Batteries": "#c3e0fb",
        "Interconnectors": "#ba63da",
        "DSR": "#feba9a",
        'Agricultural Waste Solids': '#b7492d',
        'Bioenergy': '#e25329',
        'Bituminous Coal': '#322f34',
        'Coal Unspecified': '#322f34',
        'Diesel': '#5d407c',
        'Gas Unspecified': '#bababa',
        'Lignite': '#322f34',
        'Liquified Natural Gas': '#bababa',
        'Natural Gas': '#bababa',
        'Naphtha': '#bababa',
        'Sub-bituminous Coal': '#322f34',
        'Waste': '#b7492d',
        'Waste Unspecified': '#b7492d',
        'Water': '#8292e8',
        'Transmission': '#ba63da',
        'AC': '#ba63da',
    }