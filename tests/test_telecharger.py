"""Contrat de scripts/telecharger.py (skill `donnees`). Aucun accès au réseau : la récupération est simulée."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from scripts import telecharger as t

CONTENU = b"contenu fictif d'un fichier de donnees\n"
EMPREINTE = hashlib.sha256(CONTENU).hexdigest()
MAINTENANT = datetime(2026, 11, 15, 12, 0, 0, tzinfo=UTC)


class FauxReseau:
    """Remplace le téléchargement HTTPS : sert un contenu par URL, ou échoue."""

    def __init__(self, contenus: dict[str, bytes]) -> None:
        self.contenus = contenus
        self.appels: list[str] = []

    def __call__(self, url: str, destination: Path) -> str | None:
        self.appels.append(url)
        if url not in self.contenus:
            raise t.ErreurTelechargement(f"{url} : injoignable (simulé)")
        destination.write_bytes(self.contenus[url])
        return "Sun, 15 Nov 2026 10:00:00 GMT"


def registre(tmp_path: Path, corps: str) -> Path:
    chemin = tmp_path / "sources.toml"
    chemin.write_text(corps, encoding="utf-8")
    return chemin


def source(sha256: str = "", miroir: str | None = "https://miroir.example/a.bin") -> t.Source:
    return t.Source(
        id="essai",
        fichier="a.bin",
        url="https://origine.example/a.bin",
        miroir=miroir,
        sha256=sha256,
    )


# --- Lecture du registre -------------------------------------------------------------------


def test_telecharger_lit_les_sources_du_registre_et_ignore_les_paquets(tmp_path: Path) -> None:
    chemin = registre(
        tmp_path,
        """
[[source]]
id = "a"
fichier = "a.bin"
url = "https://origine.example/a.bin"
miroir = "https://miroir.example/a.bin"
sha256 = ""

