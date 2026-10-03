"""Plan bağlamı, sınav birimleri, plan üretimi, doğrulama, kayıt ve
kesinleştirme.

Plan üretimi ile plan kaydı bilinçli olarak ayrılmıştır: `plan_hazirla`
hiçbir şey yazmaz, üretilen plan bellekte düzenlenir (sürükle-bırak, geri
al), `plan_kaydet` ise tek bir işlemde yazar.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time

from cekirdek.kurallar import DogrulamaBaglami, dogrula_plan, salonlara_dagit
from cekirdek.metin import esitle
from cekirdek.modeller import (
    Gorevlendirme, GorevRolu, Ihlal, IkiAsamaliSayim, Musaitsizlik, Oturum, OturumTuru,
    Personel, Plan, PlanParametreleri, PlanTuru, Salon,
)
from cekirdek.planlayici import PlanlamaSonucu, plan_uret
from cekirdek.takvim import gunleri_listele, pencere_adi, tek_ders_penceresi
from cekirdek.talep import SinavBirimi, YukOzeti, birimleri_olustur, yuk_ozeti
from ..veritabani import Veritabani, simdi

from .ortak import (
    HizmetHatasi, VARSAYILAN_SLOT_SAATLERI, ayarlari_getir, ogretim_yili, pencereleri_getir,
    salonlari_getir, tatilleri_getir,
)
from .plan_kayitlari import kesin_plan, son_plani_getir
from .personel import brans_havuzu_listele, musaitsizlikleri_getir, personelleri_getir
from .gorev import _sayaclara_cevir, onceki_gorev_kayitlari
from .basvuru import basvuru_kapsamindaki_ogrenciler, gecerli_basvurular, ogrenci_etiketleri
from .tek_ders import tek_ders_kayitlari
from .sorumluluk import ders_ayarlari, sorumluluk_kayitlari


# ===================================================================== plan

@dataclass
class PlanBaglami:
    """Doğrulama ve gösterim için gereken dış bilgiler."""

    pencere: tuple[date, date]
    personel: dict[int, Personel]
    salonlar: dict[int, Salon]
    ogrenci_adlari: dict[str, str]
    iki_asamali_dersler: frozenset[str]
    ogretim_yili: str
    kisisel_sinirlar: dict[str, int] = field(default_factory=dict)

    basvuru_kapsami: frozenset[str] = field(default_factory=frozenset)
    gecerli_basvurular: frozenset[str] = field(default_factory=frozenset)
    onceki_gorevler: tuple[tuple[int, GorevRolu, date], ...] = ()
    tatiller: frozenset[date] = field(default_factory=frozenset)
    musaitsizlikler: dict[int, tuple[Musaitsizlik, ...]] = field(default_factory=dict)

    def dogrulama_baglami(self) -> DogrulamaBaglami:
        return DogrulamaBaglami(
            pencere=self.pencere,
            personel=self.personel,
            ogrenci_adlari=self.ogrenci_adlari,
            iki_asamali_dersler=self.iki_asamali_dersler,
            ogretim_yili=self.ogretim_yili,
            kisisel_gunluk_sinir=self.kisisel_sinirlar,
            basvuru_kapsami=self.basvuru_kapsami,
            gecerli_basvurular=self.gecerli_basvurular,
            onceki_gorevler=self.onceki_gorevler,
            tatiller=self.tatiller,
            musaitsizlikler=self.musaitsizlikler,
        )

    def personel_adi(self, kimlik: int) -> str:
        kisi = self.personel.get(kimlik)
        return kisi.ad if kisi else f"#{kimlik}"

    def salon_adi(self, kimlik: int) -> str:
        salon = self.salonlar.get(kimlik)
        return salon.ad if salon else f"#{kimlik}"


def plan_baglami(vt: Veritabani, pencere_kodu: str,
                 kisisel_sinirlar: dict[str, int] | None = None,
                 tur: PlanTuru | str = PlanTuru.OLAGAN) -> PlanBaglami:
    """Bir planı doğrulamak için gereken her şey.

    Tek ders planında (OKY md.58/6) başvuru kapısı uygulanmaz: o öğrenciler
    olağan plandan elle seçilir, kapıdan zaten geçmişlerdir.
    """
    tur = PlanTuru(tur)
    ayar = ayarlari_getir(vt)
    with vt.baglan() as b:
        iki_asamali = frozenset(
            r[0] for r in b.execute("SELECT ad FROM v_ders WHERE iki_asamali_mi=1"))
    olagan = tur is PlanTuru.OLAGAN
    return PlanBaglami(
        pencere=pencere_araligi(vt, pencere_kodu, tur),
        personel={p.kimlik: p for p in personelleri_getir(vt, yalniz_aktif=False)},
        salonlar={s.kimlik: s for s in salonlari_getir(vt)},
        ogrenci_adlari=ogrenci_etiketleri(vt),
        iki_asamali_dersler=iki_asamali,
        ogretim_yili=ayar.get("ogretim_yili", ""),
        kisisel_sinirlar=kisisel_sinirlar or {},
        basvuru_kapsami=frozenset(basvuru_kapsamindaki_ogrenciler(vt)) if olagan else frozenset(),
        gecerli_basvurular=gecerli_basvurular(vt, pencere_kodu) if olagan else frozenset(),
        onceki_gorevler=onceki_gorev_kayitlari(vt, haric=(pencere_kodu, tur.value)),
        tatiller=tatilleri_getir(vt),
        musaitsizlikler=musaitsizlikleri_getir(vt),
    )


def pencere_araligi(vt: Veritabani, pencere_kodu: str,
                    tur: PlanTuru | str = PlanTuru.OLAGAN) -> tuple[date, date]:
    """Planın tarih penceresi.

    Olağan planda OKY md.58/2-a penceresidir. Tek ders sınavında (OKY md.58/6)
    "takip eden hafta"dır: o dönemin olağan planındaki son sınavın haftasından
    sonraki hafta; olağan plan yoksa pencere sonu esas alınır.
    """
    pencere = pencereleri_getir(vt)[pencere_kodu]
    if PlanTuru(tur) is PlanTuru.OLAGAN:
        return pencere
    son_sinav = pencere[1]
    plan_id = son_plani_getir(vt, pencere_kodu)
    if plan_id is not None:
        with vt.baglan() as b:
            satir = b.execute("SELECT MAX(tarih) FROM v_oturum WHERE plan_id=?",
                              (plan_id,)).fetchone()
        if satir and satir[0]:
            son_sinav = date.fromisoformat(satir[0])
    return tek_ders_penceresi(son_sinav)


def brans_eslemelerini_denetle(vt: Veritabani, dersler: set[str]) -> None:
    """Eşlenen branşların havuzda gerçekten bulunduğunu doğrular.

    Eşleme havuzdaki bir adla tutmuyorsa o derse hiçbir öğretmen atanamaz.
    Bu sessizce "öğretmen yok" hatasına dönüşmesin diye önden söylenir;
    eski sürümlerden kalan bozuk eşlemeler de böyle yakalanır.
    """
    havuz = {esitle(ad) for _, ad, _ in brans_havuzu_listele(vt)}
    hatali = []
    for ders, ayar in ders_ayarlari(vt).items():
        if ders not in dersler:
            continue
        for brans in ayar.alan_branslari:
            if brans and esitle(brans) not in havuz:
                hatali.append(f"{ders} → '{brans}'")
    if hatali:
        raise HizmetHatasi(
            "Şu derslerin branş eşlemesi branş havuzundaki hiçbir alanla tutmuyor. "
            "Ders / Branş ekranından yeniden eşleyin:\n\n"
            + "\n".join(f"  • {satir}" for satir in sorted(hatali)[:10]))


def sinav_birimleri(vt: Veritabani, pencere_kodu: str | None = None,
                    tur: PlanTuru | str = PlanTuru.OLAGAN) -> list[SinavBirimi]:
    if PlanTuru(tur) is PlanTuru.TEK_DERS:
        kayitlar = tek_ders_kayitlari(vt, pencere_kodu or "P1")
        if not kayitlar:
            raise HizmetHatasi(
                "Tek ders sınavına girecek öğrenci seçilmedi. Plan ekranındaki 'Tek ders "
                "öğrencileri' düğmesiyle öğrenciyi ve dersini seçin (OKY md.58/6).")
    else:
        kayitlar = sorumluluk_kayitlari(vt, pencere_kodu)
        if not kayitlar:
            raise HizmetHatasi(
                "Aktif sorumluluk kaydı yok. Önce e-Okul sorumluluk raporunu içe aktarın.")
    salonlar = salonlari_getir(vt)
    if not salonlar:
        raise HizmetHatasi("Önce en az bir sınav salonu tanımlayın.")
    brans_eslemelerini_denetle(vt, {k.ders_adi for k in kayitlar})
    return birimleri_olustur(kayitlar, ders_ayarlari(vt), salonlar)


def yuk_ozetini_getir(vt: Veritabani, sayim: IkiAsamaliSayim, gunluk_sinir: int,
                      pencere_kodu: str | None = None,
                      tur: PlanTuru | str = PlanTuru.OLAGAN) -> YukOzeti:
    return yuk_ozeti(sinav_birimleri(vt, pencere_kodu, tur), sayim, gunluk_sinir)


def _kesin_plan_engeli(vt: Veritabani, pencere_kodu: str, tur: PlanTuru) -> None:
    """Kesinleşmiş planın üstüne yeni plan yazılmasını engeller.

    Eski sürümde aynı dönem için yeni taslak kaydedilebiliyordu: ekran ve
    evrak taslağı gösteriyor, görev sayaçları iki planı birden sayıyordu.
    Kesin planda değişiklik yalnız görevli değişikliğiyle ve müdür onayıyla
    yapılır.
    """
    kesin = kesin_plan(vt, pencere_kodu, tur)
    if kesin:
        ad = pencere_adi(pencere_kodu) + (" tek ders sınavı" if tur is PlanTuru.TEK_DERS else "")
        raise HizmetHatasi(
            f"{ad} planı müdür onayıyla kesinleşmiştir (plan #{kesin[0]}, onay no "
            f"{kesin[1] or '—'}). Kesin planın yerine yeni plan kaydedilemez; görevli "
            "değişikliği için plan ekranındaki 'Görevliyi değiştir' kullanılır.")


def plan_hazirla(vt: Veritabani, parametreler: PlanParametreleri) -> PlanlamaSonucu:
    """Planı üretir; **veritabanına hiçbir şey yazmaz.**

    Üretilen plan arayüzde düzenlenir (sürükle-bırak, geri al) ve ancak
    `plan_kaydet` çağrıldığında yazılır.
    """
    tur = PlanTuru(parametreler.plan_turu)
    _kesin_plan_engeli(vt, parametreler.pencere_kodu, tur)
    pencere = pencere_araligi(vt, parametreler.pencere_kodu, tur)
    tatiller = tatilleri_getir(vt)
    gunler = gunleri_listele(pencere[0], pencere[1], parametreler.hafta_sonu_kullan, tatiller)
    # Aynı öğretim yılının diğer planlarındaki görevler sayaçlara başlangıç
    # değeri olur; böylece yük üç dönem boyunca dengelenir. Aynı dönemin eski
    # planı sayılmaz: yeni plan onun yerine geçecektir.
    onceki = onceki_gorev_kayitlari(vt, haric=(parametreler.pencere_kodu, tur.value))
    return plan_uret(
        birimler=sinav_birimleri(vt, parametreler.pencere_kodu, tur),
        parametreler=parametreler,
        gunler=gunler,
        personel=personelleri_getir(vt),
        salonlar=salonlari_getir(vt),
        pencere=pencere,
        ogretim_yili=ogretim_yili(vt),
        ogrenci_adlari=ogrenci_etiketleri(vt),
        baslangic_sayaclari=_sayaclara_cevir(onceki),
        musaitsizlikler=musaitsizlikleri_getir(vt),
        tatiller=tatiller,
        onceki_gorevler=onceki,
    )


def plani_dogrula(vt: Veritabani, plan: Plan,
                  kisisel_sinirlar: dict[str, int] | None = None) -> list[Ihlal]:
    """Elle düzenlenmiş planı da aynı kurallardan geçirir."""
    baglam = plan_baglami(vt, plan.parametreler.pencere_kodu, kisisel_sinirlar,
                          plan.parametreler.plan_turu)
    return dogrula_plan(plan, baglam.dogrulama_baglami(), baglam.salonlar)


def plan_kaydet(vt: Veritabani, sonuc: PlanlamaSonucu) -> int:
    """Planı, oturumları, öğrenci yerleşimini ve görevleri tek işlemde yazar.

    Aynı öğretim yılında aynı dönem ve türün taslağı varsa yenisi onun yerine
    geçer. Kesinleşmiş planın yerine plan yazılmaz (bkz. `_kesin_plan_engeli`).
    """
    import json
    plan = sonuc.plan
    parametreler = plan.parametreler
    tur = PlanTuru(parametreler.plan_turu)
    _kesin_plan_engeli(vt, parametreler.pencere_kodu, tur)
    yil = ogretim_yili(vt)
    ogrenci_kimlikleri = {}
    with vt.baglan() as b:
        for okul_no, sube, kimlik in b.execute("SELECT okul_no,sube,id FROM v_ogrenci"):
            ogrenci_kimlikleri[f"{okul_no}|{sube}"] = kimlik
        ders_kimlikleri = {r[0]: r[1] for r in b.execute("SELECT ad,id FROM v_ders")}
        kapasiteler = {r[0]: r[1] for r in b.execute("SELECT id,kapasite FROM v_salon")}

        # Eski sürüm taslağı yalnız dönem koduna bakarak siliyordu: yeni yılın
        # Eylül planı geçen yılın Eylül taslağını da siliyordu.
        b.execute("UPDATE plan SET silindi_mi=1 WHERE pencere_kodu=? AND tur=? AND ogretim_yili=?"
                  " AND durum='taslak' AND silindi_mi=0",
                  (parametreler.pencere_kodu, tur.value, yil))
        # Yükseltilmiş kişisel sınırlar planın parçasıdır; saklanmazsa
        # kaydedilen plan yeniden açıldığında varsayılan sınırla doğrulanır ve
        # kurallara uyan plan SP-11 ihlalleriyle dolu görünür.
        plan_id = int(b.execute(
            "INSERT INTO plan(pencere_kodu,parametreler_json,kisisel_sinirlar_json,"
            "ogretim_yili,uretildi_at,tur) VALUES(?,?,?,?,?,?)",
            (parametreler.pencere_kodu, _parametreleri_yaz(parametreler),
             json.dumps(sonuc.yukseltilen_sinirlar, ensure_ascii=False, sort_keys=True),
             yil, simdi(), tur.value)).lastrowid)

        for oturum in plan.oturumlar:
            ders_id = ders_kimlikleri.get(oturum.ders_adi)
            if ders_id is None:
                raise HizmetHatasi(f"'{oturum.ders_adi}' dersi veritabanında bulunamadı.")
            oturum_id = int(b.execute(
                "INSERT INTO oturum(plan_id,anahtar,ders_id,duzey_kumesi,oturum_turu,"
                "birim_anahtari,tarih,saat,sure,hafta_sonu_gerekcesi,kilitli_mi)"
                " VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (plan_id, oturum.anahtar, ders_id,
                 ",".join(str(d) for d in oturum.duzeyler), oturum.oturum_turu.value,
                 oturum.birim_anahtari, oturum.tarih.isoformat(),
                 oturum.saat.strftime("%H:%M"), oturum.sure_dakika,
                 oturum.hafta_sonu_gerekcesi, int(oturum.kilitli_mi))).lastrowid)
            for sira, salon_id in enumerate(oturum.salon_kimlikleri, 1):
                b.execute("INSERT INTO oturum_salon(oturum_id,salon_id,sira) VALUES(?,?,?)",
                          (oturum_id, salon_id, sira))
            ogrenci_salonlari = _ogrenci_salonlari(oturum, kapasiteler)
            for sira, anahtar in enumerate(oturum.ogrenci_anahtarlari, 1):
                ogrenci_id = ogrenci_kimlikleri.get(anahtar)
                if ogrenci_id is None:
                    raise HizmetHatasi(f"'{anahtar}' öğrencisi veritabanında bulunamadı.")
                b.execute(
                    "INSERT INTO oturum_ogrenci(oturum_id,ogrenci_id,salon_id,sira)"
                    " VALUES(?,?,?,?)", (oturum_id, ogrenci_id, ogrenci_salonlari[sira - 1], sira))
            for gorev in plan.oturum_gorevleri(oturum.anahtar):
                b.execute(
                    "INSERT INTO gorevlendirme(oturum_id,personel_id,rol,"
                    "ucretlendirilebilir_mi,gerekce,kilitli_mi,salon_id) VALUES(?,?,?,?,?,?,?)",
                    (oturum_id, gorev.personel_kimligi, gorev.rol.value,
                     int(not _yonetici_mi(b, gorev.personel_kimligi)), gorev.gerekce,
                     int(gorev.kilitli_mi), gorev.salon_kimligi))
        vt.denetim_yaz(b, "plan", plan_id, "kaydedildi",
                       f"{len(plan.oturumlar)} oturum")
        return plan_id


def _yonetici_mi(baglanti, personel_id: int) -> bool:
    kisi = baglanti.execute("SELECT unvan FROM v_personel WHERE id=?", (personel_id,)).fetchone()
    return Personel(0, "", "", kisi[0]).yonetici_mi if kisi else False


def _ogrenci_salonlari(oturum: Oturum, kapasiteler: dict[int, int]) -> list[int | None]:
    """Oturumdaki her öğrencinin salonu, öğrenci sırasıyla.

    Öğrenciler salon kapasitesiyle orantılı bloklar hâlinde dağıtılır
    (bkz. kurallar.salonlara_dagit); eski sürümün sırayla dağıtımı küçük
    salona kapasitesinden fazla öğrenci yazabiliyordu.
    """
    if not oturum.salon_kimlikleri:
        return [None] * oturum.ogrenci_sayisi
    adetler = salonlara_dagit(oturum.ogrenci_sayisi,
                              [kapasiteler.get(s, 0) for s in oturum.salon_kimlikleri])
    salonlar: list[int | None] = []
    for salon_id, adet in zip(oturum.salon_kimlikleri, adetler):
        salonlar.extend([salon_id] * adet)
    return salonlar


def plan_yukle(vt: Veritabani, plan_id: int) -> tuple[Plan, dict[str, int]]:
    """Kaydedilmiş planı bellek modeline geri okur."""
    import json
    with vt.baglan() as b:
        satir = b.execute(
            "SELECT pencere_kodu,parametreler_json,durum,mudur_onay_no,kisisel_sinirlar_json,"
            "tur FROM v_plan WHERE id=?", (plan_id,)).fetchone()
        if not satir:
            raise HizmetHatasi("Plan bulunamadı.")
        parametreler = _parametreleri_oku(satir[1], satir[0], satir[5])
        plan = Plan(parametreler)
        oturum_anahtarlari = {}
        for r in b.execute("""
                SELECT o.id,o.anahtar,d.ad,o.duzey_kumesi,o.oturum_turu,o.birim_anahtari,
                       o.tarih,o.saat,o.sure,o.hafta_sonu_gerekcesi,o.kilitli_mi,
                       COALESCE(d.brans,''),d.esdeger_branslar
                FROM v_oturum o JOIN v_ders d ON d.id=o.ders_id
                WHERE o.plan_id=? ORDER BY o.tarih,o.saat,d.ad""", (plan_id,)):
            ogrenciler = tuple(x[0] for x in b.execute(
                "SELECT og.okul_no||'|'||og.sube FROM v_oturum_ogrenci oo"
                " JOIN v_ogrenci og ON og.id=oo.ogrenci_id"
                " WHERE oo.oturum_id=? ORDER BY oo.sira", (r[0],)))
            salonlar = tuple(x[0] for x in b.execute(
                "SELECT salon_id FROM v_oturum_salon WHERE oturum_id=? ORDER BY sira", (r[0],)))
            try:
                esdeger = tuple(json.loads(r[12] or "[]"))
            except ValueError:
                esdeger = ()
            plan.oturumlar.append(Oturum(
                anahtar=r[1], ders_adi=r[2],
                duzeyler=tuple(int(x) for x in str(r[3]).split(",") if x),
                ogrenci_anahtarlari=ogrenciler, oturum_turu=OturumTuru(r[4]),
                tarih=date.fromisoformat(r[6]), saat=time.fromisoformat(r[7]),
                sure_dakika=r[8], salon_kimlikleri=salonlar,
                alan_bransi=str(r[11]).strip(),
                esdeger_branslar=esdeger,
                birim_anahtari=r[5], hafta_sonu_gerekcesi=r[9], kilitli_mi=bool(r[10])))
            oturum_anahtarlari[r[0]] = r[1]
        for oturum_id, personel_id, rol, gerekce, kilitli, salon_id in b.execute("""
                SELECT g.oturum_id,g.personel_id,g.rol,g.gerekce,g.kilitli_mi,g.salon_id
                FROM v_gorevlendirme g JOIN v_oturum o ON o.id=g.oturum_id
                WHERE o.plan_id=? ORDER BY g.id""", (plan_id,)):
            plan.gorevlendirmeler.append(Gorevlendirme(
                oturum_anahtarlari[oturum_id], personel_id, GorevRolu(rol),
                gerekce or "", bool(kilitli), salon_id))
        try:
            kisisel_sinirlar = dict(json.loads(satir[4] or "{}"))
        except ValueError:
            kisisel_sinirlar = {}
        return plan, {"plan_id": plan_id, "kesin_mi": int(satir[2] == "kesin"),
                      "mudur_onay_no": satir[3] or "",
                      "kisisel_sinirlar": kisisel_sinirlar}


def plan_kesinlestir(vt: Veritabani, plan_id: int, mudur_onay_no: str) -> None:
    """SP-05: plan müdür onayıyla kesinleşir ve oturumlar kilitlenir."""
    if not str(mudur_onay_no).strip():
        raise HizmetHatasi("Planı kesinleştirmek için müdür onay numarası zorunludur (SP-05).")
    plan, bilgi = plan_yukle(vt, plan_id)
    if bilgi["kesin_mi"]:
        raise HizmetHatasi("Bu plan zaten kesinleşmiştir.")
    engeller = [i for i in plani_dogrula(vt, plan, bilgi["kisisel_sinirlar"]) if i.engel_mi]
    if engeller:
        raise HizmetHatasi(
            "Engelli plan kesinleştirilemez:\n" +
            "\n".join(f"• {i.kural_kimligi} {i.aciklama}" for i in engeller[:5]))
    with vt.baglan() as b:
        b.execute("UPDATE plan SET durum='kesin',mudur_onay_no=?,kesinlesti_at=? WHERE id=?",
                  (str(mudur_onay_no).strip(), simdi(), plan_id))
        b.execute("UPDATE oturum SET kilitli_mi=1 WHERE plan_id=?", (plan_id,))
        vt.denetim_yaz(b, "plan", plan_id, "kesinlestirildi")


def plan_sil(vt: Veritabani, plan_id: int) -> None:
    with vt.baglan() as b:
        durum = b.execute("SELECT durum FROM v_plan WHERE id=?", (plan_id,)).fetchone()
        if not durum:
            raise HizmetHatasi("Plan bulunamadı.")
        if durum[0] == "kesin":
            raise HizmetHatasi("Kesinleşmiş plan silinemez; kayıt denetim izindedir.")
        b.execute("UPDATE plan SET silindi_mi=1 WHERE id=?", (plan_id,))
        b.execute("UPDATE oturum SET silindi_mi=1 WHERE plan_id=?", (plan_id,))
        vt.denetim_yaz(b, "plan", plan_id, "silindi")


# ------------------------------------------------------ parametre serileştirme

def _parametreleri_yaz(p: PlanParametreleri) -> str:
    import json
    return json.dumps({
        "pencere_kodu": p.pencere_kodu,
        "hafta_sonu_kullan": p.hafta_sonu_kullan,
        "ogrenci_gunluk_sinav_siniri": p.ogrenci_gunluk_sinav_siniri,
        "iki_asamali_sayim": p.iki_asamali_sayim.value,
        "slot_saatleri": [s.strftime("%H:%M") for s in p.slot_saatleri],
        "oturum_suresi_dakika": p.oturum_suresi_dakika,
        "uygulama_suresi_dakika": p.uygulama_suresi_dakika,
        "hedef_gun_sayisi": p.hedef_gun_sayisi,
        "plan_turu": PlanTuru(p.plan_turu).value,
    }, ensure_ascii=False, sort_keys=True)


def _parametreleri_oku(metin: str, pencere_kodu: str,
                       tur: str = PlanTuru.OLAGAN.value) -> PlanParametreleri:
    """Saklanan parametreleri okur; plan türünde veritabanı sütunu esastır."""
    import json
    try:
        veri = json.loads(metin)
    except ValueError:
        veri = {}
    return PlanParametreleri(
        pencere_kodu=veri.get("pencere_kodu", pencere_kodu),
        hafta_sonu_kullan=bool(veri.get("hafta_sonu_kullan", False)),
        ogrenci_gunluk_sinav_siniri=int(veri.get("ogrenci_gunluk_sinav_siniri", 2)),
        iki_asamali_sayim=IkiAsamaliSayim(veri.get("iki_asamali_sayim", "tek")),
        slot_saatleri=tuple(datetime.strptime(s, "%H:%M").time()
                            for s in veri.get("slot_saatleri", VARSAYILAN_SLOT_SAATLERI)),
        oturum_suresi_dakika=int(veri.get("oturum_suresi_dakika", 40)),
        hedef_gun_sayisi=veri.get("hedef_gun_sayisi"),
        uygulama_suresi_dakika=int(veri.get("uygulama_suresi_dakika",
                                            veri.get("oturum_suresi_dakika", 40))),
        plan_turu=PlanTuru(tur or PlanTuru.OLAGAN.value),
    )


def slot_saatlerini_coz(metin: str) -> tuple[time, ...]:
    """'08:00, 09:00' biçimindeki girdiyi saat demetine çevirir."""
    parcalar = [p.strip() for p in str(metin).replace(";", ",").split(",") if p.strip()]
    if not parcalar:
        raise HizmetHatasi("En az bir oturum saati girilmelidir.")
    try:
        saatler = tuple(datetime.strptime(p, "%H:%M").time() for p in parcalar)
    except ValueError as hata:
        raise HizmetHatasi(
            "Oturum saatleri SS:DD biçiminde ve virgülle ayrılmış olmalıdır.") from hata
    if len(set(saatler)) != len(saatler):
        raise HizmetHatasi("Oturum saatleri yinelenemez.")
    if any(a >= b for a, b in zip(saatler, saatler[1:])):
        raise HizmetHatasi("Oturum saatleri artan sırada girilmelidir.")
    return saatler
