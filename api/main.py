"""Point d'entrée FastAPI. Lancement local : `uv run uvicorn api.main:app --reload`.

Sans état : ni base, ni fichier écrit, ni journal des saisies (décision 0002). Chaque route
appelle le moteur et rend son résultat, avec le manifeste et le statut des données.

Confidentialité : date, heure et lieu de naissance ne voyagent que dans le corps d'une requête
POST, jamais dans une adresse (le journal d'accès du serveur écrit les adresses). Un message
d'erreur ne reprend aucune valeur saisie, et une panne imprévue n'écrit au journal que le type
de l'erreur et l'endroit du code : jamais son message, qui pourrait contenir une valeur.
"""

from __future__ import annotations

import logging
import traceback
from collections.abc import Awaitable, Callable
from dataclasses import asdict
from datetime import UTC
from typing import Annotated, Any

from fastapi import FastAPI, Path, Query, Request, Response
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.responses import JSONResponse
from fastapi.telemetry import TelemetryConfig
from starlette.exceptions import HTTPException as StarletteHTTPException

import moteur
from api import schemas
from api.catalogue import SIGN_LABELS
from moteur import natal, passages, places
from moteur.boundaries import INTERVAL_POLICY, BoundaryError
from moteur.civil_time import BirthInput, InputError, NonexistentLocalTime, load_zone
from moteur.classification import ClassificationError, Zodiac, load_canonical
from moteur.coordinates import REFERENCE_FRAME
from moteur.manifest import boundary_manifest
from moteur.positions import EphemerisUnavailable, OutOfEphemerisRange, PositionError

NOT_COMPUTED = "not_computed_in_this_version"
logger = logging.getLogger("zodiaque_b13.api")

# Télémétrie native de FastAPI (OpenTelemetry) : entièrement coupée. Activée, elle enregistrerait
# les échecs de validation et les exceptions avec leurs messages, donc des saisies, et une simple
# variable d'environnement suffirait à les exporter vers un tiers.
TELEMETRY_OFF: TelemetryConfig = {
    "tracing": False,
    "metrics": False,
    "logs": False,
    "operation_spans": False,
    "auto_configure": False,
}

# Les pages /docs et /redoc de FastAPI chargent leurs scripts depuis un CDN : désactivées,
# l'application n'appelle aucun tiers. Le schéma généré reste servi sur /openapi.json.
app = FastAPI(
    title="Zodiaque B13",
    version=moteur.__version__,
    docs_url=None,
    redoc_url=None,
    telemetry=TELEMETRY_OFF,
)

ERRORS: dict[int | str, dict[str, Any]] = {
    422: {"model": schemas.ErrorResponse, "description": "Saisie refusée"},
    500: {"model": schemas.ErrorResponse, "description": "Calcul arrêté"},
    503: {"model": schemas.ErrorResponse, "description": "Données locales indisponibles"},
}


# --- Erreurs : code explicite, message en français, ni trace ni saisie ---------------------------


def _error(status: int, code: str, message: str, fields: list[str] | None = None) -> JSONResponse:
    detail = schemas.ErrorDetail(code=code, message=message, fields=fields)
    body = schemas.ErrorResponse(error=detail).model_dump(exclude_none=True)
    return JSONResponse(status_code=status, content=body)


def _sentence(error: Exception) -> str:
    """Message du moteur, présenté comme une phrase. Le moteur n'y met aucune valeur saisie."""
    text = str(error)
    return text[:1].upper() + text[1:] + ("" if text.endswith(".") else ".")


# Noms de champs que l'API connaît. Un nom inconnu vient du client : il n'est pas répété.
_KNOWN_FIELDS = frozenset(
    {"year", "timezone"}
    | set(schemas.BirthRequest.model_fields)
    | set(schemas.PlaceSearchRequest.model_fields)
    | set(schemas.TimezoneRequest.model_fields)
)
UNKNOWN_FIELD = "unknown_field"


@app.exception_handler(RequestValidationError)
def _invalid_request(_: Request, error: RequestValidationError) -> JSONResponse:
    # Seuls les noms des champs sont rendus : le détail de Pydantic reprendrait les valeurs.
    names = {str(item["loc"][-1]) for item in error.errors() if item.get("loc")}
    fields = sorted({name if name in _KNOWN_FIELDS else UNKNOWN_FIELD for name in names})
    return _error(
        422,
        "invalid_request",
        "Requête refusée : un champ manque, est en trop ou n'a pas la forme attendue.",
        fields,
    )


