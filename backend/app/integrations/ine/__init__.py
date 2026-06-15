"""INE México data-source integrations.

Modules:
  - ``ckan``         datos.gob.mx CKAN API (open-data catalog)
  - ``candidaturas`` Candidaturas MX (SocialTIC) Popolo API
  - ``cartografia``  SIGE / Marco Geográfico Electoral (WMS + GeoJSON)
  - ``prep``         PREP / Cómputos results (ZIP + CSV)
  - ``padron``       Padrón / Lista Nominal statistics (via CKAN)
  - ``config``       base URLs, level mapping, source registry
"""

from app.integrations.ine import (  # noqa: F401
    candidaturas,
    cartografia,
    ckan,
    config,
    padron,
    prep,
)
