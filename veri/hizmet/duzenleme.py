"""Planın elle düzenlenmesi: oturum taşıma, anlık görüntü ve görevli
değişikliği.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time

from cekirdek.kurallar import SALON_OGRENCI_UST_SINIRI, musait_degil_mi, oturumlar_cakisir_mi
from cekirdek.metin import esitle, siralama_anahtari
from cekirdek.modeller import (
    Gorevlendirme, GorevRolu, Ihlal, Oturum, OturumTuru, Plan, PlanTuru, Salon,
)
from ..veritabani import Veritabani, simdi

from .ortak import HizmetHatasi, salonlari_getir
from .personel import musaitsizlikleri_getir, personelleri_getir
from .gorev import _sayaclara_cevir, onceki_gorev_kayitlari
from .plan import _yonetici_mi, plan_yukle, plani_dogrula


# ------------------------------------------------------- elle düzenleme

@dataclass
class TasimaSonucu:
    """Sürükle-bırak denemesinin sonucu."""

    uygulandi: bool
    ogrenci_engelleri: list[Ihlal] = field(default_factory=list)
    ogretmen_engelleri: list[Ihlal] = field(default_factory=list)
    salon_engelleri: list[Ihlal] = field(default_factory=list)
    diger_engeller: list[Ihlal] = field(default_factory=list)
    uyarilar: list[Ihlal] = field(default_factory=list)
    # Hedef saatte salonu dolu olduğu için boş salona geçirilen oturum var mı.
    salon_degisti: bool = False

    @property
    def engeller(self) -> list[Ihlal]:
        return (self.ogrenci_engelleri + self.ogretmen_engelleri
                + self.salon_engelleri + self.diger_engeller)

    def mesaj(self) -> str:
        bolumler = []
        for baslik, liste in (("Öğrenci çakışması", self.ogrenci_engelleri),
                              ("Öğretmen çakışması", self.ogretmen_engelleri),
                              ("Salon çakışması", self.salon_engelleri),
                              ("Kural ihlali", self.diger_engeller)):
            if liste:
                bolumler.append(baslik + ":\n" + "\n".join(f"  • {i.aciklama}" for i in liste))
        return "\n\n".join(bolumler)


def _engel_turu(ihlal: Ihlal) -> str:
    """İhlali kullanıcıya ayrı ayrı gösterebilmek için sınıflandırır."""
    metin = ihlal.aciklama
    if (ihlal.kural_kimligi == "SP-09" or "aynı anda iki sınavda görevli" in metin
            or "sınav görevi verilemez" in metin):
        return "ogretmen"
    if "salonu" in metin and "ayrılmış" in metin:
        return "salon"
    if "aynı anda iki sınavda" in metin or ihlal.kural_kimligi == "SP-11":
        return "ogrenci"
    return "diger"


def _yeni_engellere_bak(vt: Veritabani, plan: Plan, kisisel_sinirlar: dict[str, int] | None,
                        onceki: set[tuple[str, str]], geri_al) -> TasimaSonucu:
    """Değişiklik yeni bir engel doğurduysa geri alır ve engelleri gruplar."""
    sonrasi = plani_dogrula(vt, plan, kisisel_sinirlar)
    yeni_engeller = [i for i in sonrasi
                     if i.engel_mi and (i.kural_kimligi, i.etkilenen_kayit) not in onceki]
    if yeni_engeller:
        geri_al()
        gruplar: dict[str, list[Ihlal]] = {"ogrenci": [], "ogretmen": [], "salon": [], "diger": []}
        for ihlal in yeni_engeller:
            gruplar[_engel_turu(ihlal)].append(ihlal)
        return TasimaSonucu(False, gruplar["ogrenci"], gruplar["ogretmen"],
                            gruplar["salon"], gruplar["diger"])
    return TasimaSonucu(True, uyarilar=[i for i in sonrasi if not i.engel_mi])


def _engel_imzalari(vt: Veritabani, plan: Plan,
                    kisisel_sinirlar: dict[str, int] | None) -> set[tuple[str, str]]:
    return {(i.kural_kimligi, i.etkilenen_kayit)
            for i in plani_dogrula(vt, plan, kisisel_sinirlar) if i.engel_mi}


# Elle hafta sonuna alınan oturum için önerilen gerekçe; kullanıcı değiştirebilir.
ELLE_HAFTA_SONU_GEREKCESI = ("Hafta içi saatler yetmediği için OKY md.58/2-ç uyarınca "
                             "hafta sonuna alındı.")


def _tasinacaklar(plan: Plan, oturum: Oturum) -> list[Oturum]:
    """Yazılı taşınınca iki aşamalı dersin uygulaması da onunla gider."""
    esler = [o for o in plan.oturumlar
             if oturum.birim_anahtari and o.birim_anahtari == oturum.birim_anahtari
             and o is not oturum]
    return [oturum] + (esler if oturum.oturum_turu is OturumTuru.YAZILI else [])


def _bos_salona_gec(plan: Plan, oturum: Oturum, salonlar: dict[int, Salon]) -> bool:
    """Hedef saatte salonu dolu olan oturumu aynı sayıda boş salona geçirir.

    Taşınan oturum salonunu yanında götürüyordu; hedef saatte o salon doluysa
    başka salon boş olsa da taşıma SP-03 ile geri alınıyordu. Gerçek verinin
    kopyasında aynı saatte başka güne 330 taşımanın 76'sı yalnız bu yüzden
    reddediliyordu ve hepsi boş salona geçerek olurdu (04.10.2026). Salon sayısı
    değişmez (SP-03: salon başına bir gözcü); boş salon ya da kapasite yetmezse
    salona dokunulmaz, doğrulayıcı engeli eskisi gibi bildirir. Seçim
    planlayıcının sırasıyladır: önce büyük salon, eşitse küçük kimlik.
    """
    dolu = {k for o in plan.oturumlar if o is not oturum and oturumlar_cakisir_mi(o, oturum)
            for k in o.salon_kimlikleri}
    if not dolu & set(oturum.salon_kimlikleri):
        return False
    kalan = [k for k in oturum.salon_kimlikleri if k not in dolu]
    adaylar = sorted((s for s in salonlar.values()
                      if s.kimlik not in dolu and s.kimlik not in kalan),
                     key=lambda s: (-s.kapasite, s.kimlik))
    gereken = len(oturum.salon_kimlikleri) - len(kalan)
    if len(adaylar) < gereken:
        return False
    yeni = kalan + [s.kimlik for s in adaylar[:gereken]]
    kapasite = sum(min(salonlar[k].kapasite, SALON_OGRENCI_UST_SINIRI)
                   for k in yeni if k in salonlar)
    if kapasite < len(oturum.ogrenci_anahtarlari):
        return False
    oturum.salon_kimlikleri = tuple(yeni)
    return True


def hafta_sonu_gerekcesi_gerekir_mi(plan: Plan, anahtar: str, yeni_tarih: date) -> bool:
    """Taşıma bir oturumu gerekçesiz olarak hafta sonuna götürecek mi (SP-05)?

    Planlayıcı hafta sonuna koyduğu oturumun gerekçesini kendisi yazar. Elle
    taşımada gerekçe girilecek yer yoktu; SP-05 hafta sonuna her taşımayı geri
    alıyordu (04.10.2026, gerçek verinin kopyasıyla deneme). Arayüz bu durumda
    gerekçe sorar.
    """
    oturum = plan.oturum_bul(anahtar)
    if oturum is None:
        return False
    fark = yeni_tarih - oturum.tarih
    return any((o.tarih + fark).weekday() >= 5 and not o.hafta_sonu_gerekcesi.strip()
               for o in _tasinacaklar(plan, oturum))


def oturum_tasi(vt: Veritabani, plan: Plan, anahtar: str, yeni_tarih: date, yeni_saat: time,
                kisisel_sinirlar: dict[str, int] | None = None,
                hafta_sonu_gerekcesi: str = "") -> TasimaSonucu:
    """Oturumu yeni gün/saate taşır; yeni engel doğuruyorsa geri alır.

    İki aşamalı derste (OKY md.58/2-e) yazılı taşınınca uygulama da aynı gün
    ve saat farkıyla birlikte taşınır. Uygulama oturumu ise tek başına
    taşınabilir: hüküm "yazılı sınav ve uygulama sınavları sorumluluk
    sınavları dönemi içinde farklı günlerde de yapılabilir" der. Öğrenci,
    öğretmen ve salon çakışmaları ayrı ayrı raporlanır; uyarı düzeyindeki
    ihlaller taşımayı engellemez.

    Hafta sonuna giden ve gerekçesi olmayan oturuma `hafta_sonu_gerekcesi`
    yazılır (OKY md.58/2-ç, SP-05). Hedef saatte salonu dolu olan oturum aynı
    sayıda boş salona geçirilir (bkz. `_bos_salona_gec`). Taşıma geri alınırsa
    gerekçe ve salon da eski hâline döner.
    """
    oturum = plan.oturum_bul(anahtar)
    if oturum is None:
        raise HizmetHatasi("Taşınacak oturum bulunamadı.")
    if oturum.kilitli_mi:
        raise HizmetHatasi("Kesinleşmiş veya kilitli oturum taşınamaz.")

    onceki = _engel_imzalari(vt, plan, kisisel_sinirlar)
    tasinacaklar = _tasinacaklar(plan, oturum)
    eski_durum = [(o, o.tarih, o.saat, o.hafta_sonu_gerekcesi, o.salon_kimlikleri)
                  for o in tasinacaklar]
    saatler = list(plan.parametreler.slot_saatleri)
    gun_farki = yeni_tarih - oturum.tarih
    for es in tasinacaklar[1:]:
        # Yazılı ile uygulamanın saat farkı korunur; yeni gün o saati
        # taşımıyorsa uygulama kendi saatinde kalır.
        if es.saat in saatler and oturum.saat in saatler and yeni_saat in saatler:
            hedef = saatler.index(yeni_saat) + saatler.index(es.saat) - saatler.index(oturum.saat)
            if 0 <= hedef < len(saatler):
                es.saat = saatler[hedef]
        es.tarih = es.tarih + gun_farki
    oturum.tarih, oturum.saat = yeni_tarih, yeni_saat
    gerekce = hafta_sonu_gerekcesi.strip()
    if gerekce:
        for o in tasinacaklar:
            if o.tarih.weekday() >= 5 and not o.hafta_sonu_gerekcesi.strip():
                o.hafta_sonu_gerekcesi = gerekce
    salonlar = {s.kimlik: s for s in salonlari_getir(vt)}
    salon_degisti = False
    for o in tasinacaklar:
        salon_degisti = _bos_salona_gec(plan, o, salonlar) or salon_degisti

    def geri_al() -> None:
        for nesne, tarih, saat, eski_gerekce, eski_salonlar in eski_durum:
            nesne.tarih, nesne.saat = tarih, saat
            nesne.hafta_sonu_gerekcesi, nesne.salon_kimlikleri = eski_gerekce, eski_salonlar

    sonuc = _yeni_engellere_bak(vt, plan, kisisel_sinirlar, onceki, geri_al)
    sonuc.salon_degisti = sonuc.uygulandi and salon_degisti
    return sonuc


def plan_anlik_goruntusu(plan: Plan) -> tuple[tuple, tuple]:
    """Geri al yığını için planın değişebilen durumunu kopyalar.

    Oturumların yeri, hafta sonu gerekçesi ve görevlendirmeler birlikte
    alınır; görevli değişikliği de, hafta sonuna taşımayla yazılan gerekçe de
    geri alınabilmelidir.
    """
    return (tuple((o.anahtar, o.tarih, o.saat, o.salon_kimlikleri, o.hafta_sonu_gerekcesi)
                  for o in plan.oturumlar),
            tuple(plan.gorevlendirmeler))


def plani_geri_yukle(plan: Plan, goruntu: tuple[tuple, tuple]) -> None:
    oturumlar, gorevlendirmeler = goruntu
    durumlar = {anahtar: durum for anahtar, *durum in oturumlar}
    for oturum in plan.oturumlar:
        if oturum.anahtar in durumlar:
            (oturum.tarih, oturum.saat, oturum.salon_kimlikleri,
             oturum.hafta_sonu_gerekcesi) = durumlar[oturum.anahtar]
    plan.gorevlendirmeler = list(gorevlendirmeler)


# --------------------------------------------------------- görevli değişikliği

def gorevli_adaylari(vt: Veritabani, plan: Plan, oturum_anahtari: str, rol: GorevRolu,
                     degisecek_personel_id: int) -> list[dict]:
    """Bir görevlinin yerine geçebilecek kişiler, uygunluk ve gerekçeyle.

    Komisyonda önce alan öğretmeni, gözcülükte önce sınav branşından farklı
    öğretmen; ardından yükü az olan gelir. Uygun olmayanlar da listelenir ki
    kullanıcı neden seçilemediğini görsün.
    """
    oturum = plan.oturum_bul(oturum_anahtari)
    if oturum is None:
        raise HizmetHatasi("Oturum bulunamadı.")
    musaitsizlikler = musaitsizlikleri_getir(vt)
    alan = {esitle(b) for b in oturum.alan_branslari if b}
    bu_oturumdakiler = {g.personel_kimligi for g in plan.oturum_gorevleri(oturum_anahtari)}
    # Saat eşitliği yetmez: uzun uygulama sınavı sonraki oturum saatine taşar.
    ayni_andakiler = {
        g.personel_kimligi for g in plan.gorevlendirmeler
        for o in [plan.oturum_bul(g.oturum_anahtari)]
        if o is not None and o.anahtar != oturum_anahtari and oturumlar_cakisir_mi(o, oturum)}
    plandaki_yuk: dict[int, int] = {}
    for g in plan.gorevlendirmeler:
        plandaki_yuk[g.personel_kimligi] = plandaki_yuk.get(g.personel_kimligi, 0) + 1
    yil_yuku = _sayaclara_cevir(onceki_gorev_kayitlari(
        vt, haric=(plan.parametreler.pencere_kodu, PlanTuru(plan.parametreler.plan_turu).value)))
    adaylar = []
    for kisi in personelleri_getir(vt):
        if kisi.kimlik == degisecek_personel_id:
            continue
        neden = ""
        if not kisi.gorev_alabilir_mi:
            neden = "müdür veya rehber öğretmen"
        elif kisi.kimlik in bu_oturumdakiler:
            neden = "bu sınavda zaten görevli"
        elif kisi.kimlik in ayni_andakiler:
            neden = "aynı anda başka sınavda görevli"
        elif musait_degil_mi(musaitsizlikler.get(kisi.kimlik, ()), oturum.tarih, oturum.saat,
                             oturum.sure_dakika):
            neden = "müsait değil olarak işaretli"
        alanda = esitle(kisi.brans) in alan
        onceki_k, onceki_g = yil_yuku.get(kisi.kimlik, (0, 0))
        adaylar.append({
            "kimlik": kisi.kimlik, "ad": kisi.ad, "brans": kisi.brans, "alan_mi": alanda,
            "yonetici_mi": kisi.yonetici_mi, "uygun_mu": not neden, "neden": neden,
            "gorev_sayisi": plandaki_yuk.get(kisi.kimlik, 0) + onceki_k + onceki_g,
        })
    tercih = (lambda a: not a["alan_mi"]) if rol is GorevRolu.KOMISYON_UYESI else (
        lambda a: a["alan_mi"])
    return sorted(adaylar, key=lambda a: (not a["uygun_mu"], tercih(a), a["yonetici_mi"],
                                          a["gorev_sayisi"], siralama_anahtari(a["ad"])))


def _gorevi_degistir(plan: Plan, oturum_anahtari: str, eski_id: int, yeni_id: int,
                     gerekce: str, es_oturuma_da: bool) -> list[tuple[str, Gorevlendirme, Gorevlendirme]]:
    """Bellekteki planda görevliyi değiştirir; (oturum, eski, yeni) listesi döner."""
    oturum = plan.oturum_bul(oturum_anahtari)
    hedefler = [oturum_anahtari]
    if es_oturuma_da and oturum is not None and oturum.birim_anahtari:
        # OKY md.58/2-e: yazılı ve uygulama komisyonlarının aynı üyelerden
        # oluşturulması esastır; değişiklik eş oturuma da uygulanır.
        hedefler += [o.anahtar for o in plan.oturumlar
                     if o.birim_anahtari == oturum.birim_anahtari and o.anahtar != oturum_anahtari]
    degisenler = []
    for anahtar in hedefler:
        for sira, gorev in enumerate(plan.gorevlendirmeler):
            if gorev.oturum_anahtari == anahtar and gorev.personel_kimligi == eski_id:
                yeni = Gorevlendirme(anahtar, yeni_id, gorev.rol,
                                     gerekce.strip() or gorev.gerekce, gorev.kilitli_mi,
                                     gorev.salon_kimligi)
                plan.gorevlendirmeler[sira] = yeni
                degisenler.append((anahtar, gorev, yeni))
                break
    if not degisenler:
        raise HizmetHatasi("Bu oturumda değiştirilecek görevli bulunamadı.")
    return degisenler


def gorevli_degistir(vt: Veritabani, plan: Plan, oturum_anahtari: str, eski_personel_id: int,
                     yeni_personel_id: int, kisisel_sinirlar: dict[str, int] | None = None,
                     gerekce: str = "", es_oturuma_da: bool = True) -> TasimaSonucu:
    """Taslak planda bir görevlinin yerine başkasını koyar.

    Değişiklik bellekteki planda yapılır (kaydetmeye kadar veritabanına
    yazılmaz) ve sürükle-bırak gibi yeni engel doğuruyorsa geri alınır.
    """
    oturum = plan.oturum_bul(oturum_anahtari)
    if oturum is None:
        raise HizmetHatasi("Oturum bulunamadı.")
    if oturum.kilitli_mi:
        raise HizmetHatasi(
            "Kesinleşmiş planda görevli müdür onayıyla değiştirilir; 'Görevliyi değiştir' "
            "penceresinde onay numarasını girin.")
    onceki = _engel_imzalari(vt, plan, kisisel_sinirlar)
    yedek = list(plan.gorevlendirmeler)
    _gorevi_degistir(plan, oturum_anahtari, eski_personel_id, yeni_personel_id, gerekce,
                     es_oturuma_da)

    def geri_al() -> None:
        plan.gorevlendirmeler = yedek

    return _yeni_engellere_bak(vt, plan, kisisel_sinirlar, onceki, geri_al)


def kesin_plan_gorevli_degistir(vt: Veritabani, plan_id: int, oturum_anahtari: str,
                                eski_personel_id: int, yeni_personel_id: int,
                                mudur_onay_no: str, gerekce: str,
                                es_oturuma_da: bool = True) -> TasimaSonucu:
    """Kesinleşmiş planda görevli değiştirir; müdür onayı ve gerekçe zorunludur.

    Plan kesin kalır. Değişiklik yeni engel doğurmuyorsa veritabanına
    yazılır ve eski/yeni kişi, onay numarası ve gerekçeyle saklanır; evrak
    bu kaydı listeler.
    """
    if not str(mudur_onay_no).strip():
        raise HizmetHatasi("Kesin planda görevli değişikliği müdür onay numarası ister.")
    if not str(gerekce).strip():
        raise HizmetHatasi("Görevli değişikliğinin gerekçesi zorunludur (sağlık bilgisi "
                           "yazmayın; 'izinli', 'başka görevde' gibi yazın).")
    plan, bilgi = plan_yukle(vt, plan_id)
    if not bilgi["kesin_mi"]:
        raise HizmetHatasi("Bu plan kesin değil; değişikliği plan ekranında yapıp kaydedin.")
    onceki = _engel_imzalari(vt, plan, bilgi["kisisel_sinirlar"])
    degisenler = _gorevi_degistir(plan, oturum_anahtari, eski_personel_id, yeni_personel_id,
                                  "", es_oturuma_da)
    sonuc = _yeni_engellere_bak(vt, plan, bilgi["kisisel_sinirlar"], onceki, lambda: None)
    if not sonuc.uygulandi:
        return sonuc
    zaman = simdi()
    with vt.baglan() as b:
        for anahtar, eski, yeni in degisenler:
            satir = b.execute(
                "SELECT g.id FROM v_gorevlendirme g JOIN v_oturum o ON o.id=g.oturum_id"
                " WHERE o.plan_id=? AND o.anahtar=? AND g.personel_id=?",
                (plan_id, anahtar, eski.personel_kimligi)).fetchone()
            if not satir:
                raise HizmetHatasi("Görevlendirme kaydı bulunamadı.")
            b.execute("UPDATE gorevlendirme SET personel_id=?,ucretlendirilebilir_mi=? WHERE id=?",
                      (yeni.personel_kimligi, int(not _yonetici_mi(b, yeni.personel_kimligi)),
                       satir[0]))
            b.execute(
                "INSERT INTO gorevli_degisikligi(gorevlendirme_id,eski_personel_id,"
                "yeni_personel_id,mudur_onay_no,gerekce,olusturuldu_at) VALUES(?,?,?,?,?,?)",
                (satir[0], eski.personel_kimligi, yeni.personel_kimligi,
                 str(mudur_onay_no).strip(), str(gerekce).strip(), zaman))
            vt.denetim_yaz(b, "gorevlendirme", int(satir[0]), "gorevli_degisti",
                           str(mudur_onay_no).strip())
    return sonuc


def gorevli_degisiklikleri(vt: Veritabani, plan_id: int) -> list[dict]:
    """Kesin planda müdür onayıyla yapılmış görevli değişiklikleri."""
    with vt.baglan() as b:
        return [{"tarih": date.fromisoformat(r[0]), "saat": r[1], "ders": r[2],
                 "tur": r[3], "rol": r[4], "eski": r[5], "yeni": r[6], "onay_no": r[7],
                 "gerekce": r[8], "degisti_at": r[9]}
                for r in b.execute("""
                    SELECT o.tarih, o.saat, d.ad, o.oturum_turu, g.rol, eski.ad, yeni.ad,
                           gd.mudur_onay_no, gd.gerekce, gd.olusturuldu_at
                    FROM gorevli_degisikligi gd
                    JOIN gorevlendirme g ON g.id = gd.gorevlendirme_id
                    JOIN v_oturum o ON o.id = g.oturum_id
                    JOIN v_ders d ON d.id = o.ders_id
                    JOIN personel eski ON eski.id = gd.eski_personel_id
                    JOIN personel yeni ON yeni.id = gd.yeni_personel_id
                    WHERE o.plan_id = ? ORDER BY gd.id""", (plan_id,))]
