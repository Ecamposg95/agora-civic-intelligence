import datetime as dt
import pytest
from app.schemas.scrum import SprintCreate, WorkItemCreate
from app.services import scrum_service


def _sprint_with_items(db, ctx, ini, fin):
    s = scrum_service.create_sprint(db, ctx, SprintCreate(nombre="S", fecha_inicio=ini, fecha_fin=fin))
    # 3 items: 5pts HECHO, 8pts HECHO, 3pts POR_HACER, 1 sin estimar POR_HACER
    a = scrum_service.create_workitem(db, ctx, WorkItemCreate(titulo="a", story_points=5, sprint_id=s.id))
    b = scrum_service.create_workitem(db, ctx, WorkItemCreate(titulo="b", story_points=8, sprint_id=s.id))
    scrum_service.create_workitem(db, ctx, WorkItemCreate(titulo="c", story_points=3, sprint_id=s.id))
    scrum_service.create_workitem(db, ctx, WorkItemCreate(titulo="d", story_points=None, sprint_id=s.id))
    scrum_service.mover_estado(db, ctx, a.id, "HECHO")
    scrum_service.mover_estado(db, ctx, b.id, "HECHO")
    return s


def test_sprint_metrics(db_session, coordinador_ctx):
    s = _sprint_with_items(db_session, coordinador_ctx, "2026-07-08", "2026-07-22")
    m = scrum_service.sprint_metrics(db_session, coordinador_ctx, s.id)
    assert m["comprometido"] == 16 and m["completado"] == 13
    assert m["historias_total"] == 4 and m["historias_hechas"] == 2
    assert m["por_estado"]["HECHO"] == 2 and m["por_estado"]["POR_HACER"] == 2
    assert m["sin_estimar"] == 1


def test_velocidad_only_closed_sprints(db_session, coordinador_ctx):
    """Order-independent: asserts on THIS test's own sprint, not global state.

    Other test modules (notably test_scrum_api.py, via the `client` fixture's
    separate DB session) may leave other CERRADO sprints in the shared SQLite
    DB depending on run order/selection. So this must not assume the velocidad
    list is empty before closing — only that THIS sprint's id is absent before
    close and present (with the right value) after.
    """
    s = _sprint_with_items(db_session, coordinador_ctx, "2026-06-01", "2026-06-15")
    # abierto → no aparece
    ids_before = [v["sprint_id"] for v in scrum_service.velocidad(db_session, coordinador_ctx, n=24)]
    assert s.id not in ids_before
    scrum_service.cerrar_sprint(db_session, coordinador_ctx, s.id)
    vel = scrum_service.velocidad(db_session, coordinador_ctx, n=24)
    entry = next(v for v in vel if v["sprint_id"] == s.id)
    assert entry["velocidad"] == 13


def test_burndown_series(db_session, coordinador_ctx):
    s = _sprint_with_items(db_session, coordinador_ctx, "2026-07-08", "2026-07-10")
    bd = scrum_service.burndown(db_session, coordinador_ctx, s.id)
    assert bd["total_puntos"] == 16
    assert len(bd["dias"]) == 3                       # inicio..fin inclusive
    assert bd["dias"][0]["ideal"] == 16 and bd["dias"][-1]["ideal"] == 0
    # restante nunca sube
    restantes = [d["restante"] for d in bd["dias"]]
    assert restantes == sorted(restantes, reverse=True)
