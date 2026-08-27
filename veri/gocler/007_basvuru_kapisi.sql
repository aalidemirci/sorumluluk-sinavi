-- Başvuru kapısı — OKY md.58/2-d (sürüm 7)
--
-- 006 numaralı göç `ogrenci_talep` tablosunu ve iki öğrenci bayrağını
-- SÖKMÜŞTÜ. Gerekçe doğruydu: hiçbir kod okumuyordu, ölü şemaydı. Bu göç
-- onları geri getirir, çünkü bu kez arkalarında çalışan kod vardır.
--
-- OKY md.58/2-d (Ek:RG-8/9/2023-32303): "Okuldan mezun olamayan 12 nci sınıf
-- öğrencileri ile devamsızlık tebligatı yapıldığı hâlde okula veya sınavlara
-- katılımları sağlanamayan öğrenciler, sorumluluk sınavına girmek istediklerine
-- dair yazılı taleplerini kayıtlı oldukları okul müdürlüğüne sınav tarihinden
-- 5 iş günü öncesine kadar bildirmeleri hâlinde sorumluluk sınavı planına
-- dâhil edilir."
--
-- Başvuru OTURUMA değil PENCEREYE bağlanır: mevzuat başvuruyu plandan önce
-- ister, oturumlar ise plandan sonra doğar. Oturuma bağlamak mevzuatın
-- sırasını tersine çevirirdi.
--
-- Adlandırma: `cekirdek/talep.py` bu projede yük/talep analizi demektir.
-- Öğrenci başvurusu için "basvuru" kullanılır, "talep" değil.

-- Bayraklar öğrenciye aittir ve öğretim yılı boyunca kalıcıdır; başvuru ise
-- her pencerede yenilenir.
ALTER TABLE ogrenci ADD COLUMN mezun_olamayan_mi        INTEGER NOT NULL DEFAULT 0;
ALTER TABLE ogrenci ADD COLUMN devamsizlik_tebligati_mi INTEGER NOT NULL DEFAULT 0;

DROP VIEW v_ogrenci;
CREATE VIEW v_ogrenci AS SELECT * FROM ogrenci WHERE silindi_mi = 0;

-- Duyuru, kapının hukuki tetikleyicisidir: yayımlanmadan başvuru alınamaz.
-- Belge referansı ve yayım yeri, "duyurdum" iddiasının ispatıdır.
CREATE TABLE pencere_duyurusu (
    id               INTEGER PRIMARY KEY,
    ogretim_yili     TEXT NOT NULL,
    pencere_kodu     TEXT NOT NULL CHECK(pencere_kodu IN ('P1','P2','P3')),
    duyuru_tarihi    TEXT NOT NULL,
    basvuru_son_gunu TEXT NOT NULL,
    duyuru_referansi TEXT NOT NULL,
    yayim_yeri       TEXT NOT NULL DEFAULT '',
    olusturuldu_at   TEXT NOT NULL,
    silindi_mi       INTEGER NOT NULL DEFAULT 0,
    UNIQUE(ogretim_yili, pencere_kodu)
);

-- `durum='basvurmadi'` bilinçli bir karardır, kayıt yokluğu değildir:
-- "başvurmadı" ile "henüz bakılmadı" ayrı hâllerdir ve tutanakta ayrı görünür.
CREATE TABLE basvuru (
    id              INTEGER PRIMARY KEY,
    ogrenci_id      INTEGER NOT NULL REFERENCES ogrenci(id),
    ogretim_yili    TEXT NOT NULL,
    pencere_kodu    TEXT NOT NULL CHECK(pencere_kodu IN ('P1','P2','P3')),
    durum           TEXT NOT NULL CHECK(durum IN ('basvurdu','basvurmadi')),
    basvuru_tarihi  TEXT,
    belge_referansi TEXT NOT NULL DEFAULT '',
    -- Okulun koyduğu son günü kaçıran ama mevzuattaki 5 iş günü şartını
    -- sağlayan başvuru reddedilemez; müdür onayıyla plana eklenir.
    gec_basvuru_mu  INTEGER NOT NULL DEFAULT 0,
    mudur_onay_no   TEXT,
    olusturuldu_at  TEXT NOT NULL,
    silindi_mi      INTEGER NOT NULL DEFAULT 0,
    UNIQUE(ogrenci_id, ogretim_yili, pencere_kodu),
    CHECK(durum = 'basvurmadi' OR basvuru_tarihi IS NOT NULL),
    CHECK(gec_basvuru_mu = 0 OR mudur_onay_no IS NOT NULL)
);
CREATE INDEX ix_basvuru_pencere ON basvuru(ogretim_yili, pencere_kodu, durum);

CREATE VIEW v_pencere_duyurusu AS
    SELECT * FROM pencere_duyurusu WHERE silindi_mi = 0;
CREATE VIEW v_basvuru AS
    SELECT * FROM basvuru WHERE silindi_mi = 0;
