"""classify_infra: tags OSM reales -> (categoria, subtipo) | None."""
from infraestructura.classifiers import classify_infra


def test_power_plant_is_generacion():
    assert classify_infra({"power": "plant", "name": "Riverside"}) == ("power", "generacion")

def test_power_generator_excluded():
    """power=generator (paneles solares de techo/comunitarios) excluido como clutter; solo power=plant cuenta."""
    assert classify_infra({"power": "generator", "generator:source": "solar"}) is None

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


# -- Reglas condicionales + exclusiones (tags reales OSM) --

def test_recycling_centre_is_reciclaje():
    assert classify_infra({"amenity": "recycling", "recycling_type": "centre"}) == ("waste", "reciclaje")

def test_recycling_container_excluded():
    assert classify_infra({"amenity": "recycling", "recycling_type": "container"}) is None

def test_recycling_without_type_excluded():
    assert classify_infra({"amenity": "recycling"}) is None

def test_mast_communication_is_telecom():
    assert classify_infra({"man_made": "mast", "tower:type": "communication"}) == ("telecom", "torre")

def test_tower_communication_is_telecom():
    assert classify_infra({"man_made": "tower", "tower:type": "communication"}) == ("telecom", "torre")

def test_mast_without_tower_type_excluded():
    assert classify_infra({"man_made": "mast"}) is None

def test_power_tower_excluded():
    assert classify_infra({"power": "tower"}) is None

def test_power_pole_excluded():
    assert classify_infra({"power": "pole"}) is None

def test_power_cable_excluded():
    assert classify_infra({"power": "cable"}) is None

def test_waste_basket_excluded():
    assert classify_infra({"amenity": "waste_basket"}) is None
