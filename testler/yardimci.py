"""Testler için uydurma veri üreticileri.

Gerçek öğrenci, veli veya personel verisi teste girmez (KVKK). Buradaki tüm
ad, numara ve branşlar uydurmadır.
"""

from __future__ import annotations

import csv
from pathlib import Path


SORUMLULUK_BASLIK = ["", "Öğrenci No", "Adı Soyadı", "", "", "", "", "", "Sınıfı", "Dersi"]


def sorumluluk_csv_yaz(hedef: Path, subeler: dict[str, list[tuple[str, str, list[tuple[int, str]]]]]) -> Path:
    """OOK12001R010 düzeninde uydurma bir rapor yazar.

    `subeler`: {"9/A": [(okul_no, ad_soyad, [(duzey, ders), ...]), ...]}
    """
    satirlar: list[list[object]] = []
    for sube, ogrenciler in subeler.items():
        duzey, sube_adi = sube.split("/", 1)
        satirlar.append([f"Uydurma Anadolu Lisesi - {duzey}. Sınıf / {sube_adi} Şubesi"] + [""] * 9)
        satirlar.append(list(SORUMLULUK_BASLIK))
        for okul_no, ad_soyad, dersler in ogrenciler:
            for sira, (ders_duzeyi, ders_adi) in enumerate(dersler):
                satir = [""] * 10
                if sira == 0:
                    satir[1], satir[2] = okul_no, ad_soyad
                satir[8], satir[9] = str(ders_duzeyi), ders_adi
                satirlar.append(satir)
    hedef.parent.mkdir(parents=True, exist_ok=True)
    with hedef.open("w", encoding="utf-8-sig", newline="") as akim:
        csv.writer(akim).writerows(satirlar)
    return hedef


def ornek_sorumluluk_csv(hedef: Path) -> Path:
    return sorumluluk_csv_yaz(hedef, {
        "9/A": [
            ("101", "Uydurma Öğrenci Bir", [(9, "MATEMATİK"), (9, "FİZİK")]),
            ("102", "Uydurma Öğrenci İki", [(9, "MATEMATİK")]),
        ],
        "10/B": [
            ("201", "Uydurma Öğrenci Üç", [(10, "MATEMATİK"), (9, "KİMYA"),
                                           (10, "TÜRK DİLİ VE EDEBİYATI")]),
        ],
    })


def personel_satirlari(kisiler: list[tuple[str, str, str, str]]) -> list[list[object]]:
    """OOK01001R1 düzeninde satır listesi üretir: (ad, görev, kadro, branş)."""
    satirlar: list[list[object]] = [
        ["T.C. Millî Eğitim Bakanlığı"],
        ["Kurum Personel Listesi"],
        ["Adı Soyadı", "Görevi", "Kadro Durumu", "Branşı"],
    ]
    satirlar.extend([list(kisi) for kisi in kisiler])
    satirlar.append(["Toplam Personel Sayısı", str(len(kisiler)), "", ""])
    return satirlar


# Sınav görevlendirmesi her oturumda 2 komisyon üyesi (en az biri alan) ve
# salon başına 1 gözcü ister; kadro bunu karşılayacak genişlikte tutulur.
ORNEK_PERSONEL = [
    ("Uydurma Müdür", "Müdür", "Kadrolu", "Coğrafya"),
    ("Uydurma Yardımcı", "Müdür Yardımcısı", "Kadrolu", "Tarih"),
    ("Uydurma Matematikçi", "Öğretmen", "Kadrolu", "Matematik"),
    ("Uydurma Matematikçi İki", "Öğretmen", "Kadrolu", "Matematik"),
    ("Uydurma Fizikçi", "Öğretmen", "Kadrolu", "Fizik"),
    ("Uydurma Fizikçi İki", "Öğretmen", "Kadrolu", "Fizik"),
    ("Uydurma İngilizceci", "Öğretmen", "Kadrolu", "İngilizce"),
    ("Uydurma İngilizceci İki", "Öğretmen", "Kadrolu", "İngilizce"),
    ("Uydurma Edebiyatçı", "Öğretmen", "Sözleşmeli", "Türk Dili ve Edebiyatı"),
    ("Uydurma Tarihçi", "Öğretmen", "Kadrolu", "Tarih"),
    ("Uydurma Rehber", "Öğretmen", "Kadrolu", "Rehberlik"),
]