[[source]]
id = "paquet"
type = "paquet"
fichier = "constellations.npz"
fourni_par = "skyfield"
""",
    )
    sources = t.lire_registre(chemin)
    assert [s.id for s in sources] == ["a"]
    assert sources[0].miroir == "https://miroir.example/a.bin"
    assert sources[0].sha256 == ""


@pytest.mark.parametrize(
    "ligne",
    [
        'url = "http://origine.example/a.bin"',
        'url = "ftp://origine.example/a.bin"',
        'url = "https://origine.example/a.bin"\nmiroir = "http://miroir.example/a.bin"',
    ],
)
def test_telecharger_refuse_une_url_qui_n_est_pas_en_https(tmp_path: Path, ligne: str) -> None:
    chemin = registre(tmp_path, f'[[source]]\nid = "a"\nfichier = "a.bin"\n{ligne}\n')
    with pytest.raises(t.ErreurRegistre):
        t.lire_registre(chemin)


@pytest.mark.parametrize("nom", ["../a.bin", "sous/a.bin", "/tmp/a.bin", ".", ".."])
def test_telecharger_refuse_un_nom_de_fichier_qui_sort_du_dossier(tmp_path: Path, nom: str) -> None:
    chemin = registre(
        tmp_path,
        f'[[source]]\nid = "a"\nfichier = "{nom}"\nurl = "https://origine.example/a.bin"\n',
    )
    with pytest.raises(t.ErreurRegistre):
        t.lire_registre(chemin)


def test_telecharger_refuse_deux_sources_de_meme_identifiant(tmp_path: Path) -> None:
    bloc = '[[source]]\nid = "a"\nfichier = "{f}"\nurl = "https://origine.example/{f}"\n'
    chemin = registre(tmp_path, bloc.format(f="a.bin") + bloc.format(f="b.bin"))
    with pytest.raises(t.ErreurRegistre):
        t.lire_registre(chemin)


# --- Téléchargement ------------------------------------------------------------------------


def test_telecharger_passe_par_un_fichier_temporaire_puis_deplace(tmp_path: Path) -> None:
    reseau = FauxReseau({"https://origine.example/a.bin": CONTENU})
    etat = t.telecharger(source(), tmp_path, reseau)
    assert (tmp_path / "a.bin").read_bytes() == CONTENU
    assert [p.name for p in tmp_path.iterdir()] == ["a.bin"]  # aucun fichier temporaire restant
    assert etat.telecharge is True
    assert etat.url == "https://origine.example/a.bin"
    assert etat.taille == len(CONTENU)


def test_telecharger_sans_empreinte_declaree_rend_l_empreinte_a_figer(tmp_path: Path) -> None:
    reseau = FauxReseau({"https://origine.example/a.bin": CONTENU})
    etat = t.telecharger(source(sha256=""), tmp_path, reseau)
    assert etat.etat == "a_figer"
    assert etat.sha256 == EMPREINTE


def test_telecharger_avec_empreinte_conforme(tmp_path: Path) -> None:
    reseau = FauxReseau({"https://origine.example/a.bin": CONTENU})
    etat = t.telecharger(source(sha256=EMPREINTE), tmp_path, reseau)
    assert etat.etat == "conforme"


def test_telecharger_essaie_le_miroir_si_l_url_echoue(tmp_path: Path) -> None:
    reseau = FauxReseau({"https://miroir.example/a.bin": CONTENU})
    etat = t.telecharger(source(sha256=EMPREINTE), tmp_path, reseau)
    assert reseau.appels == ["https://origine.example/a.bin", "https://miroir.example/a.bin"]
    assert etat.etat == "conforme"
    assert etat.url == "https://miroir.example/a.bin"


def test_telecharger_echec_si_url_et_miroir_echouent(tmp_path: Path) -> None:
    etat = t.telecharger(source(), tmp_path, FauxReseau({}))
    assert etat.etat == "echec"
    assert list(tmp_path.iterdir()) == []


def test_telecharger_empreinte_differente_supprime_le_temporaire_et_echoue(tmp_path: Path) -> None:
    reseau = FauxReseau({"https://origine.example/a.bin": b"autre contenu"})
    etat = t.telecharger(source(sha256=EMPREINTE, miroir=None), tmp_path, reseau)
    assert etat.etat == "different"
    assert list(tmp_path.iterdir()) == []  # ni fichier final, ni temporaire


def test_telecharger_n_ecrase_jamais_un_fichier_conforme(tmp_path: Path) -> None:
    (tmp_path / "a.bin").write_bytes(CONTENU)
    reseau = FauxReseau({"https://origine.example/a.bin": b"version plus recente"})
    etat = t.telecharger(source(sha256=EMPREINTE), tmp_path, reseau)
    assert reseau.appels == []
    assert etat.etat == "conforme"
    assert etat.telecharge is False
    assert (tmp_path / "a.bin").read_bytes() == CONTENU


def test_telecharger_ne_retelecharge_pas_un_fichier_present_a_figer(tmp_path: Path) -> None:
    (tmp_path / "a.bin").write_bytes(CONTENU)
    reseau = FauxReseau({"https://origine.example/a.bin": b"version plus recente"})
    etat = t.telecharger(source(sha256=""), tmp_path, reseau)
    assert reseau.appels == []
    assert etat.etat == "a_figer"
    assert etat.sha256 == EMPREINTE


def test_telecharger_fichier_present_d_empreinte_differente_reste_intact(tmp_path: Path) -> None:
    (tmp_path / "a.bin").write_bytes(b"fichier modifie")
    reseau = FauxReseau({"https://origine.example/a.bin": CONTENU})
    etat = t.telecharger(source(sha256=EMPREINTE), tmp_path, reseau)
    assert reseau.appels == []
    assert etat.etat == "different"
    assert (tmp_path / "a.bin").read_bytes() == b"fichier modifie"


# --- Transport HTTPS (connexion simulée) ---------------------------------------------------


class FausseReponse:
    def __init__(self, statut: int, corps: bytes = b"", entetes: dict[str, str] | None = None):
        self.status = statut
        self._corps = corps
        self._entetes = entetes or {}

    def getheader(self, nom: str) -> str | None:
        return self._entetes.get(nom)

    def read(self, taille: int) -> bytes:
        bloc, self._corps = self._corps[:taille], self._corps[taille:]
        return bloc


class FausseConnexion:
    def __init__(self, hote: str, reponses: dict[tuple[str, str], FausseReponse]) -> None:
        self.hote = hote
        self.reponses = reponses
        self.entetes: dict[str, str] = {}
        self.cible = ""

    def request(self, methode: str, cible: str, headers: dict[str, str]) -> None:
        assert methode == "GET"
        self.cible = cible
        self.entetes = headers

    def getresponse(self) -> FausseReponse:
        return self.reponses[(self.hote, self.cible)]

    def close(self) -> None:
        pass


def brancher(
    monkeypatch: pytest.MonkeyPatch, reponses: dict[tuple[str, str], FausseReponse]
) -> list[FausseConnexion]:
    ouvertes: list[FausseConnexion] = []

    def connexion(hote: str, port: int) -> FausseConnexion:
        assert port == 443
        ouvertes.append(FausseConnexion(hote, reponses))
        return ouvertes[-1]

    monkeypatch.setattr(t, "_connexion", connexion)
    return ouvertes


def test_telecharger_https_ecrit_le_fichier_et_rend_la_date(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    entetes = {"Content-Length": str(len(CONTENU)), "Last-Modified": "date du serveur"}
    ouvertes = brancher(
        monkeypatch, {("origine.example", "/a.bin?v=1"): FausseReponse(200, CONTENU, entetes)}
    )
    date = t.recuperer_https("https://origine.example/a.bin?v=1", tmp_path / "x")
    assert (tmp_path / "x").read_bytes() == CONTENU
    assert date == "date du serveur"
    # Connexion gardée ouverte : un mandataire peut perdre la fin du fichier sur « close ».
    assert "Connection" not in ouvertes[0].entetes


def test_telecharger_https_refuse_un_fichier_tronque(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    entetes = {"Content-Length": str(len(CONTENU) + 100)}
    brancher(monkeypatch, {("origine.example", "/a.bin"): FausseReponse(200, CONTENU, entetes)})
    with pytest.raises(t.ErreurTelechargement, match="incomplet"):
        t.recuperer_https("https://origine.example/a.bin", tmp_path / "x")


def test_telecharger_fichier_tronque_ne_reste_pas_sur_le_disque(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    entetes = {"Content-Length": str(len(CONTENU) + 100)}
    brancher(monkeypatch, {("origine.example", "/a.bin"): FausseReponse(200, CONTENU, entetes)})
    etat = t.telecharger(source(miroir=None), tmp_path)
    assert etat.etat == "echec"
    assert list(tmp_path.iterdir()) == []


def test_telecharger_https_refuse_une_reponse_qui_n_est_pas_200(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    brancher(monkeypatch, {("origine.example", "/a.bin"): FausseReponse(404)})
    with pytest.raises(t.ErreurTelechargement, match="404"):
        t.recuperer_https("https://origine.example/a.bin", tmp_path / "x")


def test_telecharger_https_suit_une_redirection_sur_le_meme_hote(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    brancher(
        monkeypatch,
        {
            ("origine.example", "/a.bin"): FausseReponse(302, entetes={"Location": "/b.bin"}),
            ("origine.example", "/b.bin"): FausseReponse(
                200, CONTENU, {"Content-Length": str(len(CONTENU))}
            ),
        },
    )
    t.recuperer_https("https://origine.example/a.bin", tmp_path / "x")
    assert (tmp_path / "x").read_bytes() == CONTENU


@pytest.mark.parametrize(
    "suite", ["https://ailleurs.example/a.bin", "http://origine.example/a.bin"]
)
def test_telecharger_https_refuse_une_redirection_vers_ailleurs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, suite: str
) -> None:
    brancher(
        monkeypatch,
        {("origine.example", "/a.bin"): FausseReponse(302, entetes={"Location": suite})},
    )
    with pytest.raises(t.ErreurTelechargement, match="redirigé"):
        t.recuperer_https("https://origine.example/a.bin", tmp_path / "x")


# --- Contrôle sans téléchargement ----------------------------------------------------------


def test_telecharger_controler_ne_telecharge_rien(tmp_path: Path) -> None:
    assert t.controler(source(), tmp_path).etat == "absent"
    (tmp_path / "a.bin").write_bytes(CONTENU)
    assert t.controler(source(sha256=""), tmp_path).etat == "a_figer"
    assert t.controler(source(sha256=EMPREINTE), tmp_path).etat == "conforme"
    assert t.controler(source(sha256="0" * 64), tmp_path).etat == "different"


# --- Manifeste -----------------------------------------------------------------------------


def test_telecharger_manifeste_recoit_les_sources_et_garde_le_reste(tmp_path: Path) -> None:
    manifeste = tmp_path / "generes" / "manifest.json"
    manifeste.parent.mkdir()
    manifeste.write_text(json.dumps({"files": {"frontieres.csv": {"sha256": "abc"}}}), "utf-8")
    donnees = tmp_path / "donnees"
    donnees.mkdir()
    reseau = FauxReseau({"https://origine.example/a.bin": CONTENU})
    etat = t.telecharger(source(sha256=EMPREINTE), donnees, reseau)

    t.mettre_a_jour_manifeste([etat], manifeste, MAINTENANT)

    contenu = json.loads(manifeste.read_text("utf-8"))
    assert contenu["files"] == {"frontieres.csv": {"sha256": "abc"}}
    assert contenu["sources"]["essai"] == {
        "file": "a.bin",
        "sha256": EMPREINTE,
        "bytes": len(CONTENU),
        "url": "https://origine.example/a.bin",
        "retrieved_at": "2026-11-15T12:00:00Z",
        "last_modified": "Sun, 15 Nov 2026 10:00:00 GMT",
    }


def test_telecharger_manifeste_inchange_si_l_empreinte_n_a_pas_change(tmp_path: Path) -> None:
    manifeste = tmp_path / "generes" / "manifest.json"
    donnees = tmp_path / "donnees"
    donnees.mkdir()
    reseau = FauxReseau({"https://origine.example/a.bin": CONTENU})
    premier = t.telecharger(source(sha256=EMPREINTE), donnees, reseau)
    t.mettre_a_jour_manifeste([premier], manifeste, MAINTENANT)
    avant = manifeste.read_bytes()

    second = t.telecharger(source(sha256=EMPREINTE), donnees, reseau)  # déjà présent
    plus_tard = datetime(2027, 1, 1, tzinfo=UTC)
    t.mettre_a_jour_manifeste([second], manifeste, plus_tard)

    assert manifeste.read_bytes() == avant


def test_telecharger_manifeste_n_inscrit_que_les_fichiers_presents(tmp_path: Path) -> None:
    manifeste = tmp_path / "generes" / "manifest.json"
    etat = t.telecharger(source(), tmp_path, FauxReseau({}))  # échec
    t.mettre_a_jour_manifeste([etat], manifeste, MAINTENANT)
    assert not manifeste.exists()


# --- Ligne de commande ---------------------------------------------------------------------

REGISTRE_DEUX = """
[[source]]
id = "a"
fichier = "a.bin"
url = "https://origine.example/a.bin"
sha256 = "{sha}"

