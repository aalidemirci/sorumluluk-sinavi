"""SQLite bağlantısı, göç yönetimi ve değiştirilemez denetim izi."""

from __future__ import annotations

import hashlib
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ISTANBUL = ZoneInfo("Europe/Istanbul")

# SQLite başlığındaki application_id alanına yazılan imza. Bir veritabanı
# dosyasının bu uygulamaya ait olup olmadığı bununla anlaşılır; başka bir
# uygulamanın (ör. önceki sürümün) dosyası yanlışlıkla açılıp göç sayacı
# uyuştuğu için "şema kurulu" sanılmaz.
UYGULAMA_KIMLIGI = 0x534F5250  # "SORP"

# Başka bir işlem yazarken kilit beklemesi; süresiz asılı kalmayı önler.
MESGUL_ZAMAN_ASIMI_SN = 15.0


def simdi() -> str:
    return datetime.now(ISTANBUL).isoformat(timespec="seconds")


class VeritabaniUyumsuz(RuntimeError):
    """Dosya bu uygulamaya ait değil ya da şeması tanınmıyor."""


class Veritabani:
    def __init__(self, yol: Path):
        self.yol = Path(yol)
        self.yol.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def baglan(self):
        """İşlem sınırı olan bağlantı üretir.

        Blok hatasız biterse commit, hata alırsa rollback edilir; her iki
        durumda da bağlantı kapatılır. Eski sürümde kapatma yoktu ve
        bağlantılar çöp toplayıcıya bırakılmıştı.
        """
        baglanti = sqlite3.connect(self.yol, timeout=MESGUL_ZAMAN_ASIMI_SN)
        baglanti.row_factory = sqlite3.Row
        baglanti.execute("PRAGMA foreign_keys=ON")
        baglanti.execute("PRAGMA journal_mode=WAL")
        baglanti.execute(f"PRAGMA busy_timeout={int(MESGUL_ZAMAN_ASIMI_SN * 1000)}")
        try:
            with baglanti:
                yield baglanti
        finally:
            baglanti.close()

    # ---------------------------------------------------------------- göçler

    def surum(self) -> int:
        with self.baglan() as b:
            return int(b.execute("PRAGMA user_version").fetchone()[0])

    def _kimlik_ve_tablo_sayisi(self) -> tuple[int, int]:
        with self.baglan() as b:
            kimlik = int(b.execute("PRAGMA application_id").fetchone()[0])
            tablo = int(b.execute(
                "SELECT count(*) FROM sqlite_master WHERE type='table'"
                " AND name NOT LIKE 'sqlite_%'").fetchone()[0])
        return kimlik, tablo

    def uyumu_denetle(self) -> None:
        """Dosya başka bir uygulamaya aitse anlaşılır bir hata verir.

        Önceki sürümlerin veritabanı aynı klasörde durabilir. Göç sayacı
        uyuştuğu için şema kurulu sanılırsa uygulama sonradan "no such table"
        ile çöker; bunun yerine burada durdurup ne yapılacağını söyleriz.
        """
        if not self.yol.exists() or not self.yol.stat().st_size:
            return
        kimlik, tablo_sayisi = self._kimlik_ve_tablo_sayisi()
        if tablo_sayisi and kimlik != UYGULAMA_KIMLIGI:
            raise VeritabaniUyumsuz(
                f"{self.yol} dosyası bu uygulamaya ait değil.\n\n"
                "Aynı klasörde başka bir sürümün veritabanı bulunuyor olabilir. "
                "Dosyayı başka bir yere taşıyın ya da uygulamayı "
                "SORUMLULUK_VERI_KLASORU ortam değişkeniyle farklı bir klasöre "
                "yönlendirin. Mevcut dosya silinmedi.")

    def gocleri_uygula(self, goc_klasoru: Path | None = None) -> int:
        """Bekleyen göçleri sırayla uygular ve uygulanan göç sayısını döndürür."""
        klasor = goc_klasoru or Path(__file__).with_name("gocler")
        self.uyumu_denetle()
        mevcut = self.surum()
        uygulanan = 0
        for dosya in sorted(klasor.glob("[0-9][0-9][0-9]_*.sql")):
            hedef = int(dosya.name[:3])
            if hedef <= mevcut:
                continue
            self._yedekle(f"goc-{hedef:03d}-oncesi")
            sql = dosya.read_text(encoding="utf-8")
            baglanti = sqlite3.connect(self.yol, timeout=MESGUL_ZAMAN_ASIMI_SN)
            try:
                # executescript kendi COMMIT'ini attığı için göç ve sürüm
                # damgası tek betikte, açık BEGIN/COMMIT ile uygulanır.
                baglanti.executescript(
                    f"BEGIN;\n{sql}\n"
                    f"PRAGMA user_version={hedef};\n"
                    f"PRAGMA application_id={UYGULAMA_KIMLIGI};\n"
                    "COMMIT;")
            except Exception:
                baglanti.rollback()
                raise
            finally:
                baglanti.close()
            mevcut = hedef
            uygulanan += 1
        return uygulanan

    def _yedekle(self, etiket: str) -> Path | None:
        """Göç öncesi tam yedek alır.

        `shutil.copy2` ile yalnız .db kopyalamak WAL kipinde eksik yedek
        üretir: henüz checkpoint edilmemiş yazmalar -wal dosyasındadır.
        SQLite'ın kendi `backup` API'si WAL içeriğini de kapsar.
        """
        if not self.yol.exists() or not self.yol.stat().st_size:
            return None
        # İlk kurulumda dosya WAL kipi açıldığı için boş değildir ama içinde
        # kullanıcı verisi yoktur; anlamsız bir yedek dosyası bırakmayalım.
        with self.baglan() as b:
            tablo_sayisi = b.execute(
                "SELECT count(*) FROM sqlite_master WHERE type='table'"
                " AND name NOT LIKE 'sqlite_%'").fetchone()[0]
        if not tablo_sayisi:
            return None
        damga = datetime.now(ISTANBUL).strftime("%Y%m%d_%H%M%S")
        hedef = self.yol.with_suffix(f".db.{etiket}-{damga}.yedek")
        kaynak = sqlite3.connect(self.yol, timeout=MESGUL_ZAMAN_ASIMI_SN)
        kopya = sqlite3.connect(hedef)
        try:
            kaynak.backup(kopya)
        finally:
            kopya.close()
            kaynak.close()
        return hedef

    def yedek_al(self, hedef_klasor: Path) -> Path:
        """Kullanıcının istediği anda tam yedek alır (WAL dâhil)."""
        hedef_klasor = Path(hedef_klasor)
        hedef_klasor.mkdir(parents=True, exist_ok=True)
        damga = datetime.now(ISTANBUL).strftime("%Y%m%d_%H%M%S")
        hedef = hedef_klasor / f"sorumluluk-yedek-{damga}.db"
        kaynak = sqlite3.connect(self.yol, timeout=MESGUL_ZAMAN_ASIMI_SN)
        kopya = sqlite3.connect(hedef)
        try:
            kaynak.backup(kopya)
        finally:
            kopya.close()
            kaynak.close()
        return hedef

    # ----------------------------------------------------------- denetim izi

    def denetim_yaz(self, baglanti: sqlite3.Connection, tablo: str, kayit_id: int,
                    islem: str, ayrinti: str = "") -> None:
        """Zincirlenmiş özetle denetim kaydı ekler.

        Kişisel veri yazılmaz; yalnız tablo adı, kayıt kimliği ve işlem türü
        tutulur.
        """
        onceki = baglanti.execute("SELECT hash FROM denetim_izi ORDER BY id DESC LIMIT 1").fetchone()
        onceki_hash = onceki[0] if onceki else "0" * 64
        zaman = simdi()
        ozet = f"{onceki_hash}|{tablo}|{kayit_id}|{islem}|{ayrinti}|{zaman}"
        baglanti.execute(
            "INSERT INTO denetim_izi(tablo,kayit_id,islem,ayrinti,onceki_hash,hash,zaman)"
            " VALUES(?,?,?,?,?,?,?)",
            (tablo, kayit_id, islem, ayrinti or None, onceki_hash,
             hashlib.sha256(ozet.encode("utf-8")).hexdigest(), zaman),
        )

    def denetim_izi_saglam_mi(self) -> bool:
        """Zinciri baştan doğrular; bir kayıt değiştirilmişse False döner."""
        onceki_hash = "0" * 64
        with self.baglan() as b:
            for satir in b.execute(
                "SELECT tablo,kayit_id,islem,ayrinti,onceki_hash,hash,zaman FROM denetim_izi ORDER BY id"
            ):
                if satir["onceki_hash"] != onceki_hash:
                    return False
                ozet = (f"{onceki_hash}|{satir['tablo']}|{satir['kayit_id']}|{satir['islem']}"
                        f"|{satir['ayrinti'] or ''}|{satir['zaman']}")
                if hashlib.sha256(ozet.encode("utf-8")).hexdigest() != satir["hash"]:
                    return False
                onceki_hash = satir["hash"]
        return True