@app.exception_handler(NonexistentLocalTime)
def _nonexistent_time(_: Request, error: NonexistentLocalTime) -> JSONResponse:
    return _error(422, "nonexistent_local_time", _sentence(error))


@app.exception_handler(InputError)
def _invalid_input(_: Request, error: InputError) -> JSONResponse:
    return _error(422, "invalid_input", _sentence(error))


@app.exception_handler(places.PlaceQueryError)
def _invalid_place_query(_: Request, error: places.PlaceQueryError) -> JSONResponse:
    return _error(422, "invalid_input", _sentence(error))


@app.exception_handler(OutOfEphemerisRange)
def _out_of_range(_: Request, error: OutOfEphemerisRange) -> JSONResponse:
    return _error(422, "out_of_ephemeris_range", _sentence(error))


@app.exception_handler(EphemerisUnavailable)
def _no_ephemeris(_: Request, __: EphemerisUnavailable) -> JSONResponse:
    return _error(
        503,
        "ephemeris_unavailable",
        "Éphéméride indisponible sur ce serveur : aucune position n'est calculée, "
        "aucune valeur approchée n'est proposée.",
    )


@app.exception_handler(places.PlacesUnavailable)
def _no_places(_: Request, __: places.PlacesUnavailable) -> JSONResponse:
    return _error(
        503,
        "places_unavailable",
        "Recherche de lieu indisponible sur ce serveur : saisissez la latitude et la longitude.",
    )


def _stopped(_: Request, __: Exception) -> JSONResponse:
    return _error(
        500,
        "calculation_stopped",
        "Le calcul s'est arrêté sur un contrôle interne : aucun résultat n'est rendu.",
    )


for _stopping in (ClassificationError, BoundaryError, PositionError, passages.PassageError):
    app.add_exception_handler(_stopping, _stopped)


_HTTP_ERRORS = {
    404: ("not_found", "Adresse inconnue de l'API."),
    405: ("method_not_allowed", "Méthode refusée pour cette adresse."),
}


@app.exception_handler(StarletteHTTPException)
def _http_error(_: Request, error: StarletteHTTPException) -> JSONResponse:
    # Adresse inconnue, méthode refusée, corps illisible : même forme que les autres erreurs.
    code, message = _HTTP_ERRORS.get(
        error.status_code, ("invalid_request", "Requête refusée : elle n'a pas la forme attendue.")
    )
    return _error(error.status_code, code, message)