[[source]]
id = "b"
fichier = "b.bin"
url = "https://origine.example/b.bin"
sha256 = "{sha}"
"""


def lancer(tmp_path: Path, arguments: list[str], reseau: FauxReseau, sha: str = EMPREINTE) -> int:
    return t.main(
        arguments,
        registre=registre(tmp_path, REGISTRE_DEUX.format(sha=sha)),
        dossier=tmp_path / "donnees",
        manifeste=tmp_path / "generes" / "manifest.json",
        recuperer=reseau,
        maintenant=MAINTENANT,
    )


def test_telecharger_main_telecharge_tout_et_rend_zero(tmp_path: Path) -> None:
    reseau = FauxReseau(
        {"https://origine.example/a.bin": CONTENU, "https://origine.example/b.bin": CONTENU}
    )
    assert lancer(tmp_path, [], reseau) == 0
    assert sorted(p.name for p in (tmp_path / "donnees").iterdir()) == ["a.bin", "b.bin"]


def test_telecharger_main_option_source_ne_touche_qu_une_source(tmp_path: Path) -> None:
    reseau = FauxReseau(
        {"https://origine.example/a.bin": CONTENU, "https://origine.example/b.bin": CONTENU}
    )
    assert lancer(tmp_path, ["--source", "b"], reseau) == 0
    assert reseau.appels == ["https://origine.example/b.bin"]


def test_telecharger_main_source_inconnue_est_une_erreur(tmp_path: Path) -> None:
    reseau = FauxReseau({})
    assert lancer(tmp_path, ["--source", "absente"], reseau) == 1
    assert reseau.appels == []


def test_telecharger_main_verifier_ne_telecharge_ni_n_ecrit(tmp_path: Path) -> None:
    reseau = FauxReseau({"https://origine.example/a.bin": CONTENU})
    assert lancer(tmp_path, ["--verifier"], reseau) == 1  # rien n'est présent
    assert reseau.appels == []
    assert not (tmp_path / "donnees").exists()
    assert not (tmp_path / "generes").exists()


def test_telecharger_main_empreinte_a_figer_rend_un(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reseau = FauxReseau(
        {"https://origine.example/a.bin": CONTENU, "https://origine.example/b.bin": CONTENU}
    )
    assert lancer(tmp_path, [], reseau, sha="") == 1
    sortie = capsys.readouterr().out
    assert f'sha256 = "{EMPREINTE}"' in sortie  # ligne proposée pour donnees/sources.toml


def test_telecharger_dossier_par_defaut_et_variable_b13_donnees(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("B13_DONNEES", raising=False)
    assert t.dossier_donnees() == t.RACINE / "donnees" / "telechargees"
    monkeypatch.setenv("B13_DONNEES", str(tmp_path))
    assert t.dossier_donnees() == tmp_path


# --- Constats de la relecture du 15/11/2026 ------------------------------------------------


def test_telecharger_variable_b13_donnees_vide_est_une_erreur(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("B13_DONNEES", "")
    with pytest.raises(t.ErreurRegistre):
        t.dossier_donnees()


@pytest.mark.parametrize("valeur", [EMPREINTE.upper(), " " + EMPREINTE, EMPREINTE[:-1], "abc"])
def test_telecharger_refuse_une_empreinte_mal_formee(tmp_path: Path, valeur: str) -> None:
    """Pas de normalisation : integrite.py compare l'empreinte telle qu'elle est écrite."""
    chemin = registre(
        tmp_path,
        '[[source]]\nid = "a"\nfichier = "a.bin"\nurl = "https://origine.example/a.bin"\n'
        f'sha256 = "{valeur}"\n',
    )
    with pytest.raises(t.ErreurRegistre):
        t.lire_registre(chemin)


def test_telecharger_refuse_deux_sources_pour_le_meme_fichier(tmp_path: Path) -> None:
    bloc = '[[source]]\nid = "{i}"\nfichier = "a.bin"\nurl = "https://origine.example/{i}"\n'
    chemin = registre(tmp_path, bloc.format(i="a") + bloc.format(i="b"))
    with pytest.raises(t.ErreurRegistre):
        t.lire_registre(chemin)


def test_telecharger_lit_le_vrai_registre_du_depot() -> None:
    sources = t.lire_registre()
    assert [s.id for s in sources] == [
        "de440s",
        "iers-finals2000a",
        "geonames-cities15000",
        "geonames-admin1",
    ]
    assert all(s.url.startswith("https://") for s in sources)


def test_telecharger_empreinte_differente_n_essaie_pas_le_miroir(tmp_path: Path) -> None:
    """Contrat : une empreinte déclarée qui diffère arrête tout, miroir compris."""
    reseau = FauxReseau(
        {"https://origine.example/a.bin": b"autre", "https://miroir.example/a.bin": CONTENU}
    )
    etat = t.telecharger(source(sha256=EMPREINTE), tmp_path, reseau)
    assert etat.etat == "different"
    assert reseau.appels == ["https://origine.example/a.bin"]
    assert list(tmp_path.iterdir()) == []


def test_telecharger_n_ecrase_pas_un_fichier_apparu_pendant_le_telechargement(
    tmp_path: Path,
) -> None:
    def reseau(url: str, destination: Path) -> str | None:
        (tmp_path / "a.bin").write_bytes(b"depose par un autre lancement")
        destination.write_bytes(CONTENU)
        return None

    etat = t.telecharger(source(sha256=""), tmp_path, reseau)
    assert (tmp_path / "a.bin").read_bytes() == b"depose par un autre lancement"
    assert etat.telecharge is False
    assert [p.name for p in tmp_path.iterdir()] == ["a.bin"]


def test_telecharger_https_refuse_une_taille_non_annoncee(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    brancher(monkeypatch, {("origine.example", "/a.bin"): FausseReponse(200, CONTENU)})
    with pytest.raises(t.ErreurTelechargement, match="taille non annoncée"):
        t.recuperer_https("https://origine.example/a.bin", tmp_path / "x")


def test_telecharger_https_accepte_un_envoi_par_fragments(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    entetes = {"Transfer-Encoding": "chunked"}
    brancher(monkeypatch, {("origine.example", "/a.bin"): FausseReponse(200, CONTENU, entetes)})
    t.recuperer_https("https://origine.example/a.bin", tmp_path / "x")
    assert (tmp_path / "x").read_bytes() == CONTENU


@pytest.mark.parametrize(
    "suite", ["https://origine.example:8443/a.bin", "https://origine.example:port/a.bin"]
)
def test_telecharger_https_refuse_une_redirection_vers_un_autre_port(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, suite: str
) -> None:
    brancher(
        monkeypatch,
        {("origine.example", "/a.bin"): FausseReponse(302, entetes={"Location": suite})},
    )
    with pytest.raises(t.ErreurTelechargement):
        t.recuperer_https("https://origine.example/a.bin", tmp_path / "x")


def test_telecharger_https_s_arrete_apres_trop_de_redirections(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Location absent : la redirection revient sur la même URL, indéfiniment.
    ouvertes = brancher(monkeypatch, {("origine.example", "/a.bin"): FausseReponse(302)})
    with pytest.raises(t.ErreurTelechargement, match="trop de redirections"):
        t.recuperer_https("https://origine.example/a.bin", tmp_path / "x")
    assert len(ouvertes) == t.REDIRECTIONS_MAX + 1


def test_telecharger_manifeste_ignore_un_fichier_refuse(tmp_path: Path) -> None:
    manifeste = tmp_path / "generes" / "manifest.json"
    reseau = FauxReseau({"https://origine.example/a.bin": b"autre contenu"})
    etat = t.telecharger(source(sha256=EMPREINTE, miroir=None), tmp_path / "donnees", reseau)
    assert etat.etat == "different"
    t.mettre_a_jour_manifeste([etat], manifeste, MAINTENANT)
    assert not manifeste.exists()


def test_telecharger_manifeste_garde_les_trois_cles_de_date_a_null(tmp_path: Path) -> None:
    """Fichier présent sans avoir été téléchargé pendant l'appel (copie restaurée)."""
    manifeste = tmp_path / "generes" / "manifest.json"
    donnees = tmp_path / "donnees"
    donnees.mkdir()
    (donnees / "a.bin").write_bytes(CONTENU)
    etat = t.telecharger(source(sha256=EMPREINTE), donnees, FauxReseau({}))
    t.mettre_a_jour_manifeste([etat], manifeste, MAINTENANT)
    entree = json.loads(manifeste.read_text("utf-8"))["sources"]["essai"]
    assert entree == {
        "file": "a.bin",
        "sha256": EMPREINTE,
        "bytes": len(CONTENU),
        "url": None,
        "retrieved_at": None,
        "last_modified": None,
    }
    assert [p.name for p in manifeste.parent.iterdir()] == ["manifest.json"]  # pas de temporaire


