from cmip_indexkg.extraction.aliases import generate_aliases
from cmip_indexkg.extraction.normalization import compact_key, normalize_text


def test_experiment_ssp_aliases():
    aliases = set(generate_aliases("Experiment", "ssp245", "ssp245", {}))
    assert "SSP2-4.5" in aliases
    assert "SSP2 4.5" in aliases
    assert "ssp245" in aliases


def test_source_hyphen_alias():
    aliases = set(generate_aliases("Source", "ACCESS-CM2", "ACCESS-CM2", {}))
    assert "ACCESS-CM2" in aliases
    assert "ACCESS CM2" in aliases


def test_variable_aliases_are_conservative():
    aliases = set(generate_aliases("Variable", "tas", "tas", {}))
    assert "tas" in aliases
    assert "near-surface air temperature" in aliases
    assert "temperature" not in aliases


def test_normalization_keys():
    assert normalize_text(" SSP2-4.5 ") == "ssp2 4 5"
    assert compact_key("ACCESS-CM2") == "accesscm2"
