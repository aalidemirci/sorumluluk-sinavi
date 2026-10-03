-- Tatil günleri, öğretmen müsaitliği, görevli değişikliği, tek ders sınavı (sürüm 8)
--
-- Tek göç dosyasında toplandı: her göç ayrı bir otomatik yedek alır; aynı
-- sürümle gelen yedi küçük değişiklik yedi yedek bırakırdı.


-- ------------------------------------------------------------ tatil günleri
-- Resmî tatil ve idari izin günleri. Plan bu günlere sınav koymaz; başvuru
-- (OKY md.58/2-d, 5 iş günü) ve evrak teslim süresi hesapları bu günleri iş
-- günü saymaz. Bayramlar her yıl kaydığı ve idari izin önceden bilinmediği
-- için liste koda gömülmez, kurum girer.

CREATE TABLE tatil_gunu (
    id         INTEGER PRIMARY KEY,
    tarih      TEXT NOT NULL,
    aciklama   TEXT NOT NULL DEFAULT '',
    silindi_mi INTEGER NOT NULL DEFAULT 0
);
CREATE UNIQUE INDEX ux_tatil_tarih ON tatil_gunu(tarih) WHERE silindi_mi = 0;
CREATE VIEW v_tatil_gunu AS SELECT * FROM tatil_gunu WHERE silindi_mi = 0;


-- ------------------------------------------------------ öğretmen müsaitliği
-- OKY md.58/2-ç: sınavlar dersleri aksatmayacak şekilde planlanır. Kayıt ya
-- haftalık tekrar eden bir gündür ya da bir tarih aralığıdır; saat yoksa
-- bütün gün. Açıklama alanına sağlık bilgisi yazılmaz (KVKK özel nitelikli
-- veri); arayüz bunu söyler.

CREATE TABLE personel_musaitlik (
    id             INTEGER PRIMARY KEY,
    personel_id    INTEGER NOT NULL REFERENCES personel(id),
    hafta_gunu     INTEGER CHECK(hafta_gunu BETWEEN 0 AND 6),
    bas_saat       TEXT,
    bit_saat       TEXT,
    bas_tarih      TEXT,
    bit_tarih      TEXT,
    aciklama       TEXT NOT NULL DEFAULT '',
    olusturuldu_at TEXT NOT NULL,
    silindi_mi     INTEGER NOT NULL DEFAULT 0,
    CHECK((hafta_gunu IS NULL) <> (bas_tarih IS NULL)),
    CHECK((bas_saat IS NULL) = (bit_saat IS NULL))
);
CREATE INDEX ix_musaitlik_personel ON personel_musaitlik(personel_id, silindi_mi);
CREATE VIEW v_personel_musaitlik AS SELECT * FROM personel_musaitlik WHERE silindi_mi = 0;


-- ------------------------------------------- başvuru işaretinin öğretim yılı
-- md.58/2-d işaretleri öğrenciye aittir ama devamsızlık tebligatı o yılın
-- durumudur. Eski sürümde işaret yıldan yıla sessizce taşınıyor, öğrenci
-- yeni yılda da başvurusuz plan dışı kalıyordu. İşaretin konduğu yıl
-- tutulur; yıl değişince program gözden geçirilmesini ister. Mevcut
-- işaretler bugünkü öğretim yılına yazılır ki göçle birlikte uyarı yağmasın.

ALTER TABLE ogrenci ADD COLUMN isaret_ogretim_yili TEXT NOT NULL DEFAULT '';
UPDATE ogrenci
   SET isaret_ogretim_yili = COALESCE(
        (SELECT deger FROM kurum_ayari WHERE anahtar = 'ogretim_yili'), '')
 WHERE mezun_olamayan_mi = 1 OR devamsizlik_tebligati_mi = 1;

DROP VIEW v_ogrenci;
CREATE VIEW v_ogrenci AS SELECT * FROM ogrenci WHERE silindi_mi = 0;


-- ------------------------------------------------------ gözcünün salonu
-- OKY md.58/2-b her salon için bir gözcü ister; hangi gözcünün hangi salonda
-- olduğu evrakta yazılır. Eski planlarda boş kalır.

ALTER TABLE gorevlendirme ADD COLUMN salon_id INTEGER REFERENCES salon(id);

DROP VIEW v_gorevlendirme;
CREATE VIEW v_gorevlendirme AS SELECT * FROM gorevlendirme WHERE silindi_mi = 0;


-- ------------------------------------------------------------- plan türü
-- OKY md.58/6: sorumluluk sınavı sonunda tek dersten başarısızlığı kalan son
-- sınıf öğrencisi için takip eden hafta içinde bir sınav daha yapılır. Bu
-- sınavın planı olağan planın yanında ayrı durur; pencere kodu bağlı olduğu
-- dönemi gösterir (bkz. kararlar/0010).

ALTER TABLE plan ADD COLUMN tur TEXT NOT NULL DEFAULT 'olagan'
    CHECK(tur IN ('olagan', 'tek_ders'));

DROP VIEW v_plan;
CREATE VIEW v_plan AS SELECT * FROM plan WHERE silindi_mi = 0;

-- Tek ders sınavına girecek öğrenci ve dersi; öğrenci başına tek kayıt.
CREATE TABLE tek_ders_secimi (
    id                  INTEGER PRIMARY KEY,
    ogretim_yili        TEXT NOT NULL,
    pencere_kodu        TEXT NOT NULL CHECK(pencere_kodu IN ('P1', 'P2', 'P3')),
    ogrenci_id          INTEGER NOT NULL REFERENCES ogrenci(id),
    sorumluluk_kaydi_id INTEGER NOT NULL REFERENCES sorumluluk_kaydi(id),
    olusturuldu_at      TEXT NOT NULL,
    silindi_mi          INTEGER NOT NULL DEFAULT 0
);
CREATE UNIQUE INDEX ux_tek_ders ON tek_ders_secimi(ogretim_yili, pencere_kodu, ogrenci_id)
    WHERE silindi_mi = 0;
CREATE VIEW v_tek_ders_secimi AS SELECT * FROM tek_ders_secimi WHERE silindi_mi = 0;


-- --------------------------------------------- kesin planda görevli değişikliği
-- Kesinleşmiş planda görevli ancak müdür onayıyla değiştirilir; her
-- değişiklik eski ve yeni kişiyle birlikte saklanır, evrakta listelenir.
-- Gerekçeye sağlık bilgisi yazılmaz.

CREATE TABLE gorevli_degisikligi (
    id               INTEGER PRIMARY KEY,
    gorevlendirme_id INTEGER NOT NULL REFERENCES gorevlendirme(id),
    eski_personel_id INTEGER NOT NULL REFERENCES personel(id),
    yeni_personel_id INTEGER NOT NULL REFERENCES personel(id),
    mudur_onay_no    TEXT NOT NULL,
    gerekce          TEXT NOT NULL,
    olusturuldu_at   TEXT NOT NULL
);
CREATE INDEX ix_degisiklik_gorev ON gorevli_degisikligi(gorevlendirme_id);
