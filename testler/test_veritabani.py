from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from veri.veritabani import Veritabani


@pytest.fixture()
def vt(tmp_path: Path) -> Veritabani:
    veritabani = Veritabani(tmp_path / "sorumluluk.db")
    veritabani.gocleri_uygula()
    return veritabani


def test_goc_uygulanir_ve_yinelenmez(tmp_path: Path) -> None:
    veritabani = Veritabani(tmp_path / "sorumluluk.db")
    assert veritabani.gocleri_uygula() == 1
    assert veritabani.surum() == 1
    assert veritabani.gocleri_uygula() == 0


def test_yabanci_anahtar_butunlugu_saglam(vt: Veritabani) -> None:
    with vt.baglan() as b:
        assert list(b.execute("PRAGMA foreign_key_check")) == []


def test_yabanci_anahtar_ihlali_reddedilir(vt: Veritabani) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        with vt.baglan() as b:
            b.execute("INSERT INTO ders_brans(ders_id,brans,surum,karar_metni,etkin_baslangic)"
                      " VALUES(9999,'Matematik',1,'karar','2026-09-14')")


def test_hata_alan_islem_geri_alinir(vt: Veritabani) -> None:
    with pytest.raises(RuntimeError):
        with vt.baglan() as b:
            b.execute("INSERT INTO salon(ad,ad_anahtari,kapasite) VALUES('A-101','a-101',30)")
            raise RuntimeError("işlem yarıda kesildi")
    with vt.baglan() as b:
        assert b.execute("SELECT count(*) FROM salon").fetchone()[0] == 0


def test_denetim_izi_zinciri_dogrulanir(vt: Veritabani) -> None:
    with vt.baglan() as b:
        for kayit_id in range(1, 4):
            vt.denetim_yaz(b, "salon", kayit_id, "eklendi")
    assert vt.denetim_izi_saglam_mi()


def test_denetim_izi_degistirilemez_ve_silinemez(vt: Veritabani) -> None:
    with vt.baglan() as b:
        vt.denetim_yaz(b, "salon", 1, "eklendi")
    for sql in ("UPDATE denetim_izi SET islem='sahte' WHERE id=1",
                "DELETE FROM denetim_izi WHERE id=1"):
        with pytest.raises(sqlite3.IntegrityError):
            with vt.baglan() as b:
                b.execute(sql)


def test_denetim_izinde_kisisel_veri_tutulmaz(vt: Veritabani) -> None:
    """Denetim izi yalnız tablo, kayıt kimliği ve işlem tutar."""
    with vt.baglan() as b:
        sutunlar = {r[1] for r in b.execute("PRAGMA table_info(denetim_izi)")}
    assert sutunlar == {"id", "tablo", "kayit_id", "islem", "ayrinti",
                        "onceki_hash", "hash", "zaman"}


def test_yedek_wal_icerigini_de_kapsar(vt: Veritabani, tmp_path: Path) -> None:
    """WAL kipinde .db dosyasını kopyalamak eksik yedek üretir; SQLite'ın
    backup API'si henüz checkpoint edilmemiş yazmaları da alır."""
    with vt.baglan() as b:
        b.execute("INSERT INTO salon(ad,ad_anahtari,kapasite) VALUES('A-101','a-101',30)")
    yedek = vt.yedek_al(tmp_path / "yedekler")
    kopya = sqlite3.connect(yedek)
    try:
        assert kopya.execute("SELECT ad FROM salon").fetchone()[0] == "A-101"
    finally:
        kopya.close()


def test_yumusak_silinen_kayit_gorunumde_gorunmez(vt: Veritabani) -> None:
    with vt.baglan() as b:
        b.execute("INSERT INTO salon(ad,ad_anahtari,kapasite) VALUES('A-101','a-101',30)")
        b.execute("UPDATE salon SET silindi_mi=1 WHERE ad_anahtari='a-101'")
        assert b.execute("SELECT count(*) FROM salon").fetchone()[0] == 1
        assert b.execute("SELECT count(*) FROM v_salon").fetchone()[0] == 0


