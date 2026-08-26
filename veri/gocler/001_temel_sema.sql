-- Sorumluluk Sınavı — taban şema (sürüm 1)
--
-- Kapsam: e-Okul içe aktarma, kurum bilgileri, sınav planlama, görevlendirme,
-- evrak üretimi ve evrak teslim takibi. Sınav sonrası işlemler (sonuç, puan,
-- itiraz, telafi, diploma, disiplin) e-Okul'da yürütülür, burada tutulmaz.
--
-- Kurallar:
--   * Kullanıcı verisi silinmez, `silindi_mi` ile yumuşak silinir; uygulama
--     okumaları `v_*` görünümlerinden yapılır.
--   * Türkçe büyük/küçük harf eşleşmesi SQLite collation'ıyla yapılamaz;
--     eşleştirme anahtarları (`*_anahtari`) Python'da üretilip saklanır.
--   * Parasal alan yoktur. Ek ders ücreti MYS'de hesaplanır; burada yalnız
--     görev sayacı tutulur.

PRAGMA foreign_keys = ON;


-- ============================================================ kurum ve dönem

CREATE TABLE kurum_ayari (
    anahtar        TEXT PRIMARY KEY,
    deger          TEXT NOT NULL,
    guncellendi_at TEXT NOT NULL
);


-- =================================================================== personel

CREATE TABLE brans_havuzu (
    id             INTEGER PRIMARY KEY,
    ad             TEXT NOT NULL,
    ad_anahtari    TEXT NOT NULL UNIQUE,
    kaynak         TEXT NOT NULL CHECK(kaynak IN ('personel_raporu','manuel_ilce_mem')),
    aktif_mi       INTEGER NOT NULL DEFAULT 1,
    olusturuldu_at TEXT NOT NULL,
    guncellendi_at TEXT NOT NULL
);

CREATE TABLE personel (
    id                 INTEGER PRIMARY KEY,
    ad                 TEXT NOT NULL,
    ad_anahtari        TEXT NOT NULL,
    kurum_sicil_no     TEXT,
    brans              TEXT NOT NULL,
    unvan              TEXT NOT NULL,
    personel_tipi      TEXT NOT NULL DEFAULT 'kadrolu'
                       CHECK(personel_tipi IN ('kadrolu','sozlesmeli','ucretli','yonetici','diger')),
    kadro_durumu       TEXT NOT NULL DEFAULT '',
    aktif_mi           INTEGER NOT NULL DEFAULT 1,
    kaynak_aktarim_id  INTEGER REFERENCES ice_aktarim(id),
    silindi_mi         INTEGER NOT NULL DEFAULT 0
);
CREATE UNIQUE INDEX ux_personel_ad ON personel(ad_anahtari) WHERE silindi_mi = 0;
CREATE UNIQUE INDEX ux_personel_sicil ON personel(kurum_sicil_no)
    WHERE kurum_sicil_no IS NOT NULL AND silindi_mi = 0;
CREATE INDEX ix_personel_aktif ON personel(aktif_mi, silindi_mi);


-- ===================================================== salon, ders, öğrenci

