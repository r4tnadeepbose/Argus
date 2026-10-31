from recon.ui import theme


def test_two_palettes_available():
    assert set(theme.PALETTES) == {"dark", "light"}
    assert theme.PALETTES["dark"].name == "Slate"
    assert theme.PALETTES["light"].name == "Paper"


def test_palette_colors_are_hex():
    for palette in theme.PALETTES.values():
        for field, value in vars(palette).items():
            if field == "name":
                continue
            assert value.startswith("#") and len(value) == 7, (field, value)


def test_palette_surfaces_are_distinct():
    for palette in theme.PALETTES.values():
        assert palette.text != palette.bg
        assert palette.surface != palette.bg
        assert palette.accent != palette.bg
