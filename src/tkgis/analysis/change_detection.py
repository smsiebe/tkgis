"""Change detection between raster layers."""
from __future__ import annotations

import logging
import uuid

import numpy as np

from tkgis.models.layers import Layer, LayerType

logger = logging.getLogger(__name__)


class ChangeDetector:
    """Detect changes between two raster layers.

    Layers are expected to carry their raster data in
    ``layer.metadata["data"]`` as a 2-D NumPy array.
    """

    @staticmethod
    def _get_data(layer: Layer) -> np.ndarray:
        """Retrieve the 2-D data array from a layer's metadata."""
        data = layer.metadata.get("data")
        if data is None:
            raise ValueError(
                f"Layer '{layer.name}' has no 'data' key in metadata"
            )
        return np.asarray(data, dtype=np.float64)

    @staticmethod
    def _make_result_layer(
        data: np.ndarray, name: str, layer_type: LayerType = LayerType.RASTER
    ) -> Layer:
        """Wrap a NumPy array into a new Layer."""
        return Layer(
            id=str(uuid.uuid4()),
            name=name,
            layer_type=layer_type,
            metadata={"data": data},
        )

    def difference(self, layer_a: Layer, layer_b: Layer) -> Layer:
        """Simple image differencing: ``B - A``.

        Parameters
        ----------
        layer_a, layer_b:
            Two raster layers of the same shape.

        Returns
        -------
        Layer
            A new layer whose ``metadata["data"]`` is the difference array.
        """
        a = self._get_data(layer_a)
        b = self._get_data(layer_b)
        if a.shape != b.shape:
            raise ValueError(
                f"Shape mismatch: {a.shape} vs {b.shape}"
            )
        diff = b - a
        return self._make_result_layer(diff, "difference")

    def ratio(self, layer_a: Layer, layer_b: Layer) -> Layer:
        """Log-ratio change detection (common for SAR): ``log(B / A)``.

        Zeros in *layer_a* are replaced with a small epsilon to avoid
        division by zero.

        Parameters
        ----------
        layer_a, layer_b:
            Two raster layers of the same shape.

        Returns
        -------
        Layer
            A new layer whose ``metadata["data"]`` is the log-ratio array.
        """
        a = self._get_data(layer_a)
        b = self._get_data(layer_b)
        if a.shape != b.shape:
            raise ValueError(
                f"Shape mismatch: {a.shape} vs {b.shape}"
            )
        eps = np.finfo(np.float64).eps
        safe_a = np.where(np.abs(a) < eps, eps, a)
        log_ratio = np.log(np.abs(b) / np.abs(safe_a))
        return self._make_result_layer(log_ratio, "log_ratio")

    def threshold_change(self, diff_layer: Layer, threshold: float) -> Layer:
        """Apply an absolute-value threshold to produce a binary change mask.

        Parameters
        ----------
        diff_layer:
            A layer produced by :meth:`difference` or :meth:`ratio`.
        threshold:
            Pixels where ``|value| >= threshold`` are marked as changed (1).

        Returns
        -------
        Layer
            A new layer whose ``metadata["data"]`` is a binary uint8 array
            (0 = no change, 1 = change).
        """
        data = self._get_data(diff_layer)
        mask = (np.abs(data) >= threshold).astype(np.uint8)
        return self._make_result_layer(mask, "change_mask")
