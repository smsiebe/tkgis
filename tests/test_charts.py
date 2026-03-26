"""Tests for the tkgis charting system."""
from __future__ import annotations

from datetime import datetime

import numpy as np
import pytest
from matplotlib.figure import Figure

from tkgis.charts.spectral import SpectralProfileChart, SpectralProfileData
from tkgis.charts.histogram import HistogramChart, HistogramData
from tkgis.charts.scatter import ScatterPlotChart, ScatterData
from tkgis.charts.time_series import TimeSeriesChart, TimeSeriesData


# ------------------------------------------------------------------
# Spectral profile
# ------------------------------------------------------------------

def test_spectral_profile_creates_figure():
    chart = SpectralProfileChart()
    fig = chart.create_figure()
    assert isinstance(fig, Figure)
    assert len(fig.axes) == 1
    assert fig.axes[0].get_ylabel() == "Value"


def test_spectral_profile_updates():
    chart = SpectralProfileChart()
    fig = chart.create_figure()

    data = SpectralProfileData(
        band_names=["B1", "B2", "B3", "B4"],
        values=[0.1, 0.4, 0.35, 0.8],
        pixel_coords=(50, 75),
    )
    chart.update(data)

    ax = fig.axes[0]
    # Should have exactly one line
    assert len(ax.lines) == 1
    ydata = ax.lines[0].get_ydata()
    np.testing.assert_array_almost_equal(ydata, data.values)


# ------------------------------------------------------------------
# Histogram
# ------------------------------------------------------------------

def test_histogram_creates_and_updates():
    chart = HistogramChart()
    fig = chart.create_figure()
    assert isinstance(fig, Figure)

    rng = np.random.default_rng(42)
    data = HistogramData(values=rng.normal(128, 30, size=500).tolist(), label="Band 1", bins=32)
    chart.update(data)

    ax = fig.axes[0]
    # Histogram produces Rectangle patches
    assert len(ax.patches) > 0


# ------------------------------------------------------------------
# Scatter
# ------------------------------------------------------------------

def test_scatter_creates_and_updates():
    chart = ScatterPlotChart()
    fig = chart.create_figure()
    assert isinstance(fig, Figure)

    rng = np.random.default_rng(7)
    data = ScatterData(
        x=rng.uniform(0, 10, 50).tolist(),
        y=rng.uniform(0, 10, 50).tolist(),
        x_label="Band 3",
        y_label="Band 4",
    )
    chart.update(data)

    ax = fig.axes[0]
    # PathCollection from scatter
    assert len(ax.collections) == 1
    assert ax.get_xlabel() == "Band 3"
    assert ax.get_ylabel() == "Band 4"


# ------------------------------------------------------------------
# Time series
# ------------------------------------------------------------------

def test_time_series_creates_and_updates():
    chart = TimeSeriesChart()
    fig = chart.create_figure()
    assert isinstance(fig, Figure)

    timestamps = [datetime(2025, 1, i + 1) for i in range(10)]
    values = list(range(10))
    data = TimeSeriesData(timestamps=timestamps, values=values, label="NDVI")
    chart.update(data)

    ax = fig.axes[0]
    assert len(ax.lines) == 1


# ------------------------------------------------------------------
# ChartPanel (requires Tk root)
# ------------------------------------------------------------------

def test_chart_panel_creates(tk_root):
    from tkgis.panels.chart_panel import ChartPanel

    panel = ChartPanel()
    assert panel.dock_position == "bottom"
    assert panel.default_visible is False

    widget = panel.create_widget(tk_root)
    assert widget is not None

    # Add a chart and verify container
    chart = SpectralProfileChart()
    container = panel.add_chart(chart)
    assert container is not None
    assert panel.get_container("spectral_profile") is container

    # Adding same chart again returns existing container
    assert panel.add_chart(chart) is container

    widget.destroy()