@app.middleware("http")
async def _contain_unexpected_errors(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Panne imprévue : réponse fixe, et rien de plus au journal que son type et son lieu.

    Sans cela, le serveur écrirait le message de l'exception. Or une réponse qui ne correspond
    plus à son modèle produit un message qui cite ses valeurs, dont l'instant de naissance.
    """
    try:
        return await call_next(request)
    except Exception as error:  # noqa: BLE001 — tout doit être contenu ici
        frames = traceback.extract_tb(error.__traceback__)
        place = f"{frames[-1].filename}:{frames[-1].lineno}" if frames else "lieu inconnu"
        logger.error("erreur interne %s (%s)", type(error).__name__, place)
        if isinstance(error, ResponseValidationError):
            # Pour le diagnostic : quel champ rompt le contrat et pourquoi, jamais sa valeur.
            for item in error.errors():
                logger.error(
                    "réponse hors contrat : %s à %s",
                    item.get("type"),
                    ".".join(str(part) for part in item.get("loc", ())),
                )
        return _error(500, "internal_error", "Erreur interne : aucun résultat n'est rendu.")


# --- Aides ------------------------------------------------------------------------------------------


def _status(zodiac: Zodiac) -> str:
    """Statut des données : « candidate » tant que la porte G1 n'est pas franchie."""
    return str(boundary_manifest(zodiac)["data_status"])


def _labelled(zodiac: Zodiac) -> list[dict[str, Any]]:
    """Les 13 signes dans l'ordre du découpage, chacun avec son nom : une seule forme."""
    return [{**asdict(sign), **asdict(SIGN_LABELS[sign.sign_id])} for sign in zodiac.signs]


# --- Routes -----------------------------------------------------------------------------------------


@app.get("/health")
def health() -> schemas.HealthResponse:
    """Indique que le service répond. Ne lit ni n'écrit aucune donnée."""
    return schemas.HealthResponse(status="ok")


@app.get("/api/boundaries", response_model=schemas.WheelResponse, responses=ERRORS)
def boundaries() -> dict[str, Any]:
    """Les 13 intervalles du modèle B, tels que générés : les données de la roue."""
    zodiac = load_canonical()
    manifest = boundary_manifest(zodiac)
    return {
        "status": manifest["data_status"],
        "data_status": manifest["data_status"],
        "reference_frame_id": REFERENCE_FRAME,
        "boundary_model_id": manifest["model_id"],
        "boundary_validation_status": manifest["validation_status"],
        "interval_policy": INTERVAL_POLICY,
        # Aucun Ascendant n'est calculé dans cette version : la roue ne s'oriente pas sur lui.
        "orientation": {"anchor": "zero_longitude_left", "direction": "counterclockwise"},
        "signs": _labelled(zodiac),
        "houses": None,
        "houses_status": NOT_COMPUTED,
        "angles": None,
        "angles_status": NOT_COMPUTED,
        "bodies": [],
        "aspects": None,
        "aspects_status": NOT_COMPUTED,
        "manifest": manifest,
    }


@app.get("/api/signs", response_model=schemas.SignsResponse, responses=ERRORS)
def signs() -> dict[str, Any]:
    """Les 13 fiches de signe. Le référentiel B13 n'est pas encore transcrit : fiches absentes."""
    zodiac = load_canonical()
    manifest = boundary_manifest(zodiac)
    return {
        "data_status": manifest["data_status"],
        "signs": [
            {
                "sign_id": sign.sign_id,
                **asdict(SIGN_LABELS[sign.sign_id]),
                "sheet": None,
                "sheet_status": "not_transcribed",
                "epistemic_status": "symbolic_proposal",
            }
            for sign in zodiac.signs
        ],
        "manifest": manifest,
    }


@app.post("/api/sun-sign", response_model=schemas.SunSignResponse, responses=ERRORS)
def sun_sign(birth: schemas.BirthRequest) -> dict[str, object]:
    """Signe solaire B13 d'une saisie de naissance, avec ses signes possibles."""
    chart = natal.sun_sign_chart(BirthInput.from_record(birth.model_dump()))
    return natal.as_record(chart)


@app.get("/api/calendar/{year}", response_model=schemas.CalendarResponse, responses=ERRORS)
def calendar(
    year: Annotated[int, Path(ge=1, le=9998)],
    timezone: Annotated[str, Query(max_length=64)] = passages.DEFAULT_TIMEZONE,
) -> dict[str, Any]:
    """Entrées du Soleil dans les 13 signes pendant une année, en UTC et en heure locale."""
    load_zone(timezone)  # fuseau refusé avant tout calcul, même sans éphéméride
    result = passages.sun_entries(year, timezone)
    return {
        "year": result.year,
        "timezone": result.timezone,
        "entries": [
            {
                "sign_id": entry.sign_id,
                "boundary_deg": entry.boundary_deg,
                "tt_jd": entry.tt_jd,
                "instant_utc": entry.instant_utc.astimezone(UTC).isoformat(),
                "instant_local": entry.instant_local.isoformat(),
                "time_scale": entry.time_scale,
                "conditional": entry.conditional,
                "residual_deg": entry.residual_deg,
            }
            for entry in result.entries
        ],
        "notice": result.notice,
        "time_notice": result.time_notice,
        "data_status": result.data_status,
        "timezone_caveat": result.timezone_caveat,
        "manifest": result.manifest,
    }


@app.post("/api/places/search", response_model=schemas.PlaceSearchResponse, responses=ERRORS)
def search_places(request: schemas.PlaceSearchRequest) -> dict[str, Any]:
    """Localités dont le nom commence par la recherche. Aucune : liste vide, jamais un voisin."""
    index = places.load_places()
    return {
        "places": [asdict(place) for place in index.search(request.query, request.limit)],
        "attribution": places.GEONAMES_ATTRIBUTION,
        "data_status": _status(load_canonical()),
        "manifest": index.manifest(),
    }


@app.post("/api/places/timezone", response_model=schemas.TimezoneResponse, responses=ERRORS)
def timezone_of(request: schemas.TimezoneRequest) -> dict[str, Any]:
    """Fuseau civil de coordonnées saisies à la main, à confirmer par la personne."""
    found = places.timezone_at(request.latitude_deg, request.longitude_deg)
    return {
        "timezone": found.timezone,
        "status": found.status,
        "needs_confirmation": True,
        "data_status": _status(load_canonical()),
        "manifest": places.lookup_manifest(),
    }
