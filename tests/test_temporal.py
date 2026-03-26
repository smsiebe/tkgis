"""Tests for the temporal data management layer."""
from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pytest

from tkgis.models.events import EventBus, EventType
from tkgis.models.layers import Layer, LayerType
from tkgis.temporal.manager import TemporalLayerManager
from tkgis.temporal.raster_stack import TemporalRasterStack


# ======================================================================
# Helpers
# ======================================================================

def _make_temporal_layer(
    name: str,
    time_start: str,
    time_end: str | None = None,
    time_steps: list[str] | None = None,
) -> Layer:
    return Layer(
        name=name,
        layer_type=LayerType.TEMPORAL_RASTER,
        time_start=time_start,
        time_end=time_end or time_start,
        time_steps=time_steps,
    )


# ======================================================================
# TemporalLayerManager
# ======================================================================


class TestTemporalManagerTimeSteps:
    """test_temporal_manager_time_steps"""

    def test_returns_sorted_steps(self):
        bus = EventBus()
        mgr = TemporalLayerManager(bus)
        steps = ["2024-06-03T00:00:00", "2024-06-01T00:00:00", "2024-06-02T00:00:00"]
        layer = _make_temporal_layer("ts", "2024-06-01", time_steps=steps)
        result = mgr.get_time_steps(layer)
        assert result == [
            datetime(2024, 6, 1),
            datetime(2024, 6, 2),
            datetime(2024, 6, 3),
        ]

    def test_empty_when_no_steps(self):
        bus = EventBus()
        mgr = TemporalLayerManager(bus)
        layer = _make_temporal_layer("empty", "2024-01-01")
        assert mgr.get_time_steps(layer) == []

    def test_time_range_from_steps(self):
        bus = EventBus()
        mgr = TemporalLayerManager(bus)
        steps = ["2024-01-10T00:00:00", "2024-01-01T00:00:00", "2024-01-20T00:00:00"]
        layer = Layer(
            name="no-range",
            layer_type=LayerType.TEMPORAL_RASTER,
            time_steps=steps,
        )
        rng = mgr.get_time_range(layer)
        assert rng is not None
        assert rng == (datetime(2024, 1, 1), datetime(2024, 1, 20))

    def test_time_range_from_fields(self):
        bus = EventBus()
        mgr = TemporalLayerManager(bus)
        layer = _make_temporal_layer("r", "2024-03-01", "2024-03-31")
        rng = mgr.get_time_range(layer)
        assert rng == (datetime(2024, 3, 1), datetime(2024, 3, 31))

    def test_time_range_none_for_non_temporal(self):
        bus = EventBus()
        mgr = TemporalLayerManager(bus)
        layer = Layer(name="plain", layer_type=LayerType.RASTER)
        assert mgr.get_time_range(layer) is None


class TestTemporalManagerNearestStep:
    """test_temporal_manager_nearest_step"""

    def _layer_with_steps(self) -> Layer:
        steps = [
            "2024-01-01T00:00:00",
            "2024-01-05T00:00:00",
            "2024-01-10T00:00:00",
            "2024-01-15T00:00:00",
        ]
        return _make_temporal_layer("ns", "2024-01-01", time_steps=steps)

    def test_exact_match(self):
        bus = EventBus()
        mgr = TemporalLayerManager(bus)
        layer = self._layer_with_steps()
        assert mgr.get_nearest_step(layer, datetime(2024, 1, 5)) == datetime(2024, 1, 5)

    def test_snaps_to_closest(self):
        bus = EventBus()
        mgr = TemporalLayerManager(bus)
        layer = self._layer_with_steps()
        # 2024-01-07 is closer to 2024-01-05 (2 days) than 2024-01-10 (3 days)
        assert mgr.get_nearest_step(layer, datetime(2024, 1, 7)) == datetime(2024, 1, 5)

    def test_before_first(self):
        bus = EventBus()
        mgr = TemporalLayerManager(bus)
        layer = self._layer_with_steps()
        assert mgr.get_nearest_step(layer, datetime(2023, 12, 1)) == datetime(2024, 1, 1)

    def test_after_last(self):
        bus = EventBus()
        mgr = TemporalLayerManager(bus)
        layer = self._layer_with_steps()
        assert mgr.get_nearest_step(layer, datetime(2025, 1, 1)) == datetime(2024, 1, 15)

    def test_raises_on_empty(self):
        bus = EventBus()
        mgr = TemporalLayerManager(bus)
        layer = _make_temporal_layer("empty", "2024-01-01")
        with pytest.raises(ValueError, match="no time steps"):
            mgr.get_nearest_step(layer, datetime(2024, 1, 1))


