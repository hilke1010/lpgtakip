import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import numpy as np
import os
from docx import Document # Word okumak için gerekli kütüphane
import re # Metin ayıklamak için (Regex)

# --- 1. SAYFA VE GENEL AYARLAR ---
st.set_page_config(
    page_title="EPDK LPG Pazar Analizi",
    page_icon="⛽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. DOSYA İSİMLERİ ---
EXCEL_DOSYA_ADI = "lpg_veri.xlsx"
WORD_DOSYA_ADI = "satis.docx"

# --- 3. CSS ÖZELLEŞTİRME ---
st.markdown("""
<style>
    .stMetric {
        background-color: #f0f2f6;
        border-left: 5px solid #ff4b4b;
        padding: 15px;
        border-radius: 5px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    .block-container { padding-top: 2rem; }
    h1 { color: #0e1117; }
    h3 { color: #262730; }
</style>
""", unsafe_allow_html=True)

# --- 4. EXCEL VERİ YÜKLEME ---
@st.cache_data
def load_excel_data(file_path):
    if not os.path.exists(file_path): return None, None
    try:
        df = pd.read_excel(file_path)
        df.columns = [c.strip() for c in df.columns]
        
        date_cols = ['Lisans Başlangıç Tarihi', 'Lisans Bitiş Tarihi', 'Dağıtıcı ile Yapılan Sözleşme Başlangıç Tarihi', 'Dağıtıcı ile Yapılan Sözleşme Bitiş Tarihi']
        for col in date_cols:
            if col in df.columns: df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce')

        target_col = 'Dağıtıcı ile Yapılan Sözleşme Bitiş Tarihi'
        if target_col not in df.columns: target_col = 'Lisans Bitiş Tarihi'
        
        today = pd.to_datetime(datetime.date.today())
        if target_col in df.columns: df['Kalan_Gun'] = (df[target_col] - today).dt.days
        else: df['Kalan_Gun'] = np.nan

        def get_risk(days):
            if pd.isna(days): return "Bilinmiyor"
            if days < 0: return "SÜRESİ DOLDU 🚨"
            if days < 90: return "KRİTİK (<3 Ay) ⚠️"
            if days < 180: return "YAKLAŞIYOR (<6 Ay) ⏳"
            return "GÜVENLİ ✅"

        df['Risk_Durumu'] = df['Kalan_Gun'].apply(get_risk)
        if 'İl' in df.columns: df['İl'] = df['İl'].astype(str).str.upper().str.replace('i', 'İ').str.replace('ı', 'I')
        if 'İlçe' in df.columns: df['İlçe'] = df['İlçe'].astype(str).str.upper().str.replace('i', 'İ').str.replace('ı', 'I')
        return df, target_col
    except Exception as e:
        st.error(f"Excel hatası: {e}"); return None, None

# --- 5. WORD VERİ YÜKLEME VE AYIKLAMA (YENİ) ---
@st.cache_data
def load_word_tables(file_path):
    """
    Word dosyasındaki 'Tablo X: Şehir' formatındaki başlıkları bulur 
    ve altındaki tabloları okur.
    """
    if not os.path.exists(file_path):
        return None

    try:
        doc = Document(file_path)
        sehir_tablolari = {}
        
        # Adım 1: Önce paragraflardan şehir isimlerini bulalım
        # Regex deseni: "Tablo" kelimesi, sonra sayılar, sonra iki nokta, sonra Şehir İsmi
        # Örnek: "Tablo 4.1: Adana" -> "Adana"yı alır.
        pattern = re.compile(r"Tablo\s+[\d\.]+\s*:\s*(.+)", re.IGNORECASE)
        
        bulunan_sehirler = []
        for para in doc.paragraphs:
            match = pattern.search(para.text)
            if match:
                sehir_adi = match.group(1).strip().upper().replace('i', 'İ').replace('ı', 'I')
                bulunan_sehirler.append(sehir_adi)
        
        # Adım 2: Tabloları sırayla şehirlerle eşleştirelim
        # Varsayım: Word dosyasındaki tablo sırası ile başlık sırası aynıdır.
        tables = doc.tables
        
        min_len = min(len(bulunan_sehirler), len(tables))
        
        for i in range(min_len):
            city = bulunan_sehirler[i]
            table = tables[i]
            
            # Tabloyu DataFrame'e çevir
            data = []
            keys = None
            
            # Tablonun satırlarını gez
            for row_idx, row in enumerate(table.rows):
                text = [cell.text.strip() for cell in row.cells]
                
                # İlk 2 satır başlık olduğu için veriyi 3. satırdan (index 2) başlatalım
                # Ancak başlıkları düzgün isimlendirmek lazım
                if row_idx >= 2: 
                    data.append(text)
            
            # Sütun başlıklarını manuel olarak standartlaştıralım (Resimdeki formata göre)
            # Çünkü Word'de merge edilmiş hücreleri kodla çözmek zordur.
            custom_headers = [
                "Lisans Sahibinin Unvanı", 
                "Tüplü Satış(ton)", "Tüplü Pay(%)",
                "Dökme Satış(ton)", "Dökme Pay(%)",
                "Otogaz Satış(ton)", "Otogaz Pay(%)",
                "Toplam Satış(ton)", "Toplam Pay(%)"
            ]
            
            # Eğer tablonun sütun sayısı bizim başlık sayımızla tutuyorsa
            if len(table.rows[0].cells) == len(custom_headers):
                 df_table = pd.DataFrame(data, columns=custom_headers)
            else:
                # Tutmazsa otomatik isimlendir
                df_table = pd.DataFrame(data)
            
            # Sayısal verileri temizle (Virgülü noktaya çevir, boşlukları sil)
            # İlk sütun (Unvan) hariç diğerlerini sayıya çevirmeye çalış
            for col in df_table.columns[1:]:
                try:
                    df_table[col] = df_table[col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
                    df_table[col] = pd.to_numeric(df_table[col], errors='coerce').fillna(0)
                except:
                    pass
                
            sehir_tablolari[city] = df_table
            
        return sehir_tablolari

    except Exception as e:
        st.error(f"Word okuma hatası: {e}")
        return None

def main():
    # --- VERİLERİ OKU ---
    df, target_date_col = load_excel_data(EXCEL_DOSYA_ADI)
    word_data = load_word_tables(WORD_DOSYA_ADI)
    
    if df is None:
        st.error(f"❌ HATA: '{EXCEL_DOSYA_ADI}' bulunamadı.")
        st.stop()

    # --- ANA EKRAN ---
    st.title("🚀 Otogaz (LPG) Pazar & Risk Analizi")
    
    # KPI Kartları (Excel'den)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Toplam İstasyon", f"{len(df):,}")
    riskli_sayi = len(df[df['Kalan_Gun'] < 90])
    col2.metric("Acil Sözleşme", riskli_sayi, delta="Acil", delta_color="inverse")
    col3.metric("Aktif Dağıtıcı", df['Dağıtım Şirketi'].nunique())
    col4.metric("Ort. Kalan Gün", f"{df['Kalan_Gun'].mean():.0f}")

    st.divider()

    # --- SEKMELER (YENİ SEKME EKLENDİ) ---
    tab_risk, tab_detay, tab_market, tab_epdk, tab_data = st.tabs([
        "⚡ Sözleşme & Risk", 
        "🔢 Detaylı Bayi Sayıları", 
        "🏢 Pazar & Rekabet", 
        "📄 EPDK Raporu (Satışlar)", # YENİ SEKME
        "📋 Ham Veri"
    ])

    # =================================================
    # TAB 1, 2, 3 (MEVCUT KODLAR - ÖZET GEÇİYORUM)
    # =================================================
    with tab_risk:
        st.subheader("🚨 Kritik ve Yaklaşan Sözleşmeler")
        critical_df = df[df['Kalan_Gun'] < 180].sort_values('Kalan_Gun')
        if not critical_df.empty:
            critical_df['Bitis'] = critical_df[target_date_col].dt.strftime('%Y-%m-%d')
            st.dataframe(critical_df[['Unvan', 'İl', 'Dağıtım Şirketi', 'Bitis', 'Kalan_Gun', 'Risk_Durumu']], use_container_width=True, hide_index=True)
        else:
            st.success("Riskli sözleşme yok.")

    with tab_detay:
        st.subheader("Dağıtım Şirketleri Bayi Sayıları")
        comp_stats = df['Dağıtım Şirketi'].value_counts().reset_index()
        comp_stats.columns = ['Şirket', 'Adet']
        st.dataframe(comp_stats, use_container_width=True, height=400)

    with tab_market:
        st.subheader("Pazar Payı")
        st.plotly_chart(px.treemap(df, path=['Dağıtım Şirketi', 'İl'], color='Dağıtım Şirketi'), use_container_width=True)

    # =================================================
    # TAB 4: EPDK RAPORU (WORD DOSYASI ENTEGRASYONU)
    # =================================================
    with tab_epdk:
        st.header("📄 EPDK Satış Raporları (Tablo 4)")
        
        if word_data:
            # 1. Şehir Seçimi Kutusu
            # Word'den bulduğumuz şehir isimlerini listeye koyalım
            sehirler_listesi = sorted(list(word_data.keys()))
            
            if not sehirler_listesi:
                st.warning("Word dosyasında 'Tablo X: Şehir' formatında başlık bulunamadı.")
            else:
                secilen_il = st.selectbox("📊 Satış Raporunu Görmek İstediğiniz İli Seçin:", sehirler_listesi)
                
                # 2. Seçilen İlin Tablosunu Getir
                if secilen_il:
                    tablo_df = word_data[secilen_il]
                    
                    st.markdown(f"### {secilen_il} İli LPG Satış Dağılımı")
                    
                    # Tabloyu Göster
                    # Renklendirme: Toplam satırını veya en yüksek satışı vurgulayabiliriz
                    st.dataframe(
                        tablo_df.style.format(precision=2).background_gradient(cmap="Blues", subset=["Toplam Satış(ton)"]),
                        use_container_width=True,
                        height=600
                    )
                    
                    # İsteğe bağlı: Seçilen il için küçük bir grafik de çizelim
                    if "Toplam Satış(ton)" in tablo_df.columns and "Lisans Sahibinin Unvanı" in tablo_df.columns:
                        # "TOPLAM" satırını grafikten çıkaralım
                        grafik_data = tablo_df[tablo_df["Lisans Sahibinin Unvanı"] != "TOPLAM"].copy()
                        # En çok satan ilk 10
                        grafik_data = grafik_data.sort_values("Toplam Satış(ton)", ascending=False).head(10)
                        
                        fig_satis = px.bar(grafik_data, x="Toplam Satış(ton)", y="Lisans Sahibinin Unvanı", 
                                           text="Toplam Satış(ton)", orientation='h', title=f"{secilen_il} - En Çok Satış Yapan İlk 10 Şirket")
                        fig_satis.update_layout(yaxis={'categoryorder':'total ascending'})
                        st.plotly_chart(fig_satis, use_container_width=True)
                        
        else:
            st.warning(f"'{WORD_DOSYA_ADI}' dosyası okunamadı veya içi boş. Lütfen dosyayı GitHub'a yüklediğinizden emin olun.")

    # =================================================
    # TAB 5: HAM VERİ
    # =================================================
    with tab_data:
        st.subheader("Ham Veri")
        st.dataframe(df, use_container_width=True)

if __name__ == "__main__":
    main()
