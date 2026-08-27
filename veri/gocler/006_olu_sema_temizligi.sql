-- Kapsam dışı kalan alanlar sökülür (sürüm 6)
--
-- Sınav sonrası işlemler kapsamdan çıkarıldığında bu tablo ve sütunlar
-- kullanımsız kaldı: hiçbir kod okumuyor, hiçbir ekran yazmıyor. Şemada
-- durmaları, ileride "bu alan doldurulur" sanılmasına yol açar.
--
--   ogrenci_talep                 -> yazılı talep kaydı (SP-07)
--   ogrenci.bep_mi / bep_notu     -> BEP değerlendirme notu (SP-14)
--   ogrenci.mezun_olamayan_mi     -> plana dâhil etme ölçütü (SP-07)
--   ogrenci.devamsizlik_tebligati_mi
--
-- İlgili mevzuat hükümleri yardım sayfasında bilgi olarak kalır; bunlar
-- e-Okul'da ve okul müdürlüğünce yürütülür.

DROP TABLE IF EXISTS ogrenci_talep;

DROP VIEW v_ogrenci;

ALTER TABLE ogrenci DROP COLUMN bep_mi;
ALTER TABLE ogrenci DROP COLUMN bep_notu;
ALTER TABLE ogrenci DROP COLUMN mezun_olamayan_mi;
ALTER TABLE ogrenci DROP COLUMN devamsizlik_tebligati_mi;

CREATE VIEW v_ogrenci AS SELECT * FROM ogrenci WHERE silindi_mi = 0;
