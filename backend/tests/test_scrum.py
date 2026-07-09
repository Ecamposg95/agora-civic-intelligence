import datetime as dt
import pytest
from pydantic import ValidationError
from app.models.audit_log import AuditLog
from app.models.scrum import Sprint, WorkItem, WorkItemTask
from app.models.user import User
from app.schemas.scrum import WorkItemCreate, SprintCreate, SprintUpdate, TaskCreate, TaskUpdate
from app.schemas.minuta import MinutaCreate
from app.services import scrum_service, minuta_service


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


def test_workitem_rejects_non_fibonacci_points():
    WorkItemCreate(titulo="H", story_points=8)          # ok
    WorkItemCreate(titulo="H2", story_points=None)       # ok (sin estimar)
    with pytest.raises(ValidationError):
        WorkItemCreate(titulo="bad", story_points=4)     # 4 no es Fibonacci


def test_sprint_create_defaults_estado():
    s = SprintCreate(nombre="S1", fecha_inicio="2026-07-08", fecha_fin="2026-07-22")
    assert s.estado == "PLANIFICACION"


def test_only_one_active_sprint(db_session, coordinador_ctx):
    s1 = scrum_service.create_sprint(db_session, coordinador_ctx,
        SprintCreate(nombre="S1", fecha_inicio="2026-07-08", fecha_fin="2026-07-22"))
    s2 = scrum_service.create_sprint(db_session, coordinador_ctx,
        SprintCreate(nombre="S2", fecha_inicio="2026-07-23", fecha_fin="2026-08-06"))
    scrum_service.activar_sprint(db_session, coordinador_ctx, s1.id)
    with pytest.raises(scrum_service.SprintActivoExiste):
        scrum_service.activar_sprint(db_session, coordinador_ctx, s2.id)
    assert scrum_service.active_sprint(db_session, coordinador_ctx).id == s1.id
    scrum_service.cerrar_sprint(db_session, coordinador_ctx, s1.id)
    assert scrum_service.active_sprint(db_session, coordinador_ctx) is None


def test_create_sprint_rejects_second_activo(db_session, coordinador_ctx):
    scrum_service.create_sprint(db_session, coordinador_ctx,
        SprintCreate(nombre="S1", fecha_inicio="2026-07-08", fecha_fin="2026-07-22",
                     estado="ACTIVO"))
    with pytest.raises(scrum_service.SprintActivoExiste):
        scrum_service.create_sprint(db_session, coordinador_ctx,
            SprintCreate(nombre="S2", fecha_inicio="2026-07-23", fecha_fin="2026-08-06",
                         estado="ACTIVO"))


def test_update_sprint_rejects_second_activo(db_session, coordinador_ctx):
    s1 = scrum_service.create_sprint(db_session, coordinador_ctx,
        SprintCreate(nombre="S1", fecha_inicio="2026-07-08", fecha_fin="2026-07-22",
                     estado="ACTIVO"))
    s2 = scrum_service.create_sprint(db_session, coordinador_ctx,
        SprintCreate(nombre="S2", fecha_inicio="2026-07-23", fecha_fin="2026-08-06"))
    with pytest.raises(scrum_service.SprintActivoExiste):
        scrum_service.update_sprint(db_session, coordinador_ctx, s2.id,
            SprintUpdate(estado="ACTIVO"))
    assert scrum_service.active_sprint(db_session, coordinador_ctx).id == s1.id


def test_create_sprint_activo_succeeds_when_none_active(db_session, coordinador_ctx):
    s = scrum_service.create_sprint(db_session, coordinador_ctx,
        SprintCreate(nombre="S1", fecha_inicio="2026-07-08", fecha_fin="2026-07-22",
                     estado="ACTIVO"))
    assert s.estado == "ACTIVO"
    assert scrum_service.active_sprint(db_session, coordinador_ctx).id == s.id


def test_assignee_moves_own_card_seals_completed_at(db_session, coordinador_ctx, activista_ctx):
    act_id = activista_ctx.user.id
    wi = scrum_service.create_workitem(db_session, coordinador_ctx,
        WorkItemCreate(titulo="H", story_points=5, responsable_id=act_id))
    # assignee moves own card to HECHO → completed_at sealed
    moved = scrum_service.mover_estado(db_session, activista_ctx, wi.id, "HECHO")
    assert moved.estado == "HECHO" and moved.completed_at is not None
    # moving out of HECHO clears completed_at
    back = scrum_service.mover_estado(db_session, coordinador_ctx, wi.id, "EN_CURSO")
    assert back.completed_at is None