def test_telecharger_main_manifeste_illisible_rend_un_sans_trace(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "generes").mkdir()
    (tmp_path / "generes" / "manifest.json").write_text("{ pas du json", "utf-8")
    reseau = FauxReseau(
        {"https://origine.example/a.bin": CONTENU, "https://origine.example/b.bin": CONTENU}
    )
    assert lancer(tmp_path, [], reseau) == 1
    assert "illisible" in capsys.readouterr().err
    assert (tmp_path / "generes" / "manifest.json").read_text("utf-8") == "{ pas du json"


def test_telecharger_main_registre_invalide_rend_un(tmp_path: Path) -> None:
    code = t.main(
        [],
        registre=registre(tmp_path, '[[source]]\nfichier = "a.bin"\n'),
        dossier=tmp_path / "donnees",
        manifeste=tmp_path / "generes" / "manifest.json",
        recuperer=FauxReseau({}),
        maintenant=MAINTENANT,
    )
    assert code == 1
    assert not (tmp_path / "donnees").exists()


# --- Connexion : certificats et mandataire -------------------------------------------------


def test_telecharger_tls_verifie_le_certificat_et_le_nom_d_hote() -> None:
    import ssl

    contexte = t.contexte_tls()
    assert contexte.verify_mode == ssl.CERT_REQUIRED
    assert contexte.check_hostname is True


