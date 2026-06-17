import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import os

# ==========================================
# 1. DOSYA YOLLARI VE KURULUM
# ==========================================

CSV_PATH = '../output/parameter analysis/parameter_analysis_results.csv'
OUTPUT_DIR = '../output/parameter analysis/plots_advanced'

os.makedirs(OUTPUT_DIR, exist_ok=True)

print("Veri yükleniyor ve analiz başlıyor...")
df = pd.read_csv(CSV_PATH)

# Akademik ve profesyonel çizim ayarları
sns.set_theme(style="whitegrid")
plt.rcParams.update({
    'font.size': 12, 
    'figure.autolayout': True,
    'axes.titlesize': 14,
    'axes.titlepad': 15
})

# ==========================================
# GRAFİK 1: Arama Stratejisi (Popülasyon Boyutunun Etkisi)
# ==========================================
print("Grafik 1 çiziliyor: Popülasyon Etkisi...")
plt.figure(figsize=(10, 6))
sns.boxplot(data=df, x='K', y='Final_HV', hue='PopSize', palette='viridis')
plt.title('Arama Stratejisi: Popülasyon Boyutu vs Final Hypervolume (HV)')
plt.xlabel('Kargo Dolabı Sayısı (K)')
plt.ylabel('Final Hypervolume')
plt.legend(title='Popülasyon')
plt.savefig(f'{OUTPUT_DIR}/1_Population_Strategy.png', dpi=300, bbox_inches='tight')
plt.close()

# ==========================================
# GRAFİK 2: Lambda (POI Ağırlığı) Parametresinin Etkisi
# ==========================================
print("Grafik 2 çiziliyor: Lambda Etkisi...")
plt.figure(figsize=(10, 6))
# Pointplot, ortalamaları ve güven aralıklarını çok net gösterir
sns.pointplot(data=df, x='Lambda', y='Final_HV', hue='K', palette='Set1', markers=['o', 's', 'D'], capsize=.1)
plt.title('Talep Ağırlığı: Lambda (POI Etkisi) vs Performans')
plt.xlabel('Lambda Değeri')
plt.ylabel('Ortalama Final Hypervolume')
plt.legend(title='K Değeri')
plt.savefig(f'{OUTPUT_DIR}/2_Lambda_Effect.png', dpi=300, bbox_inches='tight')
plt.close()

# ==========================================
# GRAFİK 3: Her K Değeri İçin Özel Isı Haritaları (Heatmaps)
# ==========================================
print("Grafik 3 çiziliyor: K'ya Özel Isı Haritaları...")
unique_ks = df['K'].unique()
for k in unique_ks:
    plt.figure(figsize=(8, 6))
    subset = df[df['K'] == k]
    # Mutasyon ve Çaprazlamanın HV ortalamasını pivotla
    heatmap_data = subset.groupby(['MutRate', 'CrossRate'])['Final_HV'].mean().unstack()
    
    sns.heatmap(heatmap_data, annot=True, cmap='coolwarm', fmt=".4f", linewidths=.5)
    plt.title(f'K={k} Senaryosu İçin Parametre Isı Haritası (HV)')
    plt.xlabel('Crossover Rate (Çaprazlama)')
    plt.ylabel('Mutation Rate (Mutasyon)')
    plt.savefig(f'{OUTPUT_DIR}/3_Heatmap_K{k}.png', dpi=300, bbox_inches='tight')
    plt.close()

# ==========================================
# GRAFİK 4: Yakınsama (Convergence) ve Elit Çözüm Sayısı
# ==========================================
print("Grafik 4 çiziliyor: Yakınsama ve Arşiv Doluluğu...")
plt.figure(figsize=(10, 6))
sns.scatterplot(data=df, x='MaxGen', y='ND_Count', hue='K', palette='Dark2', s=100, alpha=0.7)
plt.title('Arama Derinliği (Jenerasyon) vs Bulunan Pareto Çözüm Sayısı (ND_Count)')
plt.xlabel('Maksimum Jenerasyon')
plt.ylabel('Non-Dominated (Elit) Çözüm Sayısı')
plt.legend(title='K Değeri')
plt.savefig(f'{OUTPUT_DIR}/4_Convergence_Proof.png', dpi=300, bbox_inches='tight')
plt.close()

