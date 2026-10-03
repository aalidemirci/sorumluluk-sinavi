# 0014 — Günlük sınav sınırı: kısa takvim korunur, mevzuat ölçüsü gösterilir

**Durum:** Kabul — 03.10.2026

## Bağlam

ÖDY md.5/1-k: "Bir sınıfta bir günde yapılacak yazılı ve uygulamalı
sınavların sayısının ikiyi geçmemesi esastır. Ancak zorunlu hâllerde bir
sınav daha yapılabilir." (Aynı hüküm OKY md.45/1-g'de.)

Program gün sayısını öğrencilerin çoğunluğuna göre seçiyor (bir hafta → iki
hafta → gereken kadar), sığmayan öğrencinin günlük sınırını gereken en düşük
değere çıkarıyordu. Sınırın tavanı yoktu: 31 dersi olan bir öğrenci 10
günlük planda günde 4 sınava girebiliyor, doğrulayıcı da yükseltilmiş sınırı
esas aldığı için hiçbir uyarı vermiyordu. Ekrandaki günlük sınır 8'e kadar
seçilebiliyordu.

## Karar

Kullanıcı kararıyla (03.10.2026) kısa takvim tercihi korunur, mevzuat ölçüsü
her durumda gösterilir:

- Bir öğrencinin bir gündeki ikiyi aşan sınavı UYARI, üçü aşan sınavı ENGEL
  üretir (SP-11). Kullanıcının seçtiği daha sıkı sınır da ayrıca gösterilir.
- Kişisel sınır en çok üçe yükseltilir. Üç de yetmiyorsa o gün sayısı
  denenmez; program daha uzun takvime geçer, pencere yetmiyorsa hafta sonunu
  açmayı önerir.
- Ekrandaki günlük sınır 1–3 arasıdır.

## Gerekçe

Elenen seçenek ("mevzuat öncelikli"): gün sayısını herkesin günde ikiye
sığacağı biçimde seçmek. Bu, tek bir ağır yüklü öğrenci yüzünden bütün okulun
programını uzatır; kullanıcı kısa takvimi tercih etti. Seçilen yol bu tercihi
korurken "zorunlu hâl"i görünür kılar: ikiyi aşan her gün listede adıyla
durur ve müdür onayından önce görülür.

## Sonuçlar

- Eski planlarda günde dört ve üzeri sınav varsa artık engel görünür ve plan
  kesinleştirilemez.
- Çok ağır yüklü öğrenci (ör. 31 ders) hafta sonu açılmadan 10 iş gününe
  sığmaz; program bunu adıyla söyler.
