#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plotting utility functions
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from typing import Optional, Tuple
import seaborn as sns


def create_heatmap_figure(figsize: Tuple[int, int] = (10, 8)) -> Tuple[Figure, Axes]:
    """
    Create a matplotlib figure and axes for heatmap
    
    Parameters:
    -----------
    figsize : Tuple[int, int]
        Figure size (width, height)
        
    Returns:
    --------
    Tuple[Figure, Axes]: Figure and axes objects
    """
    fig = Figure(figsize=figsize, dpi=100)
    ax = fig.add_subplot(111)
    return fig, ax


def plot_seaborn_heatmap(ax: Axes, 
                         data: np.ndarray,
                         x_labels: Optional[np.ndarray] = None,
                         y_labels: Optional[np.ndarray] = None,
                         cmap: str = 'YlOrBr',
                         vmin: Optional[float] = None,
                         vmax: Optional[float] = None,
                         annot: bool = False,
                         fmt: str = '.2f',
                         cbar_label: str = 'Z (µm)') -> Axes:
    """
    Plot heatmap using seaborn
    
    Parameters:
    -----------
    ax : Axes
        Matplotlib axes
    data : np.ndarray
        2D data array
    x_labels, y_labels : np.ndarray, optional
        Axis labels
    cmap : str
        Colormap name
    vmin, vmax : float, optional
        Color scale limits
    annot : bool
        Show annotations
    fmt : str
        Annotation format
    cbar_label : str
        Colorbar label
        
    Returns:
    --------
    Axes: The axes object
    """
    # Sample labels if too many
    x_tick_labels = x_labels if x_labels is not None else False
    y_tick_labels = y_labels if y_labels is not None else False
    
    if x_labels is not None and len(x_labels) > 50:
        x_tick_labels = x_labels[::5]
        xticklabels_idx = list(range(0, len(x_labels), 5))
    else:
        xticklabels_idx = True
        
    if y_labels is not None and len(y_labels) > 50:
        y_tick_labels = y_labels[::5]
        yticklabels_idx = list(range(0, len(y_labels), 5))
    else:
        yticklabels_idx = True
    
    # Create heatmap
    heatmap = sns.heatmap(
        data,
        ax=ax,
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        annot=annot if not annot or data.size < 1000 else False,  # Don't annotate large maps
        fmt=fmt,
        xticklabels=xticklabels_idx if x_labels is not None else False,
        yticklabels=yticklabels_idx if y_labels is not None else False,
        cbar_kws={'label': cbar_label}
    )
    
    ax.invert_yaxis()
    
    return ax


def add_colorbar(ax: Axes, mappable, label: str = 'Z (µm)'):
    """
    Add colorbar to axes
    
    Parameters:
    -----------
    ax : Axes
        Matplotlib axes
    mappable : 
        Mappable object from plot
    label : str
        Colorbar label
    """
    cbar = plt.colorbar(mappable, ax=ax)
    cbar.set_label(label, rotation=90, labelpad=15)
    return cbar


def format_axes(ax: Axes, 
                x_label: str = 'X (µm)',
                y_label: str = 'Y (µm)',
                title: str = '',
                fontsize: int = 12):
    """
    Format axes labels and title
    
    Parameters:
    -----------
    ax : Axes
        Matplotlib axes
    x_label, y_label : str
        Axis labels
    title : str
        Plot title
    fontsize : int
        Font size
    """
    ax.set_xlabel(x_label, fontsize=fontsize)
    ax.set_ylabel(y_label, fontsize=fontsize)
    if title:
        ax.set_title(title, fontsize=fontsize + 2)
    ax.tick_params(labelsize=fontsize - 2)


def set_aspect_ratio(ax: Axes, x_sens: float, y_sens: float, flip_axis: bool = True):
    """
    Set aspect ratio based on sensitivity values
    
    Parameters:
    -----------
    ax : Axes
        Matplotlib axes
    x_sens : float
        X sensitivity (µm/V)
    y_sens : float
        Y sensitivity (µm/V)
    flip_axis : bool
        Whether to flip axis
    """
    xy_axis = -1 if flip_axis else 1
    ax.set_aspect((x_sens / y_sens) ** xy_axis)
