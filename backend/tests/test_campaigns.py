from app.models.catalog import Cargo, Party, Coalition, CoalitionParty


def test_catalog_models_exist_and_are_global():
    # Catalogs are platform reference data: no tenant column.
    assert not hasattr(Cargo, "organization_id")
    assert {c.name for c in Cargo.__table__.columns} >= {"id", "key", "label", "ambito", "territory_level"}
    assert {c.name for c in Party.__table__.columns} >= {"id", "key", "name", "short", "color"}
    assert {c.name for c in Coalition.__table__.columns} >= {"id", "key", "name", "color"}
    assert {c.name for c in CoalitionParty.__table__.columns} >= {"coalition_id", "party_id"}