# ---------------------------------------------------------------- plan kurma

from datetime import date, time  # noqa: E402

from cekirdek.modeller import (  # noqa: E402
    Gorevlendirme, GorevRolu, Oturum, OturumTuru, Personel, Plan,
    PlanParametreleri, Salon,
)
from cekirdek.kurallar import DogrulamaBaglami  # noqa: E402


# P1 penceresi: 14.09.2026 pazartesi ile başlayan iki hafta.
PENCERE = (date(2026, 9, 14), date(2026, 9, 27))

PERSONEL = {
    1: Personel(1, "Uydurma Matematikçi", "Matematik", "Öğretmen"),
    2: Personel(2, "Uydurma Matematikçi İki", "Matematik", "Öğretmen"),
    3: Personel(3, "Uydurma Fizikçi", "Fizik", "Öğretmen"),
    4: Personel(4, "Uydurma Kimyacı", "Kimya", "Öğretmen"),
    5: Personel(5, "Uydurma Edebiyatçı", "Türk Dili ve Edebiyatı", "Öğretmen"),
    6: Personel(6, "Uydurma Yardımcı", "Tarih", "Müdür Yardımcısı"),
    7: Personel(7, "Uydurma Müdür", "Coğrafya", "Müdür"),
    8: Personel(8, "Uydurma Rehber", "Rehberlik", "Öğretmen"),
}

SALONLAR = {
    1: Salon(1, "A-101", 30),
    2: Salon(2, "A-102", 30),
    3: Salon(3, "A-103", 20),
}


def parametreler(**degisiklikler) -> PlanParametreleri:
    varsayilan = dict(pencere_kodu="P1", hafta_sonu_kullan=False,
                      ogrenci_gunluk_sinav_siniri=2)
    varsayilan.update(degisiklikler)
    return PlanParametreleri(**varsayilan)


def oturum(anahtar: str, ders: str, ogrenciler: list[str], gun: int = 14,
           saat: tuple[int, int] = (9, 0), *, tur: OturumTuru = OturumTuru.YAZILI,
           duzeyler: tuple[int, ...] = (9,), brans: str = "Matematik",
           salonlar: tuple[int, ...] = (1,), birim: str = "",
           sure: int = 40, hafta_sonu_gerekcesi: str = "") -> Oturum:
    return Oturum(
        anahtar=anahtar, ders_adi=ders, duzeyler=duzeyler,
        ogrenci_anahtarlari=tuple(ogrenciler), oturum_turu=tur,
        tarih=date(2026, 9, gun), saat=time(*saat), sure_dakika=sure,
        salon_kimlikleri=salonlar, alan_bransi=brans, birim_anahtari=birim,
        hafta_sonu_gerekcesi=hafta_sonu_gerekcesi,
    )


def gorevler(oturum_anahtari: str, komisyon: tuple[int, ...] = (1, 2),
             gozcu: tuple[int, ...] = (3,), gerekce: str = "") -> list[Gorevlendirme]:
    return (
        [Gorevlendirme(oturum_anahtari, k, GorevRolu.KOMISYON_UYESI, gerekce) for k in komisyon]
        + [Gorevlendirme(oturum_anahtari, g, GorevRolu.GOZCU) for g in gozcu]
    )


def plan(oturumlar: list[Oturum], gorevlendirmeler: list[Gorevlendirme] | None = None,
         **param) -> Plan:
    return Plan(parametreler(**param), list(oturumlar), list(gorevlendirmeler or []))


def baglam(**degisiklikler) -> DogrulamaBaglami:
    varsayilan = dict(pencere=PENCERE, personel=PERSONEL, ogretim_yili="2027-2028")
    varsayilan.update(degisiklikler)
    return DogrulamaBaglami(**varsayilan)


def kimlikler(ihlaller) -> list[str]:
    return [i.kural_kimligi for i in ihlaller]