def test_ayni_kisi_bir_oturumda_iki_gorev_alamaz(vt: Veritabani) -> None:
    """Karar md.12/2-b veritabanı düzeyinde de korunur."""
    with vt.baglan() as b:
        b.execute("INSERT INTO ders(ad,ad_anahtari,brans) VALUES('MATEMATİK','matematik','Matematik')")
        b.execute("INSERT INTO personel(ad,ad_anahtari,brans,unvan)"
                  " VALUES('Uydurma Öğretmen','uydurma öğretmen','Matematik','Öğretmen')")
        b.execute("INSERT INTO plan(pencere_kodu,parametreler_json,uretildi_at)"
                  " VALUES('P1','{}','2026-09-14T08:00:00')")
        b.execute("INSERT INTO oturum(plan_id,anahtar,ders_id,duzey_kumesi,oturum_turu,tarih,saat,sure)"
                  " VALUES(1,'a1',1,'9','yazili','2026-09-14','09:00',40)")
        b.execute("INSERT INTO gorevlendirme(oturum_id,personel_id,rol) VALUES(1,1,'komisyon_uyesi')")
    with pytest.raises(sqlite3.IntegrityError):
        with vt.baglan() as b:
            b.execute("INSERT INTO gorevlendirme(oturum_id,personel_id,rol) VALUES(1,1,'gozcu')")


def test_ilk_kurulumda_anlamsiz_yedek_birakilmaz(tmp_path: Path) -> None:
    """Boş veritabanı WAL kipi yüzünden sıfır bayt değildir; yine de içinde
    kullanıcı verisi olmadığı için yedeklenmemelidir."""
    veritabani = Veritabani(tmp_path / "sorumluluk.db")
    veritabani.gocleri_uygula()
    assert list(tmp_path.glob("*.yedek")) == []


def test_veri_varken_goc_oncesi_yedek_alinir(tmp_path: Path) -> None:
    veritabani = Veritabani(tmp_path / "sorumluluk.db")
    veritabani.gocleri_uygula()
    with veritabani.baglan() as b:
        b.execute("INSERT INTO salon(ad,ad_anahtari,kapasite) VALUES('A-101','a-101',30)")
    assert veritabani._yedekle("deneme") is not None
    assert len(list(tmp_path.glob("*.yedek"))) == 1


def test_baska_uygulamanin_veritabani_reddedilir(tmp_path: Path) -> None:
    """Önceki sürümün veritabanı aynı klasörde durabilir. Göç sayacı uyuştuğu
    için şema kurulu sanılırsa uygulama sonradan 'no such table' ile çöker."""
    from veri.veritabani import VeritabaniUyumsuz
    yabanci = tmp_path / "sorumluluk.db"
    b = sqlite3.connect(yabanci)
    b.execute("CREATE TABLE uygulama_ayari(anahtar TEXT, deger TEXT)")
    b.execute("PRAGMA user_version=6")
    b.commit()
    b.close()

    veritabani = Veritabani(yabanci)
    with pytest.raises(VeritabaniUyumsuz, match="bu uygulamaya ait değil"):
        veritabani.gocleri_uygula()
    # Yabancı dosyaya dokunulmamış olmalı.
    b = sqlite3.connect(yabanci)
    try:
        assert b.execute("PRAGMA user_version").fetchone()[0] == 6
        assert b.execute(
            "SELECT count(*) FROM sqlite_master WHERE name='uygulama_ayari'").fetchone()[0] == 1
    finally:
        b.close()


def test_kendi_veritabanimiz_imzalanir(tmp_path: Path) -> None:
    from veri.veritabani import UYGULAMA_KIMLIGI
    veritabani = Veritabani(tmp_path / "sorumluluk.db")
    veritabani.gocleri_uygula()
    with veritabani.baglan() as b:
        assert int(b.execute("PRAGMA application_id").fetchone()[0]) == UYGULAMA_KIMLIGI
    # İkinci açılışta uyum denetimi sorun çıkarmamalı.
    assert veritabani.gocleri_uygula() == 0
