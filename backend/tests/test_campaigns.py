from app.models.catalog import Cargo, Party, Coalition, CoalitionParty


def test_catalog_models_exist_and_are_global():
    # Catalogs are platform reference data: no tenant column.
    assert not hasattr(Cargo, "organization_id")
    assert {c.name for c in Cargo.__table__.columns} >= {"id", "key", "label", "ambito", "territory_level"}
    assert {c.name for c in Party.__table__.columns} >= {"id", "key", "name", "short", "color"}
    assert {c.name for c in Coalition.__table__.columns} >= {"id", "key", "name", "color"}
    assert {c.name for c in CoalitionParty.__table__.columns} >= {"coalition_id", "party_id"}


from app.models.campaign import Campaign, Contest, CampaignMembership, CampaignStatus
from app.models.base import CampaignMixin


def test_campaign_contest_membership_shape():
    assert {c.name for c in Campaign.__table__.columns} >= {"id", "organization_id", "name", "cycle", "status"}
    assert {c.name for c in Contest.__table__.columns} >= {"id", "organization_id", "campaign_id", "cargo_id", "territory_id", "election_date"}
    assert {c.name for c in CampaignMembership.__table__.columns} >= {"id", "user_id", "campaign_id", "role"}
    col = CampaignMixin.__dict__["campaign_id"]
    assert col is not None
    assert CampaignStatus.DRAFT.value == "draft"
