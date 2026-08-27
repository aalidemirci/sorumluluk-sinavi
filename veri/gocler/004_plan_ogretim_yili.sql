-- Plan öğretim yılına bağlanır (sürüm 4)
--
-- Bir öğretim yılında üç sınav dönemi vardır (P1, P2, P3). Görev yükünün
-- dengelenmesi için önceki dönemlerde kimin kaç görev aldığı bilinmelidir:
-- P2 planlanırken P1'de çok görev almış öğretmen geri plana düşmelidir.
-- Sayaçların doğru dönemde toplanabilmesi için plan, üretildiği öğretim
-- yılını taşır.

ALTER TABLE plan ADD COLUMN ogretim_yili TEXT NOT NULL DEFAULT '';

DROP VIEW v_plan;
CREATE VIEW v_plan AS SELECT * FROM plan WHERE silindi_mi = 0;

-- Öğretim yılı ve döneme göre kişi başı görev sayacı.
DROP VIEW v_gorev_sayaci;
CREATE VIEW v_gorev_sayaci AS
    SELECT p.id            AS personel_id,
           p.ad            AS ad,
           p.brans         AS brans,
           p.unvan         AS unvan,
           pl.ogretim_yili AS ogretim_yili,
           pl.pencere_kodu AS pencere_kodu,
           SUM(CASE WHEN g.rol = 'komisyon_uyesi' THEN 1 ELSE 0 END) AS komisyon_sayisi,
           SUM(CASE WHEN g.rol = 'gozcu'          THEN 1 ELSE 0 END) AS gozcu_sayisi
    FROM personel p
    JOIN gorevlendirme g ON g.personel_id = p.id AND g.silindi_mi = 0
    JOIN oturum o ON o.id = g.oturum_id AND o.silindi_mi = 0
    JOIN plan pl ON pl.id = o.plan_id AND pl.silindi_mi = 0
    WHERE p.silindi_mi = 0
    GROUP BY p.id, p.ad, p.brans, p.unvan, pl.ogretim_yili, pl.pencere_kodu;

CREATE INDEX ix_plan_yil ON plan(ogretim_yili, pencere_kodu);
