"""Télécharge les données déclarées dans donnees/sources.toml et contrôle leurs empreintes.

Régime « mesure » : les fichiers sont pris tels quels, jamais modifiés ni analysés ici.
Bibliothèque standard, plus `certifi` pour le magasin de certificats.

Usage :
    uv run python scripts/telecharger.py                 télécharge ce qui manque
    uv run python scripts/telecharger.py --source de440s une seule source
    uv run python scripts/telecharger.py --verifier      contrôle sans télécharger ni écrire

Règles :
- rien n'est téléchargé qui ne figure pas dans le registre ; HTTPS seulement ;
- le téléchargement passe par un fichier temporaire, puis est déplacé dans $B13_DONNEES
  (par défaut donnees/telechargees/) ; `miroir` est essayé si `url` échoue ;
- si une empreinte est déclarée et diffère, le fichier temporaire est supprimé : erreur ;
- un fichier présent n'est jamais écrasé ;
- le script n'écrit pas dans donnees/sources.toml : il propose la ligne, Micky valide.

Code de sortie : 0 si toutes les sources demandées sont présentes et conformes à leur empreinte
déclarée ; 1 sinon (fichier absent, empreinte à figer, empreinte différente, échec).
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import http.client
import json
import os
import re
import ssl
import sys
import tempfile
import tomllib
import urllib.parse
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import certifi

RACINE = Path(__file__).resolve().parents[1]
REGISTRE = RACINE / "donnees" / "sources.toml"
MANIFESTE = RACINE / "generes" / "manifest.json"

# Nom de client neutre : aucune information sur le projet ni sur la personne n'est envoyée.
AGENT = "donnees-fetch/1.0"
DELAI_SECONDES = 120
BLOC = 1 << 20
REDIRECTIONS_MAX = 5
EMPREINTE = re.compile(r"[0-9a-f]{64}")

NomEtat = Literal["absent", "a_figer", "conforme", "different", "echec"]
Recuperer = Callable[[str, Path], str | None]
"""Télécharge une URL vers un chemin ; rend l'en-tête Last-Modified s'il existe."""


class ErreurRegistre(Exception):
    """Le registre donnees/sources.toml est invalide."""


class ErreurTelechargement(Exception):
    """Une URL n'a pas pu être récupérée."""


class ErreurManifeste(Exception):
    """generes/manifest.json est illisible ou n'a pas la forme attendue."""


@dataclass(frozen=True)
class Source:
    id: str
    fichier: str
    url: str
    miroir: str | None
    sha256: str  # chaîne vide : empreinte pas encore figée


@dataclass(frozen=True)
class Etat:
    source: Source
    etat: NomEtat
    sha256: str | None = None  # empreinte calculée du fichier présent
    taille: int | None = None  # en octets
    url: str | None = None  # URL effectivement utilisée, si téléchargé pendant cet appel
    derniere_modification: str | None = None  # en-tête Last-Modified du serveur
    telecharge: bool = False
    message: str = ""


def dossier_donnees() -> Path:
    """Dossier des fichiers téléchargés : $B13_DONNEES, sinon donnees/telechargees/."""
    variable = os.environ.get("B13_DONNEES")
    if variable is None:
        return RACINE / "donnees" / "telechargees"
    if not variable.strip():
        # integrite.py lirait alors le répertoire courant : mieux vaut s'arrêter que diverger.
        raise ErreurRegistre("B13_DONNEES est définie mais vide : supprime-la ou donne un chemin")
    return Path(variable)


def sha256_fichier(chemin: Path) -> str:
    h = hashlib.sha256()
    with chemin.open("rb") as f:
        for bloc in iter(lambda: f.read(BLOC), b""):
            h.update(bloc)
    return h.hexdigest()


def _url_https(valeur: object, champ: str, identifiant: str) -> str:
    if not isinstance(valeur, str) or not valeur.startswith("https://"):
        raise ErreurRegistre(f"source « {identifiant} » : `{champ}` doit être une URL en https://")
    return valeur


