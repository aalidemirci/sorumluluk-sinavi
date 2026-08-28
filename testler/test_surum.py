"""Sürümün tek kaynakta kalmasını koruyan testler.

Sürüm yalnızca ``cekirdek/surum.py`` içinde yazılır. pyproject ve Inno
Setup betiği oradan okur; Inno Setup bunu Python olarak değil **metin
olarak** ayrıştırdığı için satırın biçimi de sözleşmenin parçasıdır.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from cekirdek.surum import SURUM

KOK = Path(__file__).resolve().parents[1]


def test_surum_bicimi_semverdir() -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+", SURUM), SURUM


def test_inno_setupun_ayristirdigi_satir_bicimi_korunur() -> None:
    """``yapim/sorumluluk_sinavi.iss`` bu satırı ``SURUM = "`` ile arar."""
    satirlar = (KOK / "cekirdek" / "surum.py").read_text(encoding="utf-8").splitlines()
    eslesen = [s for s in satirlar if s.startswith('SURUM = "')]
    assert eslesen == [f'SURUM = "{SURUM}"'], eslesen


def test_pyproject_surumu_elle_yazmaz() -> None:
    yapilandirma = tomllib.loads((KOK / "pyproject.toml").read_text(encoding="utf-8"))
    assert "version" not in yapilandirma["project"]
    assert "version" in yapilandirma["project"]["dynamic"]
    dinamik = yapilandirma["tool"]["setuptools"]["dynamic"]
    assert dinamik["version"] == {"attr": "cekirdek.surum.SURUM"}


def test_inno_setup_betigi_surumu_elle_yazmaz() -> None:
    betik = (KOK / "yapim" / "sorumluluk_sinavi.iss").read_text(encoding="utf-8")
    assert SURUM not in betik, "sürüm .iss içine elle yazılmış"
    assert 'Pos(\'SURUM = "\', satir)' in betik


def test_arayuz_surumu_cekirdekten_alir() -> None:
    from arayuz import uygulama
    assert uygulama.SURUM is SURUM


def test_pyinstaller_betigi_surumu_elle_yazmaz() -> None:
    betik = (KOK / "SorumlulukSinavi.spec").read_text(encoding="utf-8")
    assert SURUM not in betik, "sürüm .spec içine elle yazılmış"
    assert "from cekirdek.surum import SURUM" in betik


def test_deb_betigi_surumu_elle_yazmaz() -> None:
    """Pardus paketinin adı ve control dosyası da aynı kaynaktan gelir."""
    betik = (KOK / "yapim" / "deb_paketi.py").read_text(encoding="utf-8")
    assert SURUM not in betik, "sürüm deb_paketi.py içine elle yazılmış"
    assert "from cekirdek.surum import SURUM" in betik


def test_exe_metinleri_kurulum_betigiyle_ayni() -> None:
    """Uygulama adı ve geliştirici iki betikte de geçer; ayrışmasınlar."""
    spec = (KOK / "SorumlulukSinavi.spec").read_text(encoding="utf-8")
    iss = (KOK / "yapim" / "sorumluluk_sinavi.iss").read_text(encoding="utf-8")
    for spec_adi, iss_adi in (("AD", "Ad"), ("GELISTIRICI", "Gelistirici")):
        spec_deger = re.search(rf'^{spec_adi} = "(.+)"$', spec, re.M)
        iss_deger = re.search(rf'^#define {iss_adi}\s+"(.+)"$', iss, re.M)
        assert spec_deger and iss_deger, (spec_adi, iss_adi)
        assert spec_deger.group(1) == iss_deger.group(1), (
            f"{spec_adi}: spec={spec_deger.group(1)!r} iss={iss_deger.group(1)!r}")
