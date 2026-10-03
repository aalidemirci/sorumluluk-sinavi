"""Kayıtlı planları bulan küçük sorgular.

Başvuru, görev havuzu, personel ve tek ders bölümleri plan modülünün
yalnız bu üç sorgusuna ihtiyaç duyar; ayrı durdukları için o modüller
plan üretimini içe aktarmaz ve modüller arasında döngü oluşmaz.
"""

from __future__ import annotations

from cekirdek.modeller import PlanTuru
from ..veritabani import Veritabani

from .ortak import ogretim_yili


def kesin_plan(vt: Veritabani, pencere_kodu: str,
               tur: PlanTuru | str = PlanTuru.OLAGAN) -> tuple[int, str] | None:
    """Bu öğretim yılında aynı dönem ve türde kesinleşmiş plan: (kimlik, onay no)."""
    with vt.baglan() as b:
        satir = b.execute(
            "SELECT id, COALESCE(mudur_onay_no,'') FROM v_plan WHERE pencere_kodu=? AND tur=?"
            " AND ogretim_yili=? AND durum='kesin' ORDER BY id DESC LIMIT 1",
            (pencere_kodu, PlanTuru(tur).value, ogretim_yili(vt))).fetchone()
    return (int(satir[0]), satir[1]) if satir else None


def etkin_planlar(vt: Veritabani, ogretim_yili_: str | None = None) -> dict[tuple[str, str], int]:
    """(dönem kodu, plan türü) -> o öğretim yılının geçerli planı.

    Geçerli plan, kesinleşmiş plan varsa odur; yoksa en son kaydedilen
    taslaktır. Ekranlar, evrak ve görev sayaçları hep bu planı esas alır;
    eski sürüm yalnız en büyük kimliğe bakıyordu ve yıl ayırmıyordu.
    """
    yil = ogretim_yili(vt) if ogretim_yili_ is None else ogretim_yili_
    with vt.baglan() as b:
        satirlar = b.execute(
            "SELECT id,pencere_kodu,tur FROM v_plan WHERE ogretim_yili=?"
            " ORDER BY (durum='kesin') DESC, id DESC", (yil,)).fetchall()
    sonuc: dict[tuple[str, str], int] = {}
    for kimlik, kod, tur in satirlar:
        sonuc.setdefault((kod, tur), int(kimlik))
    return sonuc


def son_plani_getir(vt: Veritabani, pencere_kodu: str,
                    tur: PlanTuru | str = PlanTuru.OLAGAN) -> int | None:
    """Bu öğretim yılında dönemin geçerli planı (bkz. `etkin_planlar`)."""
    return etkin_planlar(vt).get((pencere_kodu, PlanTuru(tur).value))
