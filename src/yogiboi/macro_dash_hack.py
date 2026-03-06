#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jun 21 14:22:52 2025

@author: yogehs
"""
from matplotlib.colors import LogNorm, Normalize

import panel as pn
import pandas as pdx
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
# file_input = pn.widgets.FileInput(accept='.csv')
import json
import io
import pandas as pd

import sys

pn.extension()
cmap_dict = {'hertz_E': 'inferno',
             'hertz_z_c': 'afmhot',
             'ting_E0': 'inferno',
             'ting_betaE': 'viridis'}


def find_piezo_coord(nx, ny, file_ext=''):

    piezoimg_corrd = np.arange(nx*ny).reshape((ny, nx))

    if file_ext == 'jpk-force-map':

        piezoimg_corrd = np.asarray([row[::(-1)**i]
                                    for i, row in enumerate(piezoimg_corrd)])

    map_corrd_2D = np.rot90(np.fliplr(piezoimg_corrd))

    map_corrd_lin = map_corrd_2D.flatten()
    return map_corrd_2D, map_corrd_lin


def make_map(df_fileid, col_interest='hertz_E'):
    name = df_fileid.iloc[0]['file_id']
    first_row = df_fileid.iloc[0]
    extension = first_row['file_id'].split('.')[-1]
    nx, ny = json.loads(first_row['map_size_x_y_pixels'])
    scan_size_x, scan_size_y = json.loads(first_row['scan_size_x_y_m'])

    map_lin = np.nan*np.ones(nx*ny)

    map_corrd_2D, map_corrd_lin = find_piezo_coord(nx, ny, extension)
    N_curve = len(map_corrd_lin)
    for i in range(N_curve):
        temp_cid = map_corrd_lin[i]
        df_found = df_fileid[df_fileid['curve_idx'].isin([temp_cid])]
        if len(df_found) == 1:
            map_lin[i] = df_found[col_interest].iloc[0]

    # plotting the map
    # E_2d =  array_flip_coor( np.reshape(E_lin, (nx, ny)) ,nx)
    map_2D = np.reshape(map_lin, (nx, ny))
    return map_2D


# %%loading the file
# Load dataset
try:
    df = pd.read_csv('/Users/evillz/Data/CTC44/2025_12_03/psnex_map___2025.03.12_18.38.42.45/results/ys/mech_result/df_results_ting_results.csv')
    results_dict = pyafmsession.prepared_results
    for key, value in results_dict.items():
        if value is not None:

            if key == 'ting_results':
                df = value
    # else:sys.exit(0)
except NameError:
    # File uploader widget (web-compatible)
    file_input = pn.widgets.FileInput(accept='.csv')

    @pn.depends(file_input)
    def load_dataframe(file):
        if file is None:
            return pd.DataFrame()  # Empty default
        return pd.read_csv(io.BytesIO(file))
    # app = QApplication([])

    # file_path, _ = QFileDialog.getOpenFileName(None,"Open CSV File", "", "CSV Files (*.csv);;All Files (*)")
    # # file_path = '/Users/yogehs/Documents/ATIP_PhD/meccelaration/data/Dataset/df_hack__ting_results.csv'
    # if file_path:
    #     print("Selected file:", file_path)
    #     df= pd.read_csv(file_path)

    # else:
    #     print("No file selected.")
    #     app.exit()
    #     sys.exit(0)

    # app.exit()

    # Clean exit if running outside a full app


columns = list(df.select_dtypes(include=['number']).columns)
columns = ['curve_idx', 'hertz_delta0',
           'hertz_E', 'hertz_f0', 'hertz_MSE', 'hertz_RMSE',
           'hertz_Rsquared', 'hertz_chisq', 'hertz_redchi',
           'ting_E0',
           'ting_tc', 'ting_betaE', 'ting_f0', 'ting_MAE', 'ting_MSE', 'ting_RMSE',
           'ting_Rsquared', 'ting_chisq', 'ting_redchi']
groupby_column = "file_id"  # Column to group by

# Widgets
group_selector = pn.widgets.Select(name="Filter by fileid", options=[
                                   "All"] + df[groupby_column].unique().tolist(), value=df[groupby_column].unique().tolist()[0])
x_selector = pn.widgets.Select(
    name="X-axis", options=columns, value='ting_betaE')
y_selector = pn.widgets.Select(name="Y-axis", options=columns, value='ting_E0')

# Log scale checkboxes for scatter plot
log_x_scatter = pn.widgets.Checkbox(name="Log10 X-axis (Scatter)", value=False)
log_y_scatter = pn.widgets.Checkbox(name="Log10 Y-axis (Scatter)", value=True)
scatter_controls = pn.Row(log_x_scatter, log_y_scatter)
scatter_controls.visible = False

# Log scale checkbox for histogram (X-axis)
log_histogram = pn.widgets.Checkbox(name="Log10 X-axis ", value=False)

# Histogram limits inputs
xmin_input = pn.widgets.FloatInput(
    name=" X-min", step=0.1, value=None, placeholder="Auto")
xmax_input = pn.widgets.FloatInput(
    name=" X-max", step=0.1, value=None, placeholder="Auto")
histogram_controls = pn.Row(log_histogram, xmin_input, xmax_input)
map_controls = pn.Row(log_histogram, xmin_input, xmax_input)
map_controls.visible = True
histogram_controls.visible = False

# Helper function: get filtered dataframe


@pn.depends(group_selector)
def get_filtered_df(group):
    if group == "All":
        return df
    else:
        return df[df[groupby_column] == group]

# Scatter plot with color and log scale


@pn.depends(x_selector, y_selector, group_selector, log_x_scatter, log_y_scatter)
def scatter_plot(x, y, group, logx, logy):
    data = get_filtered_df(group)
    fig, ax = plt.subplots()

    # Apply log10 transform safely (avoid zeros or negatives)
    def safe_log_transform(series):
        return np.log10(series[series > 0])

    plot_data = data.copy()
    if logx:
        plot_data = plot_data[plot_data[x] > 0]
        plot_data[x] = np.log10(plot_data[x])
        xlabel = f"log10({x})"
    else:
        xlabel = x

    if logy:
        plot_data = plot_data[plot_data[y] > 0]
        plot_data[y] = np.log10(plot_data[y])
        ylabel = f"log10({y})"
    else:
        ylabel = y

    sns.scatterplot(data=plot_data, x=x, y=y,
                    hue=groupby_column, palette="deep", ax=ax)
    ax.set_title(f"{xlabel} vs {ylabel} | Group: {group}")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.legend(title=groupby_column)
    return pn.pane.Matplotlib(fig, tight=True)

# Summary statistics


@pn.depends(x_selector, y_selector, group_selector)
def summary_stats(x, y, group):
    data = get_filtered_df(group)
    stats = data[[x, y]].describe().T
    return pn.pane.DataFrame(stats, width=800)


@pn.depends(x_selector, group_selector, log_histogram, xmin_input, xmax_input)
def histogram_with_stats(x, group, log10, xmin, xmax):
    data = get_filtered_df(group)[x].dropna()

    # Apply log10 transformation if needed
    if log10:
        data = data[data > 0]
        data = np.log10(data)
        xlabel = f"log10({x})"
    else:
        xlabel = x

    # Apply limits if provided
    if xmin is not None:
        data = data[data >= xmin]
    if xmax is not None:
        data = data[data <= xmax]

    fig, ax = plt.subplots()
    sns.histplot(data, bins=20, kde=True, ax=ax)
    ax.set_title(f"Histogram of {xlabel} | Group: {group}")
    ax.set_xlabel(xlabel)

    # Summary stats
    stats = data.describe().to_frame().T
    stats_pane = pn.pane.DataFrame(stats, width=800)

    return pn.Column(pn.pane.Matplotlib(fig, tight=True), stats_pane)

# Histogram (based only on X-axis for simplicity)


@pn.depends(x_selector, group_selector, log_histogram, xmin_input, xmax_input)
def histogram(x, group, log10, xmin, xmax):
    data = get_filtered_df(group)[x].dropna()

    # Apply log10 transformation if needed
    if log10:
        data = data[data > 0]
        data = np.log10(data)
        xlabel = f"log10({x})"
    else:
        xlabel = x

    # Apply limits if provided
    if xmin is not None:
        data = data[data >= xmin]
    if xmax is not None:
        data = data[data <= xmax]

    fig, ax = plt.subplots()
    sns.histplot(data, bins=20, kde=True, ax=ax)
    ax.set_title(f"Histogram of {xlabel} | Group: {group}")
    ax.set_xlabel(xlabel)
    return pn.pane.Matplotlib(fig, tight=True)


@pn.depends(x_selector, group_selector, log_histogram, xmin_input, xmax_input)
def heatmap_plot(x_selector, group, log10, xmin, xmax):
    data = get_filtered_df(group)

    map_2D = make_map(data, x_selector)
    # Apply log10 transformation if needed
    if log10:
        # map_2D = map_2D[map_2D > 0]
        map_2D = np.log10(map_2D)
        xlabel = f"log10({x_selector})"
    else:
        xlabel = x_selector

    # Apply limits if provided
    if xmin is not None:
        c_min = xmin
    else:
        c_min = np.nanmin(map_2D)
    if xmax is not None:
        c_max = xmax
    else:
        c_max = np.nanmax(map_2D)
    norm = Normalize(c_min, c_max)

    fig, ax = plt.subplots(figsize=(5, 5))

    cbar_ax = fig.add_axes([.91, .3, .03, .4])
    try:

        cmap_i = cmap_dict[x_selector]
    except KeyError:
        cmap_i = 'rocket'
    sns.heatmap(map_2D, square=True, cbar=True, cbar_ax=cbar_ax,
                ax=ax, cmap=cmap_i, norm=norm)  # ,cbar_ax= cbar_ax)
    ax.set(xticklabels=[])
    ax.set(yticklabels=[])
    ax.invert_yaxis()
    ax.tick_params(bottom=False, left=False)
    # sns.heatmap(map_2D, cmap="plasma", ax=ax)
    ax.set_title(f"{x_selector} map of {group} ")

    return pn.pane.Matplotlib(fig, tight=True)
# @pn.depends(x_selector, group_selector, log_histogram, xmin_input, xmax_input)
# def heatmap_plot(x_selector, group, log10, xmin, xmax):
#     data = get_filtered_df(group)

#     map_2D = make_map(data, x_selector)
    
#     # Check if map has valid data
#     if map_2D.size == 0 or np.all(np.isnan(map_2D)):
#         fig, ax = plt.subplots(figsize=(5, 5))
#         ax.text(0.5, 0.5, 'No valid data to display', 
#                 ha='center', va='center', transform=ax.transAxes)
#         ax.set_title(f"{x_selector} map of {group}")
#         return pn.pane.Matplotlib(fig, tight=True)
    
#     # Apply log10 transformation if needed
#     if log10:
#         # map_2D = map_2D[map_2D > 0]
#         map_2D = np.log10(map_2D)
#         xlabel = f"log10({x_selector})"
#     else:
#         xlabel = x_selector

#     # Apply limits if provided
#     if xmin is not None:
#         c_min = xmin
#     else:
#         c_min = np.nanmin(map_2D)
#     if xmax is not None:
#         c_max = xmax
#     else:
#         c_max = np.nanmax(map_2D)
#     norm = Normalize(c_min, c_max)

#     fig, ax = plt.subplots(figsize=(5, 5))

#     cbar_ax = fig.add_axes([.91, .3, .03, .4])
#     try:

#         cmap_i = cmap_dict[x_selector]
#     except KeyError:
#         cmap_i = 'rocket'
#     sns.heatmap(map_2D, square=True, cbar=True, cbar_ax=cbar_ax,
#                 ax=ax, cmap=cmap_i, norm=norm)  # ,cbar_ax= cbar_ax)
#     ax.set(xticklabels=[])
#     ax.set(yticklabels=[])
#     ax.invert_yaxis()
#     ax.tick_params(bottom=False, left=False)
#     # sns.heatmap(map_2D, cmap="plasma", ax=ax)
#     ax.set_title(f"{x_selector} map of {group} ")

#     return pn.pane.Matplotlib(fig, tight=True)

# Tabs
tabs = pn.Tabs((" Map (Heatmap)", heatmap_plot),
               (" Scatter Plot", scatter_plot),
               (" Histogram", histogram_with_stats),
               (" Statistics", summary_stats),

               )


def toggle_controls(event):
    map_controls.visible = (event.new == 0)

    scatter_controls.visible = (event.new == 1)
    histogram_controls.visible = (event.new == 2)


tabs.param.watch(toggle_controls, "active")


dashboard = pn.Column(
    "# Are you on fire or your data is 🔥 ??",

    pn.Row(group_selector, x_selector, y_selector),
    map_controls,
    scatter_controls,
    histogram_controls,

    tabs,
)

# pn.serve(dashboard, show=True)
dashboard.show(title="🔥 AFM Results Explorer")

# %%