class TestTemporalManagerSetCurrentTimeEmitsEvent:
    """test_temporal_manager_set_current_time_emits_event"""

    def test_emits_time_step_changed(self):
        bus = EventBus()
        mgr = TemporalLayerManager(bus)
        received: list[datetime] = []
        bus.subscribe(EventType.TIME_STEP_CHANGED, lambda time: received.append(time))

        t = datetime(2024, 6, 15, 12, 0, 0)
        mgr.set_current_time(t)

        assert len(received) == 1
        assert received[0] == t

    def test_updates_current_time_property(self):
        bus = EventBus()
        mgr = TemporalLayerManager(bus)
        t = datetime(2024, 6, 15)
        mgr.set_current_time(t)
        assert mgr.current_time == t

    def test_get_active_data_index(self):
        bus = EventBus()
        mgr = TemporalLayerManager(bus)
        steps = ["2024-01-01T00:00:00", "2024-01-02T00:00:00", "2024-01-03T00:00:00"]
        layer = _make_temporal_layer("idx", "2024-01-01", time_steps=steps)
        mgr.set_current_time(datetime(2024, 1, 2, 6))
        # Closest to 2024-01-02
        assert mgr.get_active_data_index(layer) == 1

    def test_active_data_index_none_without_time(self):
        bus = EventBus()
        mgr = TemporalLayerManager(bus)
        layer = _make_temporal_layer("idx", "2024-01-01", time_steps=["2024-01-01T00:00:00"])
        assert mgr.get_active_data_index(layer) is None


# ======================================================================
# TemporalRasterStack
# ======================================================================


class TestTemporalRasterStackSorting:
    """test_temporal_raster_stack_sorting"""

    def test_sorts_by_time(self):
        layers = [
            _make_temporal_layer("c", "2024-03-01"),
            _make_temporal_layer("a", "2024-01-01"),
            _make_temporal_layer("b", "2024-02-01"),
        ]
        stack = TemporalRasterStack(layers)
        assert [l.name for l in stack.layers] == ["a", "b", "c"]

    def test_times_property(self):
        layers = [
            _make_temporal_layer("x", "2024-06-15"),
            _make_temporal_layer("y", "2024-03-10"),
        ]
        stack = TemporalRasterStack(layers)
        assert stack.times == [datetime(2024, 3, 10), datetime(2024, 6, 15)]

    def test_len(self):
        layers = [_make_temporal_layer(f"l{i}", f"2024-01-{i+1:02d}") for i in range(5)]
        stack = TemporalRasterStack(layers)
        assert len(stack) == 5

    def test_rejects_non_temporal(self):
        layers = [Layer(name="bad", layer_type=LayerType.RASTER)]
        with pytest.raises(ValueError, match="no time_start"):
            TemporalRasterStack(layers)


class TestTemporalRasterStackFrameAtTime:
    """test_temporal_raster_stack_frame_at_time"""

    def _stack(self) -> TemporalRasterStack:
        layers = [
            _make_temporal_layer("jan", "2024-01-15"),
            _make_temporal_layer("feb", "2024-02-15"),
            _make_temporal_layer("mar", "2024-03-15"),
        ]
        return TemporalRasterStack(layers)

    def test_exact_match(self):
        stack = self._stack()
        frame = stack.get_frame_at_time(datetime(2024, 2, 15))
        assert frame.name == "feb"

    def test_snaps_to_nearest(self):
        stack = self._stack()
        # 2024-02-20 is closer to feb-15 (5d) than mar-15 (23d)
        frame = stack.get_frame_at_time(datetime(2024, 2, 20))
        assert frame.name == "feb"

    def test_before_range(self):
        stack = self._stack()
        frame = stack.get_frame_at_time(datetime(2023, 1, 1))
        assert frame.name == "jan"

    def test_after_range(self):
        stack = self._stack()
        frame = stack.get_frame_at_time(datetime(2025, 12, 31))
        assert frame.name == "mar"

    def test_pixel_time_series_returns_nan_without_rasterio(self):
        """Without rasterio, get_time_series_at_pixel returns NaN array."""
        stack = self._stack()
        result = stack.get_time_series_at_pixel(0, 0)
        assert isinstance(result, np.ndarray)
        assert len(result) == 3
        assert np.all(np.isnan(result))


# ======================================================================
# TimeSliderPanel creation
# ======================================================================


class TestTimeSliderPanelCreates:
    """test_time_slider_panel_creates"""

    def test_attributes(self):
        """Panel class attributes are correct without needing Tk."""
        from tkgis.panels.time_slider import TimeSliderPanel

        assert TimeSliderPanel.name == "time_slider"
        assert TimeSliderPanel.title == "Time"
        assert TimeSliderPanel.dock_position == "bottom"
        assert TimeSliderPanel.default_visible is False

    def test_instantiation(self):
        bus = EventBus()
        mgr = TemporalLayerManager(bus)
        from tkgis.panels.time_slider import TimeSliderPanel

        panel = TimeSliderPanel(event_bus=bus, manager=mgr)
        assert panel.visible is False
        assert panel.widget is None

    def test_create_widget(self, tk_root):
        """Full widget creation requires a Tk root."""
        bus = EventBus()
        mgr = TemporalLayerManager(bus)
        from tkgis.panels.time_slider import TimeSliderPanel

        panel = TimeSliderPanel(event_bus=bus, manager=mgr)
        widget = panel.create_widget(tk_root)
        assert widget is not None
        assert panel.widget is widget

    def test_configure_updates_steps(self, tk_root):
        bus = EventBus()
        mgr = TemporalLayerManager(bus)
        from tkgis.panels.time_slider import TimeSliderPanel

        panel = TimeSliderPanel(event_bus=bus, manager=mgr)
        panel.create_widget(tk_root)

        steps = [datetime(2024, 1, 1) + timedelta(days=i) for i in range(100)]
        panel.configure(steps)
        assert len(panel._steps) == 100
