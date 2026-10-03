-- Kullanılmayan şema nesnelerinin kaldırılması (sürüm 9)
--
-- kural_karari: kural ihlallerini kalıcı tutmak için iskelet şemada (001)
-- açılmıştı. Program ihlalleri her doğrulamada yeniden hesaplar; hiçbir
-- sürüm bu tabloya yazmadı (git geçmişinde tek geçişi 001'dir), her
-- kurulumda boştur.
--
-- v_gorev_sayaci: görevleri bütün planlar üzerinden sayıyordu; taslaklar ve
-- yerine yenisi kaydedilmiş planlar dâhil. 0.6.0'dan beri sayaçlar yalnız
-- geçerli planları sayar (veri/hizmet/plan_kayitlari.py, etkin_planlar).
-- Görünüm kalsaydı, onu kullanan ilk kod 0.6.0'da giderilen çifte sayımı
-- geri getirirdi.

DROP VIEW IF EXISTS v_gorev_sayaci;
DROP INDEX IF EXISTS ix_kural_acik;
DROP TABLE IF EXISTS kural_karari;