CREATE TABLE salon (
    id         INTEGER PRIMARY KEY,
    ad         TEXT NOT NULL,
    ad_anahtari TEXT NOT NULL UNIQUE,
    kapasite   INTEGER NOT NULL CHECK(kapasite > 0),
    aktif_mi   INTEGER NOT NULL DEFAULT 1,
    silindi_mi INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE ders (
    id             INTEGER PRIMARY KEY,
    ad             TEXT NOT NULL,
    ad_anahtari    TEXT NOT NULL UNIQUE,
    brans          TEXT,
    -- OKY md.58/2-e: Türk dili ve edebiyatı ile yabancı dil dersleri yazılı ve
    -- uygulamalı olmak üzere iki aşamada yapılır.
    iki_asamali_mi INTEGER NOT NULL DEFAULT 0,
    yabanci_dil_mi INTEGER NOT NULL DEFAULT 0,
    silindi_mi     INTEGER NOT NULL DEFAULT 0
);

-- Ders/branş eşleme kararlarının sürüm geçmişi; hangi karara dayanıldığı
-- denetimde sorulabilir.
CREATE TABLE ders_brans (
    id              INTEGER PRIMARY KEY,
    ders_id         INTEGER NOT NULL REFERENCES ders(id),
    brans           TEXT NOT NULL,
    surum           INTEGER NOT NULL,
    karar_metni     TEXT NOT NULL,
    etkin_baslangic TEXT NOT NULL,
    UNIQUE(ders_id, surum)
);

CREATE TABLE ogrenci (
    id                       INTEGER PRIMARY KEY,
    okul_no                  TEXT NOT NULL,
    ad_soyad                 TEXT NOT NULL,
    sube                     TEXT NOT NULL,
    sinif_duzeyi             INTEGER NOT NULL,
    -- SP-14: BEP'li öğrenci için değerlendirme notu açılır.
    bep_mi                   INTEGER NOT NULL DEFAULT 0,
    bep_notu                 TEXT NOT NULL DEFAULT '',
    -- OKY md.58/2-d: bu iki durumdaki öğrenciler ancak yazılı talepleriyle
    -- plana dâhil edilir.
    mezun_olamayan_mi        INTEGER NOT NULL DEFAULT 0,
    devamsizlik_tebligati_mi INTEGER NOT NULL DEFAULT 0,
    silindi_mi               INTEGER NOT NULL DEFAULT 0,
    UNIQUE(okul_no, sube)
);
CREATE INDEX ix_ogrenci_sube ON ogrenci(sube);

CREATE TABLE sorumluluk_kaydi (
    id             INTEGER PRIMARY KEY,
    ogrenci_id     INTEGER NOT NULL REFERENCES ogrenci(id),
    ders_id        INTEGER NOT NULL REFERENCES ders(id),
    duzey          INTEGER NOT NULL,
    -- OKY md.58/1 son cümle: nakil/geçiş kaynaklı dersler 3/6 sayacına girmez.
    kaynak         TEXT NOT NULL CHECK(kaynak IN ('basarisizlik','nakil_gecis')),
    durum          TEXT NOT NULL DEFAULT 'aktif' CHECK(durum IN ('aktif','pasif_aktarim')),
    ice_aktarim_id INTEGER REFERENCES ice_aktarim(id),
    silindi_mi     INTEGER NOT NULL DEFAULT 0,
    UNIQUE(ogrenci_id, ders_id, duzey, kaynak)
);
CREATE INDEX ix_sorumluluk_ders ON sorumluluk_kaydi(ders_id, durum);
CREATE INDEX ix_sorumluluk_ogrenci ON sorumluluk_kaydi(ogrenci_id, durum);


-- ============================================================= içe aktarma

CREATE TABLE ice_aktarim (
    id             INTEGER PRIMARY KEY,
    tur            TEXT NOT NULL CHECK(tur IN ('sorumluluk','personel')),
    dosya_adi      TEXT NOT NULL,
    sha256         TEXT NOT NULL,
    durum          TEXT NOT NULL DEFAULT 'onay_bekliyor'
                   CHECK(durum IN ('onay_bekliyor','onaylandi','vazgecildi')),
    eklenen        INTEGER NOT NULL DEFAULT 0,
    guncellenen    INTEGER NOT NULL DEFAULT 0,
    cikan          INTEGER NOT NULL DEFAULT 0,
    degismedi      INTEGER NOT NULL DEFAULT 0,
    olusturuldu_at TEXT NOT NULL,
    onaylandi_at   TEXT,
    UNIQUE(tur, sha256)
);

CREATE TABLE sorumluluk_aktarim_satiri (
    id             INTEGER PRIMARY KEY,
    ice_aktarim_id INTEGER NOT NULL REFERENCES ice_aktarim(id) ON DELETE CASCADE,
    satir_no       INTEGER NOT NULL,
    okul_no        TEXT NOT NULL,
    ad_soyad       TEXT NOT NULL,
    sube           TEXT NOT NULL,
    duzey          INTEGER NOT NULL,
    ders_adi       TEXT NOT NULL,
    kaynak         TEXT NOT NULL DEFAULT 'basarisizlik',
    eylem          TEXT NOT NULL CHECK(eylem IN ('eklenecek','degismedi','guncellenecek'))
);
CREATE INDEX ix_sorumluluk_satiri ON sorumluluk_aktarim_satiri(ice_aktarim_id, satir_no);

CREATE TABLE personel_aktarim_satiri (
    id             INTEGER PRIMARY KEY,
    ice_aktarim_id INTEGER NOT NULL REFERENCES ice_aktarim(id) ON DELETE CASCADE,
    satir_no       INTEGER NOT NULL,
    ad             TEXT NOT NULL,
    unvan          TEXT NOT NULL,
    kadro_durumu   TEXT NOT NULL,
    brans          TEXT NOT NULL,
    personel_tipi  TEXT NOT NULL,
    kurum_sicil_no TEXT,
    eylem          TEXT NOT NULL CHECK(eylem IN ('eklenecek','degismedi','guncellenecek'))
);
CREATE INDEX ix_personel_satiri ON personel_aktarim_satiri(ice_aktarim_id, satir_no);


-- ================================================================ planlama

CREATE TABLE plan (
    id                INTEGER PRIMARY KEY,
    pencere_kodu      TEXT NOT NULL CHECK(pencere_kodu IN ('P1','P2','P3')),
    -- Plan üretilirken kullanıcıya sorulan parametrelerin tamamı; planın
    -- neden bu biçimde çıktığı sonradan açıklanabilsin diye saklanır.
    parametreler_json TEXT NOT NULL,
    durum             TEXT NOT NULL DEFAULT 'taslak' CHECK(durum IN ('taslak','kesin')),
    mudur_onay_no     TEXT,
    uretildi_at       TEXT NOT NULL,
    kesinlesti_at     TEXT,
    silindi_mi        INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX ix_plan_pencere ON plan(pencere_kodu, durum, silindi_mi);

CREATE TABLE oturum (
    id                  INTEGER PRIMARY KEY,
    plan_id             INTEGER NOT NULL REFERENCES plan(id),
    anahtar             TEXT NOT NULL,
    ders_id             INTEGER NOT NULL REFERENCES ders(id),
    duzey_kumesi        TEXT NOT NULL,          -- "9" ya da "9,10"
    oturum_turu         TEXT NOT NULL CHECK(oturum_turu IN ('yazili','uygulama')),
    -- İki aşamalı dersin yazılı ve uygulama oturumlarını birbirine bağlar.
    birim_anahtari      TEXT NOT NULL DEFAULT '',
    tarih               TEXT NOT NULL,
    saat                TEXT NOT NULL,
    sure                INTEGER NOT NULL CHECK(sure > 0),
    hafta_sonu_gerekcesi TEXT NOT NULL DEFAULT '',
    kilitli_mi          INTEGER NOT NULL DEFAULT 0,
    silindi_mi          INTEGER NOT NULL DEFAULT 0,
    UNIQUE(plan_id, anahtar)
);
CREATE INDEX ix_oturum_zaman ON oturum(plan_id, tarih, saat);
CREATE INDEX ix_oturum_ders ON oturum(ders_id);

CREATE TABLE oturum_salon (
    id        INTEGER PRIMARY KEY,
    oturum_id INTEGER NOT NULL REFERENCES oturum(id) ON DELETE CASCADE,
    salon_id  INTEGER NOT NULL REFERENCES salon(id),
    sira      INTEGER NOT NULL,
    UNIQUE(oturum_id, salon_id)
);
CREATE INDEX ix_oturum_salon_salon ON oturum_salon(salon_id);

CREATE TABLE oturum_ogrenci (
    id         INTEGER PRIMARY KEY,
    oturum_id  INTEGER NOT NULL REFERENCES oturum(id) ON DELETE CASCADE,
    ogrenci_id INTEGER NOT NULL REFERENCES ogrenci(id),
    salon_id   INTEGER REFERENCES salon(id),
    sira       INTEGER NOT NULL,
    UNIQUE(oturum_id, ogrenci_id)
);
CREATE INDEX ix_oturum_ogrenci_ogrenci ON oturum_ogrenci(ogrenci_id);

CREATE TABLE gorevlendirme (
    id                    INTEGER PRIMARY KEY,
    oturum_id             INTEGER NOT NULL REFERENCES oturum(id) ON DELETE CASCADE,
    personel_id           INTEGER NOT NULL REFERENCES personel(id),
    rol                   TEXT NOT NULL CHECK(rol IN ('komisyon_uyesi','gozcu')),
    -- Karar md.12/2-c: yöneticilere sınav görevi için ücret ödenmez.
    -- Burada yalnız sayaç etiketidir; tutar hesaplanmaz.
    ucretlendirilebilir_mi INTEGER NOT NULL DEFAULT 1,
    gerekce               TEXT NOT NULL DEFAULT '',
    kilitli_mi            INTEGER NOT NULL DEFAULT 0,
    silindi_mi            INTEGER NOT NULL DEFAULT 0,
    -- Karar md.12/2-b: aynı kişi bir sınavda hem komisyon üyesi hem gözcü olamaz.
    UNIQUE(oturum_id, personel_id)
);
CREATE INDEX ix_gorev_personel ON gorevlendirme(personel_id, silindi_mi);
CREATE INDEX ix_gorev_oturum ON gorevlendirme(oturum_id, silindi_mi);

-- SP-07 / OKY md.58/2-d: mezun olamayan 12. sınıf ve devamsızlık tebligatı
-- yapılan öğrenciler yazılı talepleriyle plana dâhil edilir.
CREATE TABLE ogrenci_talep (
    id              INTEGER PRIMARY KEY,
    ogrenci_id      INTEGER NOT NULL REFERENCES ogrenci(id),
    ders_id         INTEGER REFERENCES ders(id),
    talep_tarihi    TEXT NOT NULL,
    belge_referansi TEXT NOT NULL,
    olusturuldu_at  TEXT NOT NULL,
    UNIQUE(ogrenci_id, ders_id)
);


-- ================================================== evrak ve teslim takibi

CREATE TABLE belge_surumu (
    id               INTEGER PRIMARY KEY,
    tur              TEXT NOT NULL,
    kayit_anahtari   TEXT NOT NULL,
    surum            INTEGER NOT NULL,
    sha256           TEXT NOT NULL,
    kaynak_sha256    TEXT NOT NULL,
    onceki_surum_id  INTEGER REFERENCES belge_surumu(id),
    onaylandi_mi     INTEGER NOT NULL DEFAULT 0,
    degisiklik_foyu  TEXT,
    olusturma_tarihi TEXT NOT NULL,
    UNIQUE(tur, kayit_anahtari, surum)
);

CREATE TABLE evrak_kaydi (
    id               INTEGER PRIMARY KEY,
    tur              TEXT NOT NULL,
    kayit_anahtari   TEXT NOT NULL,
    dosya_yolu       TEXT NOT NULL,
    belge_surumu_id  INTEGER REFERENCES belge_surumu(id),
    uretildi_at      TEXT NOT NULL
);

-- Sınav evrakının komisyondan teslim alınmasının izlenmesi.
CREATE TABLE evrak_teslim (
    id                      INTEGER PRIMARY KEY,
    oturum_id               INTEGER NOT NULL REFERENCES oturum(id) ON DELETE CASCADE,
    evrak_turu              TEXT NOT NULL CHECK(evrak_turu IN (
                                'sinav_kagitlari','komisyon_tutanagi','yoklama_listesi',
                                'kagit_sarf_tutanagi','kopya_tutanagi','diger')),
    adet                    INTEGER,
    teslim_eden_personel_id INTEGER REFERENCES personel(id),
    teslim_alan_personel_id INTEGER REFERENCES personel(id),
    teslim_at               TEXT,
    aciklama                TEXT NOT NULL DEFAULT '',
    silindi_mi              INTEGER NOT NULL DEFAULT 0,
    UNIQUE(oturum_id, evrak_turu)
);
CREATE INDEX ix_teslim_oturum ON evrak_teslim(oturum_id, silindi_mi);


-- ====================================================== kurallar ve denetim

CREATE TABLE kural_karari (
    id             INTEGER PRIMARY KEY,
    kural_kimligi  TEXT NOT NULL,
    kayit_turu     TEXT NOT NULL,
    kayit_id       INTEGER NOT NULL DEFAULT 0,
    ciddiyet       TEXT NOT NULL CHECK(ciddiyet IN ('ENGEL','UYARI','BILGI')),
    aciklama       TEXT NOT NULL,
    dayanak_metni  TEXT NOT NULL,
    olusturuldu_at TEXT NOT NULL,
    giderildi_at   TEXT
);
CREATE INDEX ix_kural_acik ON kural_karari(kayit_turu, giderildi_at);

CREATE TABLE denetim_izi (
    id          INTEGER PRIMARY KEY,
    tablo       TEXT NOT NULL,
    kayit_id    INTEGER NOT NULL,
    islem       TEXT NOT NULL,
    ayrinti     TEXT,
    onceki_hash TEXT NOT NULL,
    hash        TEXT NOT NULL,
    zaman       TEXT NOT NULL
);

CREATE TRIGGER denetim_izi_degistirilemez BEFORE UPDATE ON denetim_izi BEGIN
    SELECT RAISE(ABORT, 'Denetim izi değiştirilemez.');
END;
CREATE TRIGGER denetim_izi_silinemez BEFORE DELETE ON denetim_izi BEGIN
    SELECT RAISE(ABORT, 'Denetim izi silinemez.');
END;


-- ================================================================ görünümler
-- Uygulama okumaları yumuşak silinmiş kayıtları görmez.

CREATE VIEW v_personel      AS SELECT * FROM personel      WHERE silindi_mi = 0;
CREATE VIEW v_salon         AS SELECT * FROM salon         WHERE silindi_mi = 0;
CREATE VIEW v_ders          AS SELECT * FROM ders          WHERE silindi_mi = 0;
CREATE VIEW v_ogrenci       AS SELECT * FROM ogrenci       WHERE silindi_mi = 0;
CREATE VIEW v_plan          AS SELECT * FROM plan          WHERE silindi_mi = 0;
CREATE VIEW v_oturum        AS SELECT * FROM oturum        WHERE silindi_mi = 0;
CREATE VIEW v_gorevlendirme AS SELECT * FROM gorevlendirme WHERE silindi_mi = 0;
CREATE VIEW v_evrak_teslim  AS SELECT * FROM evrak_teslim  WHERE silindi_mi = 0;
CREATE VIEW v_brans_havuzu  AS SELECT * FROM brans_havuzu  WHERE aktif_mi = 1;

CREATE VIEW v_sorumluluk_kaydi AS
    SELECT * FROM sorumluluk_kaydi WHERE silindi_mi = 0;

CREATE VIEW v_oturum_salon AS
    SELECT os.* FROM oturum_salon os
    JOIN oturum o ON o.id = os.oturum_id AND o.silindi_mi = 0;

CREATE VIEW v_oturum_ogrenci AS
    SELECT oo.* FROM oturum_ogrenci oo
    JOIN oturum o ON o.id = oo.oturum_id AND o.silindi_mi = 0;

-- Görev sayaçları: Karar md.12/2-a'daki 12 komisyon / 15 gözcülük sınırının
-- izlenmesi için. Tutar hesaplanmaz.
CREATE VIEW v_gorev_sayaci AS
    SELECT p.id            AS personel_id,
           p.ad            AS ad,
           p.brans         AS brans,
           p.unvan         AS unvan,
           SUM(CASE WHEN g.rol = 'komisyon_uyesi' THEN 1 ELSE 0 END) AS komisyon_sayisi,
           SUM(CASE WHEN g.rol = 'gozcu'          THEN 1 ELSE 0 END) AS gozcu_sayisi
    FROM personel p
    LEFT JOIN gorevlendirme g ON g.personel_id = p.id AND g.silindi_mi = 0
    WHERE p.silindi_mi = 0 AND p.aktif_mi = 1
    GROUP BY p.id, p.ad, p.brans, p.unvan;
