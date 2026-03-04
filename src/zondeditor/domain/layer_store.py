from __future__ import annotations

from collections.abc import Callable, Sequence

from .layers import Layer, build_default_layers, layer_from_dict, normalize_layers, validate_layers


class LayerStore:
    """Single source of truth for per-test layers."""

    def get_layers(self, test, depth_range_fn: Callable[[object], tuple[float, float]]) -> list[Layer]:
        raw = list(getattr(test, "layers", []) or [])
        layers: list[Layer] = []
        for item in raw:
            if isinstance(item, Layer):
                layers.append(item)
            elif isinstance(item, dict):
                layers.append(layer_from_dict(item))
        if not layers:
            top, bot = depth_range_fn(test)
            layers = build_default_layers(top, bot)
        try:
            layers = normalize_layers(layers)
            validate_layers(layers)
        except Exception:
            top, bot = depth_range_fn(test)
            layers = build_default_layers(top, bot)
        test.layers = layers
        return layers

    def ensure_defaults_for_all_tests(self, tests: Sequence[object], depth_range_fn: Callable[[object], tuple[float, float]]) -> bool:
        changed = False
        for test in tests or []:
            before = bool(getattr(test, "layers", None))
            self.get_layers(test, depth_range_fn)
            if not before:
                changed = True
        return changed