def test_telecharger_connexion_directe_sans_mandataire(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(t.urllib.request, "getproxies", dict)
    connexion = t._connexion("origine.example", 443)
    assert (connexion.host, connexion.port) == ("origine.example", 443)
    assert connexion._tunnel_host is None


def test_telecharger_connexion_par_le_mandataire_avec_ses_identifiants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import base64

    monkeypatch.setattr(
        t.urllib.request, "getproxies", lambda: {"https": "http://nom:mot%20secret@localhost:3128"}
    )
    monkeypatch.setattr(t.urllib.request, "proxy_bypass", lambda hote: False)
    connexion = t._connexion("origine.example", 443)
    assert (connexion.host, connexion.port) == ("localhost", 3128)
    assert (connexion._tunnel_host, connexion._tunnel_port) == ("origine.example", 443)
    attendu = "Basic " + base64.b64encode(b"nom:mot secret").decode()
    assert connexion._tunnel_headers["Proxy-Authorization"] == attendu


def test_telecharger_connexion_ignore_le_mandataire_pour_un_hote_exclu(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(t.urllib.request, "getproxies", lambda: {"https": "http://localhost:3128"})
    monkeypatch.setattr(t.urllib.request, "proxy_bypass", lambda hote: True)
    connexion = t._connexion("origine.example", 443)
    assert connexion.host == "origine.example"


def test_telecharger_connexion_refuse_un_mandataire_qui_n_est_pas_en_http(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(t.urllib.request, "getproxies", lambda: {"https": "socks5://localhost:1"})
    monkeypatch.setattr(t.urllib.request, "proxy_bypass", lambda hote: False)
    with pytest.raises(t.ErreurTelechargement, match="mandataire"):
        t._connexion("origine.example", 443)
