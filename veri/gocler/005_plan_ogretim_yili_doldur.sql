-- Öğretim yılı boş kalan planlar doldurulur (sürüm 5)
--
-- 004 numaralı göç `plan.ogretim_yili` sütununu boş varsayılanla ekledi.
-- Daha önce kaydedilmiş planlarda bu alan boş kaldığı için görev sayacı
-- raporu öğretim yılına göre süzdüğünde hiçbir satır bulamıyordu. Mevcut
-- kayıtlar kurum ayarındaki öğretim yılıyla doldurulur.

UPDATE plan
   SET ogretim_yili = COALESCE(
        (SELECT deger FROM kurum_ayari WHERE anahtar = 'ogretim_yili'), '')
 WHERE ogretim_yili = '';