def lire_registre(chemin: Path = REGISTRE) -> list[Source]:
    """Sources à télécharger. Les sources de type « paquet » viennent d'une dépendance : ignorées."""
    try:
        donnees = tomllib.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as erreur:
        raise ErreurRegistre(f"{chemin} illisible : {erreur}") from erreur
    sources: list[Source] = []
    for entree in donnees.get("source", []):
        if entree.get("type") == "paquet":
            continue
        identifiant = entree.get("id")
        if not isinstance(identifiant, str) or not identifiant:
            raise ErreurRegistre("une source n'a pas d'identifiant `id`")
        if any(s.id == identifiant for s in sources):
            raise ErreurRegistre(f"source « {identifiant} » déclarée deux fois")
        fichier = entree.get("fichier")
        if (
            not isinstance(fichier, str)
            or fichier in {"", ".", ".."}
            or Path(fichier).name != fichier
        ):
            raise ErreurRegistre(
                f"source « {identifiant} » : `fichier` doit être un nom simple, sans dossier"
            )
        if any(s.fichier == fichier for s in sources):
            raise ErreurRegistre(f"fichier « {fichier} » déclaré par deux sources")
        # Même lecture que scripts/verifications/integrite.py : l'empreinte n'est pas normalisée.
        empreinte = entree.get("sha256", "")
        if not isinstance(empreinte, str) or not (
            empreinte == "" or EMPREINTE.fullmatch(empreinte)
        ):
            raise ErreurRegistre(
                f"source « {identifiant} » : `sha256` doit être vide ou compter 64 chiffres "
                "hexadécimaux en minuscules"
            )
        miroir = entree.get("miroir")
        sources.append(
            Source(
                id=identifiant,
                fichier=fichier,
                url=_url_https(entree.get("url"), "url", identifiant),
                miroir=None if miroir is None else _url_https(miroir, "miroir", identifiant),
                sha256=empreinte,
            )
        )
    return sources


def contexte_tls() -> ssl.SSLContext:
    """Vérification complète du certificat et du nom d'hôte, avec le magasin `certifi`."""
    return ssl.create_default_context(cafile=certifi.where())


def _connexion(hote: str, port: int) -> http.client.HTTPSConnection:
    """Connexion TLS vers `hote`, par le mandataire HTTPS de l'environnement s'il y en a un.

    Certificats : magasin `certifi` (celui du système ne valide pas les hôtes du JPL).
    La connexion reste ouverte (pas d'en-tête `Connection: close`) : certains mandataires
    perdent la fin du fichier quand le serveur ferme la connexion.
    """
    contexte = contexte_tls()
    mandataire = urllib.request.getproxies().get("https")
    if not mandataire or urllib.request.proxy_bypass(hote):
        return http.client.HTTPSConnection(hote, port, timeout=DELAI_SECONDES, context=contexte)
    parties = urllib.parse.urlsplit(mandataire)
    if parties.scheme != "http" or not parties.hostname:
        raise ErreurTelechargement("mandataire HTTPS non pris en charge (schéma http attendu)")
    entetes: dict[str, str] = {}
    if parties.username:
        identifiants = (
            f"{urllib.parse.unquote(parties.username)}:"
            f"{urllib.parse.unquote(parties.password or '')}"
        )
        entetes["Proxy-Authorization"] = "Basic " + base64.b64encode(identifiants.encode()).decode()
    connexion = http.client.HTTPSConnection(
        parties.hostname, parties.port or 80, timeout=DELAI_SECONDES, context=contexte
    )
    connexion.set_tunnel(hote, port, headers=entetes)
    return connexion


def recuperer_https(url: str, destination: Path) -> str | None:
    """Télécharge `url` vers `destination` et rend l'en-tête Last-Modified.

    Échoue si la réponse n'est pas un 200, si elle redirige hors HTTPS ou vers un autre hôte
    (seules les URL du registre sont téléchargées), ou si la taille reçue diffère de la taille
    annoncée par le serveur.
    """
    courante = url
    for _ in range(REDIRECTIONS_MAX + 1):
        parties = urllib.parse.urlsplit(courante)
        if parties.scheme != "https" or not parties.hostname:
            raise ErreurTelechargement(f"{url} : redirigé hors HTTPS vers {courante}")
        cible = (parties.path or "/") + (f"?{parties.query}" if parties.query else "")
        try:
            connexion = _connexion(parties.hostname, parties.port or 443)
            try:
                connexion.request(
                    "GET", cible, headers={"User-Agent": AGENT, "Accept-Encoding": "identity"}
                )
                reponse = connexion.getresponse()
                if reponse.status in {301, 302, 303, 307, 308}:
                    suite = urllib.parse.urljoin(courante, reponse.getheader("Location") or "")
                    arrivee = urllib.parse.urlsplit(suite)
                    if (arrivee.hostname, arrivee.port or 443) != (
                        parties.hostname,
                        parties.port or 443,
                    ):
                        raise ErreurTelechargement(
                            f"{url} : redirigé vers un autre hôte ({suite}), absent du registre"
                        )
                    courante = suite
                    continue
                if reponse.status != 200:
                    raise ErreurTelechargement(f"{url} : réponse HTTP {reponse.status}")
                # Complétude : taille annoncée, ou envoi par fragments (http.client détecte alors
                # une fin prématurée). Sans l'un ni l'autre, un fichier tronqué passerait inaperçu.
                annonce = reponse.getheader("Content-Length")
                fragmente = (reponse.getheader("Transfer-Encoding") or "").lower() == "chunked"
                if not fragmente and not (annonce and annonce.isdigit()):
                    raise ErreurTelechargement(
                        f"{url} : taille non annoncée par le serveur, complétude invérifiable"
                    )
                recu = 0
                with destination.open("wb") as sortie:
                    while bloc := reponse.read(BLOC):
                        sortie.write(bloc)
                        recu += len(bloc)
                if not fragmente and annonce and recu != int(annonce):
                    raise ErreurTelechargement(
                        f"{url} : téléchargement incomplet, {recu} octets reçus sur {annonce}"
                    )
                return reponse.getheader("Last-Modified")
            finally:
                connexion.close()
        except (OSError, http.client.HTTPException, ValueError) as erreur:
            raise ErreurTelechargement(f"{url} : {erreur}") from erreur
    raise ErreurTelechargement(f"{url} : trop de redirections")


