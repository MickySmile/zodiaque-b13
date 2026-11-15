"""Contrats de l'API : un modèle Pydantic par entrée et par sortie (annexe technique § F).

Champs en anglais, noms de l'annexe. Une valeur absente reste `null`, accompagnée d'un statut.
Les réponses refusent tout champ non déclaré : si le moteur change de forme, l'écart se voit.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Manifest = dict[str, Any]
DataStatus = Literal["verified", "candidate", "synthetic"]
FiniteFloat = Annotated[float, Field(allow_inf_nan=False)]
ShortText = Annotated[str, Field(max_length=64)]


class Request(BaseModel):
    """Entrée : types stricts, aucun champ inconnu. Le moteur contrôle ensuite les valeurs."""

    model_config = ConfigDict(extra="forbid", strict=True)


class Response(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- Erreurs ------------------------------------------------------------------------------------


class ErrorDetail(Response):
    code: str
    message: str  # en français, destiné à la personne ; ne reprend aucune saisie
    fields: list[str] | None = None  # noms des champs refusés, jamais leurs valeurs


class ErrorResponse(Response):
    error: ErrorDetail


# --- Santé --------------------------------------------------------------------------------------


class HealthResponse(Response):
    """Réponse de la route de santé."""

    status: Literal["ok"]


# --- Frontières : données de la roue ----------------------------------------------------------


class WheelSign(Response):
    sign_id: str
    name: str
    glyph: str
    start_deg: float
    end_deg: float
    width_deg: float


class Orientation(Response):
    anchor: Literal["zero_longitude_left"]
    direction: Literal["counterclockwise"]


class WheelResponse(Response):
    status: DataStatus
    data_status: DataStatus
    reference_frame_id: str
    boundary_model_id: str
    boundary_validation_status: str
    interval_policy: str
    orientation: Orientation
    signs: list[WheelSign]
    houses: None
    houses_status: str
    angles: None
    angles_status: str
    bodies: list[Any]
    aspects: None
    aspects_status: str
    manifest: Manifest


# --- Fiches -------------------------------------------------------------------------------------


class SignSheet(Response):
    sign_id: str
    name: str
    glyph: str
    sheet: None
    sheet_status: Literal["not_transcribed"]
    epistemic_status: Literal["symbolic_proposal"]


class SignsResponse(Response):
    data_status: DataStatus
    signs: list[SignSheet]
    manifest: Manifest


# --- Signe solaire ------------------------------------------------------------------------------


class BirthRequest(Request):
    """Saisie de naissance (annexe F). Donnée personnelle : jamais conservée ni journalisée."""

    date_local: ShortText
    time_local: ShortText | None = None
    time_status: Literal["known", "uncertain", "unknown"]
    time_uncertainty_seconds: FiniteFloat = 0.0
    timezone: ShortText
    fold: int | None = None
    latitude_deg: FiniteFloat
    longitude_deg: FiniteFloat
    altitude_m: FiniteFloat | None = None
    calendar: ShortText = "proleptic_gregorian"
    source: ShortText | None = None


class ModelBlock(Response):
    id: str
    reference_frame: str
    boundary_source_equinox: str
    boundary_sha256: str | None
    interval_policy: str
    validation_status: str


class PositionBlock(Response):
    body: str
    body_identifier: int
    target_kind: str
    longitude_deg: float
    latitude_deg: float


class ClassificationBlock(Response):
    sign_id: str | None
    degrees_in_sign: float | None
    fraction_in_sign: float | None
    status: Literal["certain", "possible"]
    possible_signs: list[str]


class TransitionBlock(Response):
    instant_utc: str
    from_sign: str
    to_sign: str
    boundary_deg: float


class UncertaintyBlock(Response):
    time_interval_utc: list[str] | None
    longitude_interval_deg: list[float] | None
    input_probability_distribution: None
    transitions: list[TransitionBlock]


class InterpretationBlock(Response):
    ruleset_id: None
    epistemic_status: Literal["symbolic_proposal"]
    text: None


class ScenarioBlock(Response):
    fold: int
    instant_utc: str
    utc_offset_seconds: int
    time_scale: str
    conditional: bool
    position: PositionBlock
    classification: ClassificationBlock
    uncertainty: UncertaintyBlock
    interpretation: InterpretationBlock


class SunSignResponse(Response):
    title: str | None
    time_status: Literal["known", "uncertain", "unknown"]
    local_time_kind: Literal["unique", "ambiguous", "unknown"]
    data_status: DataStatus
    model: ModelBlock
    scenarios: list[ScenarioBlock]
    ascendant: None
    ascendant_status: str
    houses: None
    houses_status: str
    timezone_caveat: str | None
    manifest: Manifest


# --- Calendrier ---------------------------------------------------------------------------------


class CalendarEntry(Response):
    sign_id: str
    boundary_deg: float
    tt_jd: float
    instant_utc: str
    instant_local: str
    time_scale: str
    conditional: bool
    residual_deg: float


class CalendarResponse(Response):
    year: int
    timezone: str
    entries: list[CalendarEntry]
    notice: str
    time_notice: str
    data_status: DataStatus
    timezone_caveat: str | None
    manifest: Manifest


# --- Lieux --------------------------------------------------------------------------------------


class PlaceSearchRequest(Request):
    """Recherche d'un lieu de naissance : donnée personnelle, transmise dans le corps."""

    query: Annotated[str, Field(max_length=100)]
    limit: Annotated[int, Field(ge=1, le=20)] = 8


class PlaceBlock(Response):
    geoname_id: int
    name: str
    admin1_name: str | None
    country_code: str
    latitude_deg: float
    longitude_deg: float
    timezone: str
    population: int


class PlaceSearchResponse(Response):
    places: list[PlaceBlock]
    attribution: str
    data_status: DataStatus
    manifest: Manifest


class TimezoneRequest(Request):
    latitude_deg: FiniteFloat
    longitude_deg: FiniteFloat


class TimezoneResponse(Response):
    timezone: str | None
    status: Literal["found", "no_civil_timezone", "unknown_to_timezone_database"]
    needs_confirmation: Literal[True]
    data_status: DataStatus
    manifest: Manifest
