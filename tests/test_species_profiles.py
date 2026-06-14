"""Tests del loader de species_profiles.yaml."""

from __future__ import annotations

import pytest

from dondeplanto.config import SPECIES_PROFILES_PATH
from dondeplanto.scoring.species_profiles import load_profiles


def test_load_profiles_returns_three_species() -> None:
    profiles = load_profiles()
    assert "Eucalyptus dunnii" in profiles
    assert "Eucalyptus grandis" in profiles
    assert "Pinus taeda" in profiles


def test_each_profile_has_required_fields() -> None:
    profiles = load_profiles()
    required = {
        "temp_min_c",
        "temp_opt_low_c",
        "temp_opt_high_c",
        "temp_max_c",
        "precip_min_mm",
        "precip_opt_low_mm",
        "precip_opt_high_mm",
        "precip_max_mm",
        "drought_tolerance",
        "fire_sensitivity",
    }
    for name, profile in profiles.items():
        missing = required - set(profile.keys())
        assert not missing, f"perfil {name!r} sin campos {missing}"


def test_profile_field_types() -> None:
    profiles = load_profiles()
    for name, profile in profiles.items():
        for k, v in profile.items():
            assert isinstance(v, (int, float)), f"{name}.{k} no es número: {v!r}"


def test_dunnii_specific_values() -> None:
    """Sanity check de los valores del spec sección 3."""
    p = load_profiles()["Eucalyptus dunnii"]
    assert p["temp_min_c"] == 12
    assert p["temp_opt_low_c"] == 18
    assert p["temp_opt_high_c"] == 24
    assert p["temp_max_c"] == 28
    assert p["precip_min_mm"] == 800
    assert p["precip_opt_low_mm"] == 1000
    assert p["precip_opt_high_mm"] == 1400
    assert p["precip_max_mm"] == 1800
    assert p["drought_tolerance"] == 0.7
    assert p["fire_sensitivity"] == 0.5


def test_load_profiles_is_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    """load_profiles usa lru_cache: segunda llamada no relee el archivo."""
    p1 = load_profiles()
    p2 = load_profiles()
    assert p1 is p2  # mismo dict (lru_cache hit)


def test_load_profiles_missing_file_returns_empty(
    tmp_path: pytest.TempPathFactory,
) -> None:
    """Si el YAML no existe, devuelve {} y no crashea."""
    fake = tmp_path / "no_existe.yaml"  # type: ignore[attr-defined]
    assert load_profiles(fake) == {}


def test_load_profiles_malformed_returns_empty(
    tmp_path: pytest.TempPathFactory,
) -> None:
    """YAML con raíz no-mapping devuelve {} sin crashear."""
    fake = tmp_path / "bad.yaml"  # type: ignore[attr-defined]
    fake.write_text("- 1\n- 2\n", encoding="utf-8")  # raíz es list
    assert load_profiles(fake) == {}


def test_default_path_uses_config_constant() -> None:
    """Si no se pasa path, usa SPECIES_PROFILES_PATH de config."""
    # Llamada sin argumento debe usar el path por defecto de config
    profiles = load_profiles()
    assert SPECIES_PROFILES_PATH.exists()
    assert "Eucalyptus dunnii" in profiles
