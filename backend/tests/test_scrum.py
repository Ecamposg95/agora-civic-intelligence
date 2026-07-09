import datetime as dt
from app.models.scrum import Sprint, WorkItem, WorkItemTask


def test_scrum_entities_persist(db_session):
    s = Sprint(organization_id="org-1", campaign_id="camp-1", nombre="Sprint 1",
               fecha_inicio=dt.date(2026, 7, 8), fecha_fin=dt.date(2026, 7, 22),
               estado="PLANIFICACION")
    db_session.add(s); db_session.flush()
    wi = WorkItem(organization_id="org-1", campaign_id="camp-1", titulo="Historia A",
                  tipo="HISTORIA", story_points=5, estado="POR_HACER", prioridad="MEDIA",
                  orden=0, sprint_id=s.id)
    db_session.add(wi); db_session.flush()
    t = WorkItemTask(organization_id="org-1", campaign_id="camp-1", work_item_id=wi.id,
                     texto="subtarea", done=False, orden=0)
    db_session.add(t); db_session.flush()
    assert wi.sprint_id == s.id and wi.completed_at is None
    assert wi.origin_acuerdo_id is None and t.work_item_id == wi.id
