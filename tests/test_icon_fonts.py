from icon_fonts import (
    DEFAULT_FONT_WEIGHT,
    FONT_WEIGHT_NAMES,
    resolve_weight_choice,
    weight_name_for_position,
    weight_position_for_name,
)


def test_weight_position_round_trip() -> None:
    for index, name in enumerate(FONT_WEIGHT_NAMES, start=1):
        assert weight_position_for_name(name) == index
        assert weight_name_for_position(index) == name


def test_weight_position_clamps_to_bounds() -> None:
    assert weight_name_for_position(0) == FONT_WEIGHT_NAMES[0]
    assert weight_name_for_position(999) == FONT_WEIGHT_NAMES[-1]


def test_weight_position_defaults_for_unknown_name() -> None:
    default_index = weight_position_for_name(DEFAULT_FONT_WEIGHT)
    assert weight_position_for_name("Unknown") == default_index


def test_resolve_weight_choice_prefers_bolder_on_tie() -> None:
    choice = resolve_weight_choice("Light", ("Thin", "Regular"))
    assert choice == "Regular"


def test_resolve_weight_choice_handles_invalid_options() -> None:
    choice = resolve_weight_choice("Medium", ("Invalid",))
    assert choice == "Medium"
