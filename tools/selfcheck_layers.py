from src.zondeditor.domain.layers import (
    Layer,
    SoilType,
    build_default_layers,
    calc_mode_for_soil,
    insert_layer_between,
    move_layer_boundary,
    normalize_layers,
    validate_layers,
)


def main() -> int:
    base = build_default_layers(0.0, 1.0)[0]
    layers = normalize_layers([
        base,
        Layer(
            top_m=1.0,
            bot_m=2.0,
            soil_type=SoilType.SAND,
            calc_mode=calc_mode_for_soil(SoilType.SAND),
            style={"color": "#fff", "hatch": "diag"},
            ige_num=2,
        ),
    ])
    moved = move_layer_boundary(layers, 1, 0.7)
    validate_layers(moved)
    assert abs(moved[0].bot_m - 0.7) < 1e-6
    assert abs(moved[1].top_m - 0.7) < 1e-6

    ins = insert_layer_between(moved, 1)
    validate_layers(ins)
    assert len(ins) == 3
    assert calc_mode_for_soil(SoilType.FILL).value == "limited"
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
