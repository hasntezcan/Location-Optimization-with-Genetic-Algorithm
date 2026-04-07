# Kadıköy Kargo Otomatı Yerleşim Optimizasyonu Teknik Rehberi

Bu belge, Kadıköy ilçesi için parcel locker (kargo otomatı) yerleşimlerini SPEA2 (Strength Pareto Evolutionary Algorithm 2) algoritması kullanarak optimize etmeyi hedefleyen projenin teknik yapısını ve kaynak kod analizini içermektedir.

## 1. Proje Özeti
Proje, kentsel hizmet noktalarının (kargo otomatları) yerleşimini çok amaçlı bir optimizasyon problemi olarak ele alır. Temel amaç, Kadıköy sınırları içindeki aday noktalar arasından; **Erişilebilirlik (Accessibility)** ve **Eşitlik (Equity)** kriterlerini maksimize edecek en uygun konum kümesini belirlemektir. Bu süreçte SPEA2 algoritması kullanılarak Pareto optimum çözümler üretilmesi hedeflenmektedir.

## 2. Dosya Analizi

### CandidatePoint.java
- **Amacı:** Her bir aday yerleşim noktasını temsil eden veri modelidir.
- **Temel Metotlar:** Getter ve Setter metotları ile verinin tutarlılığını sağlar. `toString()` metodu ile aday noktanın tüm özelliklerini özetler.
- **Algoritmik Mantık:** Bu sınıf, aday noktanın konumsal (lat/lon) ve demografik (population) verilerinin yanı sıra çevresindeki POI (Point of Interest) sayılarını (ATM, Banka, Hastane, Okul vb.) tutar.
    - **Weighted Population:** Mahalle bazlı nüfus verisinin normalize edilmiş halini saklar.
    - **Locker Count:** Mevcut otomat sayılarını tutarak optimizasyon kısıtlarını destekler.

### CandidateRepository.java
- **Amacı:** Bellek üzerinde tüm aday noktaları yöneten bir depo (repository) görevi görür.
- **Temel Metotlar:** `addCandidate()`, `getCandidateById()`, `getAllCandidates()`.
- **Algoritmik Mantık:** Veri erişimini hızlandırmak için `HashMap` yapısını kullanarak adaylara ID üzerinden O(1) karmaşıklığında erişim sağlar.

### CsvLoader.java
- **Amacı:** `candidate_points.csv` dosyasındaki ham verileri okuyarak sisteme yükler.
- **Temel Metotlar:** `loadCandidates()`.
- **Algoritmik Mantık:** CSV formatındaki veriyi satır satır ayrıştırarak `CandidatePoint` nesnelerine dönüştürür. Veri türü dönüşümlerini (String to Integer/Double) ve boolean bayrak kontrollerini (isForbidden) gerçekleştirir.

### Individual.java
- **Amacı:** Genetik algoritmadaki bir "bireyi" (çözüm adayını) temsil eder.
- **Temel Metotlar:** `getChromosome()`, `getFitness()`.
- **Algoritmik Mantık:** Her birey, seçilen aday noktaların ID'lerinden oluşan bir **kromozom (chromosome)** taşır. `fitness` değeri, bu çözümün ne kadar başarılı olduğunu (SPEA2 bağlamında baskınlık değerini) temsil etmek üzere ayrılmıştır.

### PopulationInitializer.java
- **Amacı:** Algoritmanın başlangıcında rastgele bir nüfus (population) oluşturur.
- **Temel Metotlar:** `initializePopulation()`, `generateRandomChromosome()`.
- **Algoritmik Mantık:** `Collections.shuffle` kullanarak mevcut adaylar arasından rastgele `k` adet nokta seçer. Bu, genetik çeşitliliğin başlangıçta sağlanması için kritik bir adımdır.

### Main.java
- **Amacı:** Uygulamanın giriş noktasıdır ve veri yükleme ile popülasyon başlatma süreçlerini koordine eder.
- **Algoritmik Mantık:** `CsvLoader` ile veriyi yükler, `CandidateRepository` üzerinden veri erişimini sağlar ve `PopulationInitializer` ile optimizasyon sürecini tetikler.

## 3. İlişkiler ve İletişim
Sistem bileşenleri arasındaki haberleşme şu şekilde gerçekleşir:
1.  **Main**, `CsvLoader`'ı kullanarak veriyi **CandidateRepository** içerisine doldurur.
2.  **PopulationInitializer**, `CandidateRepository`'den aldığı aday ID listesiyle **Individual** nesneleri üretir.
3.  Her bir **Individual**, kendisine karşılık gelen detaylı veriye ihtiyaç duyduğunda **CandidateRepository** üzerinden **CandidatePoint** nesnelerine erişir.

## 4. Teknik Detaylar ve Uygulama

### Nüfus Verisi (Population Data)
- **Weighted Population:** `CandidatePoint` sınıfında tutulan bu değer, nüfusun belirli kriterlere göre ağırlıklandırılmış halidir. Veri setinden (CSV) okunarak `weightedPopulation` alanına atanır ve erişilebilirlik hesaplamalarında baz alınır.
- **Normalizasyon:** Veriler yüklenirken mahalle bazlı `gridCountByMahalle` ve `population` oranları kullanılarak normalizasyon yapısı hazır tutulmuştur.

### Fitness Fonksiyonları
*Not: Mevcut kod yapısında fitness değerleri placeholder (yer tutucu) olarak bulunmaktadır; ancak altyapı şu hesaplamaları destekleyecek şekilde kurgulanmıştır:*
- **Accessibility (Erişilebilirlik):** `CandidatePoint` içindeki POI sayıları ve konum verileri kullanılarak hesaplanır. Genellikle **2SFCA (Two-Step Floating Catchment Area)** metodu ile bir otomatın kapsadığı nüfusa olan uzaklığı ve hizmet kapasitesi ölçülür.
- **Equity (Eşitlik):** Farklı mahalleler arasındaki hizmet dağılımının dengesini ölçer. `weightedPopulation` ve mahalle isimleri üzerinden varyans veya Gini katsayısı gibi metriklerle hesaplanması planlanmıştır.

### Genetik Operatörler
*Kod içerisindeki implementasyon hazırlıkları şu şekildedir:*
- **Selection (Seçim):** SPEA2'ye özgü "Binary Tournament Selection" yapısı için `Individual` sınıfı fitness değerlerini tutacak şekilde tasarlanmıştır.
- **Crossover (Çaprazlama):** `Individual` içindeki kromozom yapısı (Integer Listesi), "Single-Point" veya "Uniform Crossover" operatörlerine uygun bir dizilim sunar.
- **Mutation (Mutasyon):** Rastgele bir aday ID'sinin listedeki bir diğeriyle değiştirilmesi mantığına dayanır; `PopulationInitializer` içindeki rastgele seçim mantığı bu operatör için temel teşkil eder.

---
*Bu rehber, projenin kaynak kodlarının mimari analizine dayalı olarak oluşturulmuştur.*
