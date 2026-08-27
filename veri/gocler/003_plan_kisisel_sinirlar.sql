-- Kişisel günlük sınırlar planla birlikte saklanır (sürüm 3)
--
-- Pencereye sığmayan öğrencinin günlük sınav sınırı plan üretilirken gereken
-- en düşük değere çıkarılır. Bu karar planın parçasıdır: saklanmazsa
-- kaydedilmiş plan yeniden açıldığında varsayılan sınırla doğrulanır ve
-- gerçekte kurallara uyan plan SP-11 ihlalleriyle dolu görünür.

ALTER TABLE plan ADD COLUMN kisisel_sinirlar_json TEXT NOT NULL DEFAULT '{}';

DROP VIEW v_plan;
CREATE VIEW v_plan AS SELECT * FROM plan WHERE silindi_mi = 0;
