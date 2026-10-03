"""Dönemler arası görev havuzu: önceki dönemlerin görevleri ve sayaçlar.
"""

from __future__ import annotations

from datetime import date

from cekirdek.kurallar import ucretlendirilemeyen_gorevler
from cekirdek.metin import siralama_anahtari
from cekirdek.modeller import GorevRolu, Personel, PlanTuru
from cekirdek.takvim import pencere_adi
from ..veritabani import Veritabani

from .plan_kayitlari import etkin_planlar
from .personel import personelleri_getir


# ============================================ dönemler arası görev havuzu

def _gorev_kayitlari(vt: Veritabani, plan_kimlikleri: list[int]
                     ) -> list[tuple[int, GorevRolu, date, str]]:
    """Verilen planların görevleri: (personel, rol, tarih, dönem kodu)."""
    if not plan_kimlikleri:
        return []
    yer_tutucu = ",".join("?" * len(plan_kimlikleri))
    with vt.baglan() as b:
        return [(r[0], GorevRolu(r[1]), date.fromisoformat(r[2]), r[3]) for r in b.execute(f"""
            SELECT g.personel_id, g.rol, o.tarih, pl.pencere_kodu
            FROM v_gorevlendirme g
            JOIN v_oturum o ON o.id = g.oturum_id
            JOIN v_plan pl ON pl.id = o.plan_id
            WHERE pl.id IN ({yer_tutucu}) ORDER BY o.tarih, g.id""", plan_kimlikleri)]


def onceki_gorev_kayitlari(vt: Veritabani, haric: tuple[str, str] | None = None
                           ) -> tuple[tuple[int, GorevRolu, date], ...]:
    """Aynı öğretim yılının geçerli planlarındaki görevler (personel, rol, tarih).

    Bir öğretim yılında üç sınav dönemi vardır. P2 planlanırken P1'de görev
    almış öğretmenin yükü hesaba katılmazsa aynı kişiler üst üste
    görevlendirilir; yıllık ücret sınırı da (Karar md.12/2-a) yıla bakar.
    `haric` (dönem, tür) yeniden planlanan planı dışarıda bırakır: eski
    sürüm aynı dönemin eski planını "önceki dönem" sayıyor, yeni plan
    eskisinde çok görev alan öğretmeni gereksiz yere geri plana itiyordu.
    Her dönemden yalnız geçerli plan sayılır (bkz. `etkin_planlar`).
    """
    planlar = [kimlik for anahtar, kimlik in etkin_planlar(vt).items() if anahtar != haric]
    return tuple((kimlik, rol, tarih) for kimlik, rol, tarih, _ in _gorev_kayitlari(vt, planlar))


def _sayaclara_cevir(gorevler) -> dict[int, tuple[int, int]]:
    sayac: dict[int, list[int]] = {}
    for kimlik, rol, _ in gorevler:
        kayit = sayac.setdefault(kimlik, [0, 0])
        kayit[0 if rol is GorevRolu.KOMISYON_UYESI else 1] += 1
    return {kimlik: (k, g) for kimlik, (k, g) in sayac.items()}


def onceki_gorev_sayaclari(vt: Veritabani, haric: tuple[str, str] | None = None
                           ) -> dict[int, tuple[int, int]]:
    """Kişi başına (komisyon, gözcülük) sayacı; bkz. `onceki_gorev_kayitlari`."""
    return _sayaclara_cevir(onceki_gorev_kayitlari(vt, haric))


def gorev_havuzu_ozeti(vt: Veritabani) -> list[dict]:
    """Öğretim yılı boyunca kişi başına dönem dönem görev dağılımı.

    Her dönemden yalnız geçerli plan sayılır; tek ders sınavının (OKY md.58/6)
    görevleri bağlı olduğu dönemin sütununa girer. Ücret sınırı aşımı görev
    tarihlerine göre hesaplanır (Karar md.12/2-a ve toplu sözleşme askısı).
    """
    kisiler: dict[int, dict] = {}
    personel = {p.kimlik: p for p in personelleri_getir(vt, yalniz_aktif=False)}
    for kimlik, rol, tarih, pencere in _gorev_kayitlari(vt, list(etkin_planlar(vt).values())):
        kisi = personel.get(kimlik)
        kayit = kisiler.setdefault(kimlik, {
            "kimlik": kimlik, "ad": kisi.ad if kisi else f"#{kimlik}",
            "brans": kisi.brans if kisi else "", "unvan": kisi.unvan if kisi else "",
            "pencereler": {}, "komisyon": 0, "gozcu": 0, "_gorevler": []})
        komisyon, gozcu = kayit["pencereler"].get(pencere, (0, 0))
        if rol is GorevRolu.KOMISYON_UYESI:
            kayit["pencereler"][pencere] = (komisyon + 1, gozcu)
            kayit["komisyon"] += 1
        else:
            kayit["pencereler"][pencere] = (komisyon, gozcu + 1)
            kayit["gozcu"] += 1
        kayit["_gorevler"].append((rol, tarih))
    for kayit in kisiler.values():
        kayit["toplam"] = kayit["komisyon"] + kayit["gozcu"]
        asan = ucretlendirilemeyen_gorevler(kayit.pop("_gorevler"))
        kayit["ucretsiz_komisyon"] = asan[GorevRolu.KOMISYON_UYESI]
        kayit["ucretsiz_gozcu"] = asan[GorevRolu.GOZCU]
        kayit["asildi_mi"] = any(asan.values())
        kayit["ucretlendirilebilir"] = not Personel(0, "", "", kayit["unvan"]).yonetici_mi
    return sorted(kisiler.values(), key=lambda x: siralama_anahtari(x["ad"]))


def taslak_pencereler(vt: Veritabani) -> list[str]:
    """Bu öğretim yılında geçerli planı henüz kesinleşmemiş dönemlerin adları.

    Görev sayacı raporu kesinleşmemiş plandan da üretilir; sayıların
    değişebileceğini belgeye yazabilmek için hangi dönemlerin taslak olduğu
    bilinmelidir.
    """
    etkin = etkin_planlar(vt)
    if not etkin:
        return []
    with vt.baglan() as b:
        taslaklar = {r[0] for r in b.execute(
            f"SELECT id FROM v_plan WHERE durum='taslak' AND id IN "
            f"({','.join('?' * len(etkin))})", list(etkin.values()))}
    adlar = []
    for (kod, tur), kimlik in sorted(etkin.items()):
        if kimlik in taslaklar:
            adlar.append(pencere_adi(kod) + (" (tek ders)" if tur == PlanTuru.TEK_DERS.value
                                             else ""))
    return adlar