def controler(source: Source, dossier: Path) -> Etat:
    """État d'une source d'après le fichier présent, sans rien télécharger ni écrire."""
    chemin = dossier / source.fichier
    if not chemin.is_file():
        return Etat(source, "absent", message="pas encore téléchargé")
    empreinte = sha256_fichier(chemin)
    taille = chemin.stat().st_size
    if not source.sha256:
        return Etat(source, "a_figer", empreinte, taille, message="empreinte à figer")
    if empreinte != source.sha256:
        return Etat(
            source,
            "different",
            empreinte,
            taille,
            message="le fichier présent n'a pas l'empreinte déclarée : modifié ou corrompu",
        )
    return Etat(source, "conforme", empreinte, taille)


def telecharger(source: Source, dossier: Path, recuperer: Recuperer = recuperer_https) -> Etat:
    """Télécharge une source si son fichier est absent. Un fichier présent n'est jamais écrasé."""
    present = controler(source, dossier)
    if present.etat != "absent":
        return present

    dossier.mkdir(parents=True, exist_ok=True)
    # Nom unique : deux lancements simultanés ne partagent pas leur fichier temporaire.
    descripteur, nom = tempfile.mkstemp(
        dir=dossier, prefix=f".{source.fichier}.", suffix=".partiel"
    )
    os.close(descripteur)
    temporaire = Path(nom)
    echecs: list[str] = []
    try:
        for url in [u for u in (source.url, source.miroir) if u]:
            try:
                derniere_modification = recuperer(url, temporaire)
            except ErreurTelechargement as erreur:
                echecs.append(str(erreur))
                temporaire.unlink(missing_ok=True)
                continue
            empreinte = sha256_fichier(temporaire)
            taille = temporaire.stat().st_size
            if source.sha256 and empreinte != source.sha256:
                return Etat(
                    source,
                    "different",
                    empreinte,
                    taille,
                    url,
                    derniere_modification,
                    message=(
                        "le fichier reçu n'a pas l'empreinte déclarée ; il n'a pas été gardé. "
                        "Le fichier distant a peut-être changé depuis que l'empreinte a été figée : "
                        "une nouvelle empreinte demande une décision datée"
                    ),
                )
            # Lien plutôt que renommage : échoue si le fichier est apparu entre-temps,
            # au lieu de l'écraser.
            temporaire.chmod(0o644)
            try:
                os.link(temporaire, dossier / source.fichier)
            except FileExistsError:
                return controler(source, dossier)
            return Etat(
                source,
                "conforme" if source.sha256 else "a_figer",
                empreinte,
                taille,
                url,
                derniere_modification,
                telecharge=True,
                message="" if source.sha256 else "empreinte à figer",
            )
        return Etat(source, "echec", message=" ; ".join(echecs) or "aucune URL")
    finally:
        temporaire.unlink(missing_ok=True)