# ==========================================
# GRAFİK 5: Hesaplama Maliyeti (Trade-off: Süre vs Başarı)
# ==========================================
print("Grafik 5 çiziliyor: Hesaplama Maliyeti Takası...")
plt.figure(figsize=(10, 6))
sns.scatterplot(data=df, x='Runtime_ms', y='Final_HV', hue='K', style='PopSize', palette='deep', s=80, alpha=0.7)
plt.title('Hesaplama Maliyeti Takası: Çalışma Süresi vs Hypervolume')
plt.xlabel('Çalışma Süresi (ms) [Logaritmik Ölçek]')
plt.ylabel('Final Hypervolume')
plt.xscale('log') # Süreler çok farklı olduğu için log scale daha iyi gösterir
plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
plt.savefig(f'{OUTPUT_DIR}/5_Runtime_Tradeoff.png', dpi=300, bbox_inches='tight')
plt.close()

# ==========================================
# DETAYLI METİN RAPORU (TEZ İÇİN)
# ==========================================
print("Detaylı akademik rapor TXT olarak yazılıyor...")
grouped = df.groupby(['K', 'Lambda', 'PopSize', 'MutRate', 'CrossRate']).agg({
    'Final_HV': 'mean',
    'ND_Count': 'mean',
    'Runtime_ms': 'mean',
    'MaxGen': 'first',
    'FunctionEvals': 'first'
}).reset_index()

report_path = f'{OUTPUT_DIR}/thesis_detailed_report.txt'
with open(report_path, 'w', encoding='utf-8') as f:
    f.write("="*80 + "\n")
    f.write("SPEA2 PARAMETRE ANALİZİ\n")
    f.write("="*80 + "\n\n")
    
    # BÖLÜM 1: K Bazında Mutlak Şampiyonlar
    f.write("--- BÖLÜM 1: HER PROBLEM BOYUTU (K) İÇİN MUTLAK ŞAMPİYONLAR ---\n")
    f.write("(Tüm seed'lerin ve Lambda senaryolarının ortalamasına göre en yüksek HV)\n\n")
    best_k = grouped.loc[grouped.groupby('K')['Final_HV'].idxmax()]
    f.write(best_k.to_string(index=False))
    f.write("\n\n" + "-"*80 + "\n\n")
    
    # BÖLÜM 2: Lambda Kırılımı (Uygulama arka planı için asıl kullanılacak olan)
    f.write("--- BÖLÜM 2: K ve LAMBDA SENARYOLARINA GÖRE EN İYİ PARAMETRELER ---\n")
    f.write("(Kullanıcı haritada farklı bir Lambda seçtiğinde kullanılacak olan optimum değerler)\n\n")
    best_k_lam = grouped.loc[grouped.groupby(['K', 'Lambda'])['Final_HV'].idxmax()]
    f.write(best_k_lam.to_string(index=False))
    f.write("\n\n" + "-"*80 + "\n\n")

    # BÖLÜM 3: Hesaplama Bütçesi
    f.write("--- BÖLÜM 3: HESAPLAMA BÜTÇESİ (FUNCTION EVALUATIONS) ÖZETİ ---\n")
    f.write("Bütçe (FE) = PopSize * (MaxGen + 1) kuralına göre ayarlanmıştır.\n\n")
    budget_summary = df.groupby('K').agg({
        'FunctionEvals': 'first',
        'Runtime_ms': ['mean', 'min', 'max']
    })
    f.write(budget_summary.to_string())

print(f"\nMUHTEŞEM! Tüm analizler '{OUTPUT_DIR}' klasöründe başarıyla oluşturuldu.")