def test_non_assignee_non_coordinator_cannot_move(db_session, coordinador_ctx, activista_ctx, otro_activista_ctx):
    wi = scrum_service.create_workitem(db_session, coordinador_ctx,
        WorkItemCreate(titulo="H", story_points=3, responsable_id=activista_ctx.user.id))
    with pytest.raises(scrum_service.NoAutorizado):
        scrum_service.mover_estado(db_session, otro_activista_ctx, wi.id, "EN_CURSO")


def test_activista_cannot_create_workitem_via_service_is_governance(db_session, coordinador_ctx):
    # create is governance; service itself doesn't gate role (router does), but
    # board groups by active sprint estado
    scrum_service.create_workitem(db_session, coordinador_ctx, WorkItemCreate(titulo="A", story_points=8))
    b = scrum_service.board(db_session, coordinador_ctx)
    assert "POR_HACER" in b and "EN_CURSO" in b and "HECHO" in b


def test_task_toggle_by_assignee_and_convert_acuerdo(db_session, coordinador_ctx, activista_ctx):
    wi = scrum_service.create_workitem(db_session, coordinador_ctx,
        WorkItemCreate(titulo="H", story_points=5, responsable_id=activista_ctx.user.id))
    t = scrum_service.add_task(db_session, coordinador_ctx, wi.id, TaskCreate(texto="paso 1"))
    done = scrum_service.update_task(db_session, activista_ctx, wi.id, t.id, TaskUpdate(done=True))
    assert done.done is True
    # convert an acuerdo (from a minuta) into a WorkItem
    m = minuta_service.create_minuta(db_session, coordinador_ctx,
        MinutaCreate(titulo="Acta", fecha="2026-07-08",
                     acuerdos=[{"texto": "Comprar lonas"}]))
    ac = m.acuerdos[0]
    new_wi = scrum_service.convertir_acuerdo(db_session, coordinador_ctx, m.id, ac.id)
    assert new_wi.origin_acuerdo_id == ac.id and new_wi.titulo == "Comprar lonas"
    db_session.refresh(ac)
    assert ac.work_item_id == new_wi.id
    with pytest.raises(scrum_service.YaConvertido):
        scrum_service.convertir_acuerdo(db_session, coordinador_ctx, m.id, ac.id)


def test_task_toggle_denied_for_non_owner(db_session, coordinador_ctx, activista_ctx, otro_activista_ctx):
    # workitem assigned to activista_ctx; task has no responsable → otro_activista is
    # neither coordinator, task-owner, nor parent-owner → NoAutorizado.
    wi = scrum_service.create_workitem(db_session, coordinador_ctx,
        WorkItemCreate(titulo="H", story_points=3, responsable_id=activista_ctx.user.id))
    t = scrum_service.add_task(db_session, coordinador_ctx, wi.id, TaskCreate(texto="paso"))
    with pytest.raises(scrum_service.NoAutorizado):
        scrum_service.update_task(db_session, otro_activista_ctx, wi.id, t.id, TaskUpdate(done=True))


def test_create_sprint_audit_row_has_entity_id(db_session, coordinador_ctx):
    sprint = scrum_service.create_sprint(db_session, coordinador_ctx,
        SprintCreate(nombre="S1", fecha_inicio="2026-07-08", fecha_fin="2026-07-22"))
    row = db_session.query(AuditLog).filter(AuditLog.action == "sprint.create").one()
    assert row.entity_id == sprint.id
    assert row.entity_id is not None


def test_create_workitem_audit_row_has_entity_id(db_session, coordinador_ctx):
    wi = scrum_service.create_workitem(db_session, coordinador_ctx,
        WorkItemCreate(titulo="H", story_points=5))
    row = db_session.query(AuditLog).filter(AuditLog.action == "workitem.create").one()
    assert row.entity_id == wi.id
    assert row.entity_id is not None
