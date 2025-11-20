import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import numpy as np
import os

# --- 1. SAYFA VE GENEL AYARLAR ---
st.set_page_config(
    page_title="EPDK LPG Pazar Analizi",
    page_icon="⛽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. SABİT VE KONFİGÜRASYON ---
SABIT_DOSYA_ADI = "lpg_veri.xlsx"

# Türkiye İl Merkez Koordinatları (Harita İçin)
IL_KOORDINATLARI = {
    'ADANA': [37.0000, 35.3213], 'ADIYAMAN': [37.7648, 38.2786], 'AFYONKARAHİSAR': [38.7507, 30.5567],
    'AĞRI': [39.7191, 43.0503], 'AKSARAY': [38.3687, 34.0370], 'AMASYA': [40.6499, 35.8353],
    'ANKARA': [39.9334, 32.8597], 'ANTALYA': [36.8969, 30.7133], 'ARDAHAN': [41.1105, 42.7022],
    'ARTVİN': [41.1828, 41.8183], 'AYDIN': [37.8560, 27.8416], 'BALIKESİR': [39.6484, 27.8826],
    'BARTIN': [41.6344, 32.3375], 'BATMAN': [37.8812, 41.1351], 'BAYBURT': [40.2552, 40.2249],
    'BİLECİK': [40.1451, 29.9798], 'BİNGÖL': [38.8854, 40.498], 'BİTLİS': [38.3938, 42.1232],
    'BOLU': [40.7392, 31.6089], 'BURDUR': [37.7204, 30.2908], 'BURSA': [40.1885, 29.0610],
    'ÇANAKKALE': [40.1553, 26.4142], 'ÇANKIRI': [40.6013, 33.6134], 'ÇORUM': [40.5506, 34.9556],
    'DENİZLİ': [37.7765, 29.0864], 'DİYARBAKIR': [37.9144, 40.2306], 'DÜZCE': [40.8438, 31.1565],
    'EDİRNE': [41.6771, 26.5557], 'ELAZIĞ': [38.6810, 39.2264], 'ERZİNCAN': [39.7500, 39.5000],
    'ERZURUM': [39.9000, 41.2700], 'ESKİŞEHİR': [39.7767, 30.5206], 'GAZİANTEP': [37.0662, 37.3833],
    'GİRESUN': [40.9128, 38.3895], 'GÜMÜŞHANE': [40.4600, 39.4700], 'HAKKARİ': [37.5833, 43.7333],
    'HATAY': [36.4018, 36.3498], 'IĞDIR': [39.9167, 44.0333], 'ISPARTA': [37.7648, 30.5566],
    'İSTANBUL': [41.0082, 28.9784], 'İZMİR': [38.4192, 27.1287], 'KAHRAMANMARAŞ': [37.5858, 36.9371],
    'KARABÜK': [41.2061, 32.6204], 'KARAMAN': [37.1759, 33.2287], 'KARS': [40.6167, 43.1000],
    'KASTAMONU': [41.3887, 33.7827], 'KAYSERİ': [38.7312, 35.4787], 'KIRIKKALE': [39.8468, 33.5153],
    'KIRKLARELİ': [41.7333, 27.2167], 'KIRŞEHİR': [39.1425, 34.1709], 'KİLİS': [36.7184, 37.1212],
    'KOCAELİ': [40.8533, 29.8815], 'KONYA': [37.8667, 32.4833], 'KÜTAHYA': [39.4167, 29.9833],
    'MALATYA': [38.3552, 38.3095], 'MANİSA': [38.6191, 27.4289], 'MARDİN': [37.3212, 40.7245],
    'MERSİN': [36.8000, 34.6333], 'MUĞLA': [37.2153, 28.3636], 'MUŞ': [38.9462, 41.7539],
    'NEVŞEHİR': [38.6939, 34.6857], 'NİĞDE': [37.9667, 34.6833], 'ORDU': [40.9839, 37.8764],
    'OSMANİYE': [37.0742, 36.2476], 'RİZE': [41.0201, 40.5234], 'SAKARYA': [40.7569, 30.3783],
    'SAMSUN': [41.2867, 36.3300], 'SİİRT': [37.9333, 41.9500], 'SİNOP': [42.0231, 35.1531],
    'SİVAS': [39.7477, 37.0179], 'ŞANLIURFA': [37.1591, 38.7969], 'ŞIRNAK': [37.5164, 42.4611],
    'TEKİRDAĞ': [40.9833, 27.5167], 'TOKAT': [40.3167, 36.5500], 'TRABZON': [41.0027, 39.7168],
    'TUNCELİ': [39.1079, 39.5401], 'UŞAK': [38.6823, 29.4082], 'VAN': [38.4891, 43.4089],
    'YALOVA': [40.6500, 29.2667], 'YOZGAT': [39.8181, 34.8147], 'ZONGULDAK': [41.4564, 31.7987]
}

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

# --- 4. VERİ YÜKLEME VE İŞLEME ---
@st.cache_data
def load_data(file_path):
    if not os.path.exists(file_path):
        return None
    
    try:
        df = pd.read_excel(file_path)
        # Sütun isimlerini temizle
        df.columns = [c.strip() for c in df.columns]
        
        # Tarih Sütunları
        date_cols = [
            'Lisans Başlangıç Tarihi', 'Lisans Bitiş Tarihi',
            'Dağıtıcı ile Yapılan Sözleşme Başlangıç Tarihi',
            'Dağıtıcı ile Yapılan Sözleşme Bitiş Tarihi'
        ]
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce')

        # Ana Hedef Tarih
        target_col = 'Dağıtıcı ile Yapılan Sözleşme Bitiş Tarihi'
        if target_col not in df.columns:
            # Eğer bu sütun yoksa Lisans Bitiş Tarihi'ni kullanmayı dene (Yedek Plan)
            target_col = 'Lisans Bitiş Tarihi'
        
        # Kalan Gün Hesabı
        today = pd.to_datetime(datetime.date.today())
        if target_col in df.columns:
            df['Kalan_Gun'] = (df[target_col] - today).dt.days
        else:
            df['Kalan_Gun'] = np.nan

        # Risk Kategorileri
        def get_risk(days):
            if pd.isna(days): return "Bilinmiyor"
            if days < 0: return "SÜRESİ DOLDU 🚨"
            if days < 90: return "KRİTİK (<3 Ay) ⚠️"
            if days < 180: return "YAKLAŞIYOR (<6 Ay) ⏳"
            return "GÜVENLİ ✅"

        df['Risk_Durumu'] = df['Kalan_Gun'].apply(get_risk)
        
        # İl ve İlçe düzenleme (Büyük harf ve Türkçe karakter)
        if 'İl' in df.columns:
            df['İl'] = df['İl'].astype(str).str.upper().str.replace('i', 'İ').str.replace('ı', 'I')
        if 'İlçe' in df.columns:
            df['İlçe'] = df['İlçe'].astype(str).str.upper().str.replace('i', 'İ').str.replace('ı', 'I')

        return df, target_col

    except Exception as e:
        st.error(f"Veri okuma hatası: {e}")
        return None, None

def main():
    # --- VERİYİ OKU ---
    df, target_date_col = load_data(SABIT_DOSYA_ADI)
    
    if df is None:
        st.error(f"❌ HATA: '{SABIT_DOSYA_ADI}' dosyası bulunamadı. Lütfen Excel dosyasını GitHub'a yüklediğinden emin ol.")
        st.stop()

    # --- SIDEBAR FİLTRELERİ (GELİŞMİŞ) ---
    with st.sidebar:
        st.title("🔍 Filtre Paneli")
        st.markdown("Verileri daraltmak için aşağıdakileri kullanın.")
        
        # 1. İl Filtresi
        all_cities = sorted(df['İl'].unique().tolist())
        selected_cities = st.multiselect("🏢 Şehir Seç", all_cities)
        
        # 2. İlçe Filtresi (İl seçimine göre dinamik değişir)
        if selected_cities:
            filtered_districts = sorted(df[df['İl'].isin(selected_cities)]['İlçe'].unique().tolist())
        else:
            filtered_districts = sorted(df['İlçe'].unique().tolist())
        
        selected_districts = st.multiselect("📍 İlçe Seç", filtered_districts)

        # 3. Şirket Filtresi
        all_companies = sorted(df['Dağıtım Şirketi'].dropna().unique().tolist())
        selected_companies = st.multiselect("⛽ Şirket Seç", all_companies)

        # 4. Risk Filtresi
        all_risks = df['Risk_Durumu'].unique().tolist()
        selected_risks = st.multiselect("⚠️ Risk Durumu", all_risks)

        st.info(f"Toplam Kayıt: {len(df)}")

    # --- FİLTRE UYGULAMA MOTORU ---
    df_filtered = df.copy()
    if selected_cities:
        df_filtered = df_filtered[df_filtered['İl'].isin(selected_cities)]
    if selected_districts:
        df_filtered = df_filtered[df_filtered['İlçe'].isin(selected_districts)]
    if selected_companies:
        df_filtered = df_filtered[df_filtered['Dağıtım Şirketi'].isin(selected_companies)]
    if selected_risks:
        df_filtered = df_filtered[df_filtered['Risk_Durumu'].isin(selected_risks)]

    # --- ANA EKRAN ---
    st.title("🚀 Otogaz (LPG) Pazar & Risk Analizi")
    st.markdown(f"**Veri Kaynağı:** EPDK Lisans Veritabanı | **Son Güncelleme:** {datetime.date.today().strftime('%d.%m.%Y')}")

    # KPI KARTLARI
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Toplam İstasyon", f"{len(df_filtered):,}")
    with col2:
        riskli_sayi = len(df_filtered[df_filtered['Kalan_Gun'] < 90])
        st.metric("Riskli Sözleşme (<90 Gün)", riskli_sayi, delta="Acil Aksiyon", delta_color="inverse")
    with col3:
        active_companies = df_filtered['Dağıtım Şirketi'].nunique()
        st.metric("Aktif Dağıtıcı", active_companies)
    with col4:
        avg_days = df_filtered['Kalan_Gun'].mean()
        st.metric("Ort. Sözleşme Ömrü", f"{avg_days/365:.1f} Yıl" if not pd.isna(avg_days) else "-")

    st.divider()

    # --- SEKMELER ---
    tab_risk, tab_geo, tab_market, tab_trend, tab_data = st.tabs([
        "⚡ Sözleşme & Risk", 
        "🗺️ Coğrafi Analiz", 
        "🏢 Pazar & Rekabet", 
        "📈 Zaman Analizi",
        "📋 Ham Veri"
    ])

    # =================================================
    # TAB 1: RİSK ANALİZİ (En Önemli Kısım)
    # =================================================
    with tab_risk:
        st.subheader("🚨 Kritik Sözleşme Takip Tablosu (İlk 90 Gün)")
        
        # Kritik veriyi hazırla
        critical_df = df_filtered[df_filtered['Kalan_Gun'] < 90].sort_values('Kalan_Gun')
        
        if not critical_df.empty:
            critical_df['Bitis_Tarih_Str'] = critical_df[target_date_col].dt.strftime('%Y-%m-%d')
            
            st.dataframe(
                critical_df[['Unvan', 'İl', 'İlçe', 'Dağıtım Şirketi', 'Bitis_Tarih_Str', 'Kalan_Gun']],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Unvan": st.column_config.TextColumn("Bayi Adı", width="large"),
                    "Kalan_Gun": st.column_config.ProgressColumn(
                        "Kalan Gün", format="%d Gün", min_value=0, max_value=90
                    ),
                    "Bitis_Tarih_Str": "Bitiş Tarihi"
                }
            )
        else:
            st.success("Seçilen kriterlere göre önümüzdeki 90 gün içinde bitecek sözleşme bulunmuyor.")

        st.write("---")
        
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Yıllara Göre Sözleşme Bitişleri")
            df_filtered['Bitis_Yili'] = df_filtered[target_date_col].dt.year
            year_counts = df_filtered['Bitis_Yili'].value_counts().sort_index().reset_index()
            year_counts.columns = ['Yıl', 'Adet']
            # Gelecek 10 yılı gösterelim sadece
            curr_year = datetime.date.today().year
            year_counts = year_counts[(year_counts['Yıl'] >= curr_year) & (year_counts['Yıl'] <= curr_year + 10)]
            
            fig_bar = px.bar(year_counts, x='Yıl', y='Adet', text='Adet', color='Adet', color_continuous_scale='Oranges')
            st.plotly_chart(fig_bar, use_container_width=True)
            
        with c2:
            st.subheader("Risk Dağılımı")
            risk_counts = df_filtered['Risk_Durumu'].value_counts().reset_index()
            risk_counts.columns = ['Durum', 'Adet']
            fig_pie_risk = px.pie(risk_counts, values='Adet', names='Durum', hole=0.4, 
                                  color_discrete_map={"SÜRESİ DOLDU 🚨":"red", "KRİTİK (<3 Ay) ⚠️":"orange", "GÜVENLİ ✅":"green"})
            st.plotly_chart(fig_pie_risk, use_container_width=True)

    # =================================================
    # TAB 2: COĞRAFİ ANALİZ (Harita & Sunburst)
    # =================================================
    with tab_geo:
        col_map, col_details = st.columns([2, 1])
        
        with col_map:
            st.subheader("📍 İstasyon Haritası")
            # Koordinat eşleme
            map_df = df_filtered.copy()
            lats, lons = [], []
            
            for il_adi in map_df['İl']:
                # Eşleşme için temizlik
                key = str(il_adi).upper().replace('İ','I')
                coord = None
                for k, v in IL_KOORDINATLARI.items():
                    if k in key:
                        coord = v
                        break
                
                if coord:
                    # Üst üste binmemesi için hafif rastgelelik (Jitter)
                    lats.append(coord[0] + np.random.uniform(-0.03, 0.03))
                    lons.append(coord[1] + np.random.uniform(-0.03, 0.03))
                else:
                    lats.append(None); lons.append(None)
            
            map_df['lat'] = lats
            map_df['lon'] = lons
            map_df = map_df.dropna(subset=['lat'])
            
            if not map_df.empty:
                fig_map = px.scatter_mapbox(
                    map_df, lat="lat", lon="lon", color="Dağıtım Şirketi",
                    hover_name="Unvan", hover_data=["İlçe", "Kalan_Gun"],
                    zoom=5, height=600, mapbox_style="carto-positron",
                    size_max=10
                )
                st.plotly_chart(fig_map, use_container_width=True)
            else:
                st.warning("Harita için yeterli veri eşleştirilemedi.")

        with col_details:
            st.subheader("İl -> İlçe Dağılımı")
            # Sunburst Grafiği (İl ve İlçe hiyerarşisi)
            # Çok fazla veri varsa sadece top 10 ili al
            top_cities = df_filtered['İl'].value_counts().head(10).index
            sunburst_df = df_filtered[df_filtered['İl'].isin(top_cities)]
            
            fig_sun = px.sunburst(sunburst_df, path=['İl', 'İlçe'], title="Bölgesel Yoğunluk (İlk 10 İl)")
            st.plotly_chart(fig_sun, use_container_width=True)

            st.subheader("Şehir Bazlı Yoğunluk")
            city_counts = df_filtered['İl'].value_counts().reset_index().head(10)
            city_counts.columns = ['Şehir', 'Adet']
            st.dataframe(city_counts, use_container_width=True, hide_index=True)

    # =================================================
    # TAB 3: PAZAR & REKABET
    # =================================================
    with tab_market:
        c_tree, c_pie = st.columns([2, 1])
        
        with c_tree:
            st.subheader("🏢 Pazar Hakimiyet Haritası (Treemap)")
            st.markdown("Kutucukların büyüklüğü istasyon sayısını gösterir.")
            fig_tree = px.treemap(df_filtered, path=['Dağıtım Şirketi', 'İl'], color='Dağıtım Şirketi')
            st.plotly_chart(fig_tree, use_container_width=True)

        with c_pie:
            st.subheader("🍰 Pazar Payı")
            comp_counts = df_filtered['Dağıtım Şirketi'].value_counts().reset_index()
            comp_counts.columns = ['Şirket', 'Adet']
            
            # Diğerleri Grubu
            if len(comp_counts) > 10:
                top_10 = comp_counts.iloc[:10]
                others = pd.DataFrame({'Şirket': ['DİĞERLERİ'], 'Adet': [comp_counts.iloc[10:]['Adet'].sum()]})
                comp_counts = pd.concat([top_10, others], ignore_index=True)
            
            fig_pie = px.pie(comp_counts, values='Adet', names='Şirket', hole=0.4)
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            fig_pie.update_layout(showlegend=False)
            st.plotly_chart(fig_pie, use_container_width=True)

    # =================================================
    # TAB 4: ZAMAN ANALİZİ (TRENDLER)
    # =================================================
    with tab_trend:
        st.subheader("📈 Lisans Başlangıç Tarihine Göre Büyüme")
        
        if 'Dağıtıcı ile Yapılan Sözleşme Başlangıç Tarihi' in df_filtered.columns:
            trend_df = df_filtered.copy()
            trend_df['Yil'] = trend_df['Dağıtıcı ile Yapılan Sözleşme Başlangıç Tarihi'].dt.year
            
            # Yıllara göre yeni bayi sayısı
            yearly_growth = trend_df['Yil'].value_counts().sort_index().reset_index()
            yearly_growth.columns = ['Yıl', 'Yeni Bayi Sayısı']
            
            # 2000 yılından sonrasını alalım (Gürültüyü önlemek için)
            yearly_growth = yearly_growth[yearly_growth['Yıl'] >= 2000]

            fig_line = px.line(yearly_growth, x='Yıl', y='Yeni Bayi Sayısı', markers=True, 
                               title="Yıllara Göre Sisteme Giren Yeni Bayi Sayısı")
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.warning("Sözleşme başlangıç tarihi verisi bulunamadığı için trend analizi yapılamıyor.")

    # =================================================
    # TAB 5: HAM VERİ & RAPOR
    # =================================================
    with tab_data:
        st.subheader("📋 Detaylı Veri Listesi ve İndirme")
        
        # Tabloyu göster
        show_cols = ['Lisans No', 'Unvan', 'İl', 'İlçe', 'Dağıtım Şirketi', target_date_col, 'Kalan_Gun', 'Risk_Durumu']
        # Sütunların hepsi var mı kontrol et, yoksa olanları göster
        existing_cols = [c for c in show_cols if c in df_filtered.columns]
        
        export_df = df_filtered[existing_cols].sort_values('Kalan_Gun')
        
        # Tarih formatı düzeltme
        if target_date_col in export_df.columns:
            export_df[target_date_col] = export_df[target_date_col].dt.strftime('%Y-%m-%d')
        
        st.download_button(
            "📥 Excel Listesini İndir (CSV)",
            export_df.to_csv(index=False).encode('utf-8'),
            "filtrelenmis_bayi_listesi.csv",
            "text/csv",
            key='download-csv'
        )
        
        # Renklendirme fonksiyonu
        def highlight_risk(val):
            if val == 'SÜRESİ DOLDU 🚨': return 'background-color: #ffcccc; color: black'
            if val == 'KRİTİK (<3 Ay) ⚠️': return 'background-color: #ffeebb; color: black'
            return ''

        st.dataframe(export_df.style.applymap(highlight_risk, subset=['Risk_Durumu']), use_container_width=True, height=600)

if __name__ == "__main__":
    main()
