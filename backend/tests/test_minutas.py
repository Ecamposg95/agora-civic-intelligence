import datetime as dt
from app.models.minuta import Minuta, Acuerdo


def test_minuta_and_acuerdo_persist(db_session):
    m = Minuta(
        organization_id="org-1", campaign_id="camp-1",
        titulo="Reunión de arranque", fecha=dt.date(2026, 7, 8),
        tipo="REUNION", estado="BORRADOR",
        asistentes=[{"nombre": "Lucy"}, {"user_id": "u-2", "nombre": "Juan"}],
        cuerpo="Notas de la reunión.",
    )
    db_session.add(m)
    db_session.flush()
    a = Acuerdo(
        organization_id="org-1", campaign_id="camp-1", minuta_id=m.id,
        texto="Levantar padrón de la sección 123", orden=0,
        estado="PENDIENTE", fecha_limite=dt.date(2026, 7, 15),
    )
    db_session.add(a)
    db_session.flush()
    assert m.id and a.minuta_id == m.id
    assert m.estado == "BORRADOR" and a.estado == "PENDIENTE"
    assert a.work_item_id is None
