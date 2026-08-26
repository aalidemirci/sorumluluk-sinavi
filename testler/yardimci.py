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


ORNEK_PERSONEL = [
    ("Uydurma Müdür", "Müdür", "Kadrolu", "Coğrafya"),
    ("Uydurma Yardımcı", "Müdür Yardımcısı", "Kadrolu", "Tarih"),
    ("Uydurma Matematikçi", "Öğretmen", "Kadrolu", "Matematik"),
    ("Uydurma Fizikçi", "Öğretmen", "Kadrolu", "Fizik"),
    ("Uydurma Edebiyatçı", "Öğretmen", "Sözleşmeli", "Türk Dili ve Edebiyatı"),
    ("Uydurma Rehber", "Öğretmen", "Kadrolu", "Rehberlik"),
]
