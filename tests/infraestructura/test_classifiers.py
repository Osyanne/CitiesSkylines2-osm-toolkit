"""classify_infra: tags OSM reales -> (categoria, subtipo) | None."""
from infraestructura.classifiers import classify_infra


def test_power_plant_is_generacion():
    assert classify_infra({"power": "plant", "name": "Riverside"}) == ("power", "generacion")

def test_power_generator_is_generacion():
    assert classify_infra({"power": "generator", "generator:source": "solar"}) == ("power", "generacion")

def test_substation_is_subestacion():
    assert classify_infra({"power": "substation", "name": "Main St"}) == ("power", "subestacion")

def test_power_line_is_transmision():
    assert classify_infra({"power": "line"}) == ("power", "transmision")

def test_minor_line_is_transmision():
    assert classify_infra({"power": "minor_line"}) == ("power", "transmision")

def test_water_tower_is_suministro():
    assert classify_infra({"man_made": "water_tower"}) == ("water", "suministro")

def test_water_works_is_suministro():
    assert classify_infra({"man_made": "water_works", "name": "Fridley"}) == ("water", "suministro")

def test_wastewater_plant_is_aguas_residuales():
    assert classify_infra({"man_made": "wastewater_plant"}) == ("water", "aguas_residuales")

def test_landfill_is_disposicion():
    assert classify_infra({"landuse": "landfill"}) == ("waste", "disposicion")

def test_incinerator_is_disposicion():
    assert classify_infra({"man_made": "incinerator", "name": "HERC"}) == ("waste", "disposicion")

def test_communications_tower_is_telecom_torre():
    assert classify_infra({"man_made": "communications_tower"}) == ("telecom", "torre")

def test_data_center_is_telecom():
    assert classify_infra({"telecom": "data_center"}) == ("telecom", "data_center")

def test_unknown_returns_none():
    assert classify_infra({"amenity": "cafe"}) is None

def test_empty_returns_none():
    assert classify_infra({}) is None