def mettre_a_jour_manifeste(etats: Sequence[Etat], manifeste: Path, maintenant: datetime) -> None:
    """Inscrit dans generes/manifest.json les fichiers présents, sous la clé `sources`.

    Une entrée dont l'empreinte n'a pas changé est laissée telle quelle : la date de récupération
    reste celle de la copie figée. Les autres clés du manifeste ne sont pas touchées.
    """
    contenu: dict[str, object] = {}
    if manifeste.exists():
        try:
            lu = json.loads(manifeste.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as erreur:
            raise ErreurManifeste(f"{manifeste} illisible : {erreur}") from erreur
        if not isinstance(lu, dict):
            raise ErreurManifeste(f"{manifeste} : un objet JSON est attendu")
        contenu = lu
    brut = contenu.get("sources", {})
    if not isinstance(brut, dict):
        raise ErreurManifeste(f"{manifeste} : `sources` doit être un objet")
    sources: dict[str, object] = dict(brut)
    change = False
    for etat in etats:
        if etat.etat not in {"conforme", "a_figer"}:
            continue
        existante = sources.get(etat.source.id)
        if isinstance(existante, dict) and existante.get("sha256") == etat.sha256:
            continue
        # Les trois dernières clés sont toujours présentes : `null` quand le fichier n'a pas été
        # téléchargé pendant cet appel (copie restaurée, manifeste reconstruit).
        horodatage = maintenant.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        sources[etat.source.id] = {
            "file": etat.source.fichier,
            "sha256": etat.sha256,
            "bytes": etat.taille,
            "url": etat.url if etat.telecharge else None,
            "retrieved_at": horodatage if etat.telecharge else None,
            "last_modified": etat.derniere_modification if etat.telecharge else None,
        }
        change = True
    if not change:
        return
    contenu["sources"] = sources
    contenu.setdefault("files", {})
    manifeste.parent.mkdir(parents=True, exist_ok=True)
    # Écriture par fichier temporaire puis renommage : jamais de manifeste à moitié écrit.
    provisoire = manifeste.with_name(manifeste.name + ".partiel")
    try:
        provisoire.write_text(
            json.dumps(contenu, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        provisoire.replace(manifeste)
    finally:
        provisoire.unlink(missing_ok=True)


def _taille_lisible(octets: int | None) -> str:
    if octets is None:
        return "—"
    if octets >= 1 << 20:
        return f"{octets / (1 << 20):.1f} Mio"
    if octets >= 1 << 10:
        return f"{octets / (1 << 10):.1f} Kio"
    return f"{octets} o"


LIBELLES: dict[NomEtat, str] = {
    "absent": "absent",
    "a_figer": "à figer",
    "conforme": "conforme",
    "different": "DIFFÉRENT",
    "echec": "ÉCHEC",
}


def afficher(etats: Sequence[Etat]) -> None:
    for etat in etats:
        source = etat.source
        print(
            f"  {source.id:<22} {source.fichier:<22} {_taille_lisible(etat.taille):>10}  "
            f"{LIBELLES[etat.etat]}"
        )
        if etat.sha256:
            print(f"      sha256 {etat.sha256}")
        if etat.telecharge:
            print(f"      téléchargé depuis {etat.url}")
        if etat.message:
            print(f"      {etat.message}")
    a_figer = [e for e in etats if e.etat == "a_figer"]
    if a_figer:
        print()
        print("Empreintes à figer dans donnees/sources.toml (Micky valide chaque ligne) :")
        for etat in a_figer:
            print(f'  [{etat.source.id}]  sha256 = "{etat.sha256}"')


def main(
    argv: Sequence[str] | None = None,
    *,
    registre: Path = REGISTRE,
    dossier: Path | None = None,
    manifeste: Path = MANIFESTE,
    recuperer: Recuperer = recuperer_https,
    maintenant: datetime | None = None,
) -> int:
    analyseur = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    analyseur.add_argument("--source", metavar="ID", help="ne traiter que cette source")
    analyseur.add_argument(
        "--verifier", action="store_true", help="contrôler sans télécharger ni écrire"
    )
    options = analyseur.parse_args(argv)

    try:
        sources = lire_registre(registre)
        cible = dossier if dossier is not None else dossier_donnees()
    except ErreurRegistre as erreur:
        print(f"  ✘ {erreur}", file=sys.stderr)
        return 1
    if options.source is not None:
        sources = [s for s in sources if s.id == options.source]
        if not sources:
            print(
                f"  ✘ source « {options.source} » absente de donnees/sources.toml", file=sys.stderr
            )
            return 1

    manifeste_ok = True
    if options.verifier:
        etats = [controler(s, cible) for s in sources]
    else:
        etats = [telecharger(s, cible, recuperer) for s in sources]
        try:
            mettre_a_jour_manifeste(etats, manifeste, maintenant or datetime.now(UTC))
        except ErreurManifeste as erreur:
            print(f"  ✘ {erreur}", file=sys.stderr)
            manifeste_ok = False

    print(f"Données dans {cible}")
    afficher(etats)
    return 0 if manifeste_ok and all(e.etat == "conforme" for e in etats) else 1


if __name__ == "__main__":
    sys.exit(main())
