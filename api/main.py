"""Point d'entrée FastAPI. Lancement local : `uv run uvicorn api.main:app --reload`.

Sans état : ni base, ni fichier écrit, ni journal des saisies (décision 0002).
"""

from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

import moteur

# Les pages /docs et /redoc de FastAPI chargent leurs scripts depuis un CDN : désactivées,
# l'application n'appelle aucun tiers. Le schéma généré reste servi sur /openapi.json.
app = FastAPI(title="Zodiaque B13", version=moteur.__version__, docs_url=None, redoc_url=None)


class HealthResponse(BaseModel):
    """Réponse de la route de santé."""

    status: Literal["ok"]


@app.get("/health")
def health() -> HealthResponse:
    """Indique que le service répond. Ne lit ni n'écrit aucune donnée."""
    return HealthResponse(status="ok")
