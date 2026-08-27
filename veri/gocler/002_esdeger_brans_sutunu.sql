-- Eşdeğer branşlar ayrı sütuna taşınır (sürüm 2)
--
-- Birleşik derslerde (ör. "Görsel Sanatlar/Müzik") komisyon iki alandan
-- kurulabilir. Bu alanlar önce `ders.brans` içinde " / " ile birleştirilerek
-- saklanıyordu. Ancak e-Okul branş adlarının kendisinde eğik çizgi
-- bulunabiliyor — "Kimya / Kimya Teknolojisi" tek bir branştır. Ayırıcıyla
-- saklamak bu adı iki sahte branşa bölüyor ve o branştaki öğretmenler
-- görünmez oluyordu.
--
-- Artık `ders.brans` yalnız asıl alanı, `ders.esdeger_branslar` ise ek
-- alanları JSON dizisi olarak tutar. Ayırıcı yok, ad bozulmuyor.

ALTER TABLE ders ADD COLUMN esdeger_branslar TEXT NOT NULL DEFAULT '[]';

DROP VIEW v_ders;
CREATE VIEW v_ders AS SELECT * FROM ders WHERE silindi_mi = 0;
