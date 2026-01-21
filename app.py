import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import numpy as np
import os
import io
import time

# --- 1. SAYFA VE GENEL AYARLAR ---
st.set_page_config(
    page_title="EPDK LPG Pazar Analizi",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- PERFORMANS AYARLARI ---
MAX_ROW_DISPLAY = 1000  
MAX_MAP_POINTS = 50000 
PREVIEW_ROW_LIMIT = 100

# --- 2. DOSYA İSİMLERİ ---
SABIT_DOSYA_ADI = "lpg.xlsx" # Akaryakıttan farklı olarak lpg.xlsx'e bağladık

# --- 3. CSS ÖZELLEŞTİRME ---
st.markdown("""
<style>
    .stMetric {
        background-color: #f0f2f6;
        border-left: 5px solid #e67e22; /* LPG için turuncu tonu */
        padding: 15px;
        border-radius: 5px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    .block-container { padding-top: 2rem; }
    .warning-box {
        padding: 1rem;
        background-color: #ffeba0;
        border-left: 6px solid #ffa500;
        color: #5c3a00;
        border-radius: 4px;
        font-weight: bold;
    }
    .year-box {
        background-color: #fef5e7;
        padding: 10px;
        border-radius: 5px;
        text-align: center;
        border: 1px solid #fad7a0;
        margin-bottom: 5px;
    }
    .year-title { font-weight: bold; color: #a04000; font-size: 1.1em; }
    .year-count { font-size: 1.5em; font-weight: bold; color: #d35400; }
    
    .insight-box-success { padding: 15px; border-radius: 8px; background-color: #d4edda; border-left: 5px solid #28a745; color: #155724; margin-bottom: 10px; }
    .insight-box-warning { padding: 15px; border-radius: 8px; background-color: #fff3cd; border-left: 5px solid #ffc107; color: #856404; margin-bottom: 10px; }
    .insight-box-danger { padding: 15px; border-radius: 8px; background-color: #f8d7da; border-left: 5px solid #dc3545; color: #721c24; margin-bottom: 10px; }
    .insight-box-info { padding: 15px; border-radius: 8px; background-color: #d1ecf1; border-left: 5px solid #17a2b8; color: #0c5460; margin-bottom: 10px; }
    .district-chip { display: inline-block; background-color: #f1f3f5; padding: 5px 10px; margin: 3px; border-radius: 15px; font-size: 0.9em; border: 1px solid #ddd; cursor: help; }
</style>
""", unsafe_allow_html=True)

# --- 4. KOORDİNAT VERİTABANI (İL MERKEZLERİ) ---
CITY_COORDINATES = {
    "ADANA": [37.0000, 35.3213], "ADIYAMAN": [37.7648, 38.2786], "AFYONKARAHİSAR": [38.7507, 30.5567],
    "AĞRI": [39.7191, 43.0503], "AMASYA": [40.6499, 35.8353], "ANKARA": [39.9334, 32.8597],
    "ANTALYA": [36.8969, 30.7133], "ARTVİN": [41.1828, 41.8183], "AYDIN": [37.8560, 27.8416],
    "BALIKESİR": [39.6484, 27.8826], "BİLECİK": [40.1451, 29.9799], "BİNGÖL": [38.8854, 40.4983],
    "BİTLİS": [38.3938, 42.1232], "BOLU": [40.7350, 31.6061], "BURDUR": [37.4613, 30.0665],
    "BURSA": [40.1885, 29.0610], "ÇANAKKALE": [40.1553, 26.4142], "ÇANKIRI": [40.6013, 33.6134],
    "ÇORUM": [40.5506, 34.9556], "DENİZLİ": [37.7765, 29.0864], "DİYARBAKIR": [37.9144, 40.2306],
    "EDİRNE": [41.6768, 26.5603], "ELAZIĞ": [38.6810, 39.2264], "ERZİNCAN": [39.7500, 39.5000],
    "ERZURUM": [39.9043, 41.2679], "ESKİŞEHİR": [39.7767, 30.5206], "GAZİANTEP": [37.0662, 37.3833],
    "GİRESUN": [40.9128, 38.3895], "GÜMÜŞHANE": [40.4600, 39.4700], "HAKKARİ": [37.5833, 43.7333],
    "HATAY": [36.4018, 36.3498], "ISPARTA": [37.7648, 30.5566], "MERSİN": [36.8000, 34.6333],
    "İSTANBUL": [41.0082, 28.9784], "İZMİR": [38.4189, 27.1287], "KARS": [40.6172, 43.0974],
    "KASTAMONU": [41.3887, 33.7827], "KAYSERİ": [38.7312, 35.4787], "KIRKLARELİ": [41.7333, 27.2167],
    "KIRŞEHİR": [39.1425, 34.1709], "KOCAELİ": [40.8533, 29.8815], "KONYA": [37.8667, 32.4833],
    "KÜTAHYA": [39.4167, 29.9833], "MALATYA": [38.3552, 38.3095], "MANİSA": [38.6191, 27.4289],
    "KAHRAMANMARAŞ": [37.5858, 36.9371], "MARDİN": [37.3212, 40.7245], "MUĞLA": [37.2153, 28.3636],
    "MUŞ": [38.9462, 41.7539], "NEVŞEHİR": [38.6244, 34.7144], "NİĞDE": [37.9667, 34.6833],
    "ORDU": [40.9839, 37.8764], "RİZE": [41.0201, 40.5234], "SAKARYA": [40.7569, 30.3783],
    "SAMSUN": [41.2928, 36.3313], "SİİRT": [37.9333, 41.9500], "SİNOP": [42.0231, 35.1531],
    "SİVAS": [39.7477, 37.0179], "TEKİRDAĞ": [40.9833, 27.5167], "TOKAT": [40.3167, 36.5500],
    "TRABZON": [41.0015, 39.7178], "TUNCELİ": [39.1079, 39.5401], "ŞANLIURFA": [37.1591, 38.7969],
    "UŞAK": [38.6823, 29.4082], "VAN": [38.4891, 43.4089], "YOZGAT": [39.8181, 34.8147],
    "ZONGULDAK": [41.4564, 31.7987], "AKSARAY": [38.3687, 34.0370], "BAYBURT": [40.2552, 40.2249],
    "KARAMAN": [37.1759, 33.2287], "KIRIKKALE": [39.8468, 33.5153], "BATMAN": [37.8812, 41.1291],
    "ŞIRNAK": [37.4187, 42.4918], "BARTIN": [41.6344, 32.3375], "ARDAHAN": [41.1105, 42.7022],
    "IĞDIR": [39.9196, 44.0459], "YALOVA": [40.6500, 29.2667], "KARABÜK": [41.2061, 32.6204],
    "KİLİS": [36.7184, 37.1212], "OSMANİYE": [37.0742, 36.2467], "DÜZCE": [40.8438, 31.1565]
}

# --- 5. BÖLGE TANIMLARI ---
BOLGE_TANIMLARI = {
    "Orta Anadolu": [
        "DÜZCE", "KARABÜK", "KONYA", "BOLU", "AFYONKARAHİSAR",
        "AKSARAY", "ESKİŞEHİR", "ANKARA", "KIRIKKALE", "KASTAMONU",
        "ÇANKIRI", "YOZGAT", "KIRŞEHİR", "KAYSERİ", "NEVŞEHİR",
        "NİĞDE", "ZONGULDAK", "BARTIN"
    ]
}

# --- 6. EXCEL VERİ YÜKLEME ---
@st.cache_data
def load_data(file_path):
    if not os.path.exists(file_path): return None, None, None
    try:
        df = pd.read_excel(file_path)
        df.columns = [str(c).strip() for c in df.columns]
        
        # Sütun ismi Dağıtıcı ise Dağıtım Şirketi yapıyoruz (standart için)
        if 'Dağıtıcı' in df.columns and 'Dağıtım Şirketi' not in df.columns:
            df.rename(columns={'Dağıtıcı': 'Dağıtım Şirketi'}, inplace=True)
        
        # Tarih formatlarını düzenle
        date_cols = ['Lisans Başlangıç Tarihi', 'Lisans Bitiş Tarihi',
                     'Dağıtıcı ile Yapılan Sözleşme Başlangıç Tarihi',
                     'Dağıtıcı ile Yapılan Sözleşme Bitiş Tarihi']
        for col in date_cols:
            if col in df.columns: df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce')

        target_col = 'Dağıtıcı ile Yapılan Sözleşme Bitiş Tarihi'
        if target_col not in df.columns: target_col = 'Lisans Bitiş Tarihi'
        
        start_col = 'Dağıtıcı ile Yapılan Sözleşme Başlangıç Tarihi'
        if start_col not in df.columns: start_col = 'Lisans Başlangıç Tarihi'

        today = pd.to_datetime(datetime.date.today())
        if target_col in df.columns:
            df['Kalan_Gun'] = (df[target_col] - today).dt.days
            df['Bitis_Yili'] = df[target_col].dt.year
            month_map = {1: 'Ocak', 2: 'Şubat', 3: 'Mart', 4: 'Nisan', 5: 'Mayıs', 6: 'Haziran', 7: 'Temmuz', 8: 'Ağustos', 9: 'Eylül', 10: 'Ekim', 11: 'Kasım', 12: 'Aralık'}
            df['Bitis_Ayi_No'] = df[target_col].dt.month
            df['Bitis_Ayi'] = df['Bitis_Ayi_No'].map(month_map)
        else:
            df['Kalan_Gun'] = np.nan
            df['Bitis_Yili'] = np.nan

        if start_col in df.columns and target_col in df.columns:
            df['Sozlesme_Suresi_Gun'] = (df[target_col] - df[start_col]).dt.days
        else:
            df['Sozlesme_Suresi_Gun'] = np.nan

        def get_risk(days):
            if pd.isna(days): return "Bilinmiyor"
            if days < 0: return "SÜRESİ DOLDU 🚨"
            if days < 90: return "KRİTİK (<3 Ay) ⚠️"
            if days < 180: return "YAKLAŞIYOR (<6 Ay) ⏳"
            return "GÜVENLİ ✅"
        df['Risk_Durumu'] = df['Kalan_Gun'].apply(get_risk)

        if 'İl' in df.columns: df['İl'] = df['İl'].astype(str).str.upper().str.replace('i', 'İ').str.replace('ı', 'I')
        if 'İlçe' in df.columns: df['İlçe'] = df['İlçe'].astype(str).str.upper().str.replace('i', 'İ').str.replace('ı', 'I')
        return df, target_col, start_col
    except Exception as e: return None, str(e), None

# --- DETAY TABLOSU ---
def show_details_table(dataframe, target_date_col, extra_cols=None):
    if dataframe is None or dataframe.empty:
        st.info("Kayıt bulunamadı.")
        return
    
    # Görselleştirme için limit ve Excel indirme butonu
    record_count = len(dataframe)
    cols = ['Unvan', 'İl', 'İlçe', 'Dağıtım Şirketi', target_date_col, 'Kalan_Gun', 'Risk_Durumu']
    if extra_cols: cols.extend(extra_cols)
    
    display_df = dataframe[cols].copy() if all(c in dataframe.columns for c in cols) else dataframe.head(MAX_ROW_DISPLAY)
    
    st.markdown(f"**📋 Listelenen Bayi Sayısı:** {record_count}")
    st.dataframe(display_df, use_container_width=True, hide_index=True)

# --- ANA UYGULAMA ---
def main():
    data_result = load_data(SABIT_DOSYA_ADI)
    if data_result is None or data_result[0] is None:
        st.error(f"⚠️ Hata: {SABIT_DOSYA_ADI} dosyası bulunamadı veya okunamadı.")
        st.stop()
    df, target_date_col, start_date_col = data_result

    with st.sidebar:
        st.title("🔍 LPG Filtre Paneli")
        
        region_options = ["Tümü"] + list(BOLGE_TANIMLARI.keys())
        selected_region = st.selectbox("🌍 Bölge Seç", region_options)
        
        if selected_region != "Tümü":
            df_sidebar = df[df['İl'].isin(BOLGE_TANIMLARI[selected_region])]
        else: df_sidebar = df.copy()

        all_cities = sorted(df_sidebar['İl'].unique().tolist())
        selected_cities = st.multiselect("🏢 Şehir Seç", all_cities)

        all_companies = sorted(df['Dağıtım Şirketi'].dropna().unique().tolist())
        selected_companies = st.multiselect("⛽ Şirket Seç", all_companies)

    # Filtreleme İşlemi
    df_filtered = df.copy()
    if selected_region != "Tümü": df_filtered = df_filtered[df_filtered['İl'].isin(BOLGE_TANIMLARI[selected_region])]
    if selected_cities: df_filtered = df_filtered[df_filtered['İl'].isin(selected_cities)]
    if selected_companies: df_filtered = df_filtered[df_filtered['Dağıtım Şirketi'].isin(selected_companies)]

    # --- KPI EKRANI ---
    st.title("🚀 LPG Pazar & Risk Analizi")
    c1, c2, c3 = st.columns(3)
    c1.metric("Toplam LPG İstasyonu", f"{len(df_filtered):,}")
    acil = len(df_filtered[df_filtered['Kalan_Gun'] < 90]) if 'Kalan_Gun' in df_filtered.columns else 0
    c2.metric("Kritik Sözleşme (<90 Gün)", acil, delta_color="inverse")
    c3.metric("Aktif Dağıtıcı Sayısı", df_filtered['Dağıtım Şirketi'].nunique())

    st.divider()

    # --- SEKMELER ---
    tabs = st.tabs(["📊 Genel Bakış", "🤖 Makine Analizi", "📅 Takvim", "📍 İlçe Analizi", "📋 Ham Veri"])

    # 1. Genel Bakış (Harita ve Pie)
    with tabs[0]:
        col_map, col_pie = st.columns([2, 1])
        with col_map:
            st.subheader("🗺️ Bölgesel Yoğunluk")
            map_data = df_filtered['İl'].value_counts().reset_index()
            map_data.columns = ['İl', 'Adet']
            map_data['lat'] = map_data['İl'].map(lambda x: CITY_COORDINATES.get(x, [0,0])[0])
            map_data['lon'] = map_data['İl'].map(lambda x: CITY_COORDINATES.get(x, [0,0])[1])
            fig_map = px.scatter_mapbox(map_data, lat="lat", lon="lon", size="Adet", color="Adet",
                                        hover_name="İl", mapbox_style="open-street-map", zoom=4.5)
            st.plotly_chart(fig_map, use_container_width=True)
        
        with col_pie:
            st.subheader("📈 Pazar Payı")
            dist_data = df_filtered['Dağıtım Şirketi'].value_counts().head(10)
            fig_pie = px.pie(values=dist_data.values, names=dist_data.index, hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)

    # 2. Makine Analizi (Akıllı Öneriler)
    with tabs[1]:
        st.subheader("🤖 Stratejik Analiz Notları")
        # Örnek: Güzel Enerji için analiz yapalım (LPG dosyasındaki adını kontrol etmelisin)
        my_company = "GÜZEL ENERJİ AKARYAKIT ANONİM ŞİRKETİ" 
        my_df = df_filtered[df_filtered['Dağıtım Şirketi'] == my_company]
        
        if not my_df.empty:
            st.markdown(f"<div class='insight-box-success'>✅ <b>Hakimiyet:</b> Bu filtrelerde toplam <b>{len(my_df)}</b> bayiniz bulunuyor.</div>", unsafe_allow_html=True)
            
            # Eksik ilçeleri bulma
            all_dists = set(df_filtered['İlçe'].unique())
            my_dists = set(my_df['İlçe'].unique())
            missing = sorted(list(all_dists - my_dists))
            if missing:
                st.markdown(f"<div class='insight-box-warning'>🚀 <b>Fırsat:</b> Hiç bayinizin olmadığı <b>{len(missing)}</b> ilçe var. Rakip istilası olabilir!</div>", unsafe_allow_html=True)
                with st.expander("İlçeleri Gör"):
                    st.write(", ".join(missing))
        else:
            st.info("Seçili filtrelerde analiz edilecek şirket verisi bulunamadı.")

    # 3. Takvim
    with tabs[2]:
        if 'Bitis_Yili' in df_filtered.columns:
            st.subheader("📅 Yıllık Bitiş Projeksiyonu")
            proj = df_filtered['Bitis_Yili'].value_counts().sort_index()
            fig_proj = px.bar(x=proj.index, y=proj.values, labels={'x':'Yıl', 'y':'Bayi Sayısı'})
            st.plotly_chart(fig_proj, use_container_width=True)

    # 4. İlçe Analizi
    with tabs[3]:
        st.subheader("📍 İlçe Bazlı Derinlik")
        ilce_data = df_filtered['İlçe'].value_counts().head(20).sort_values()
        fig_ilce = px.bar(x=ilce_data.values, y=ilce_data.index, orientation='h', title="En Çok İstasyon Olan 20 İlçe")
        st.plotly_chart(fig_ilce, use_container_width=True)

    # 5. Ham Veri
    with tabs[4]:
        st.subheader("📋 Veri Listesi")
        show_details_table(df_filtered, target_date_col)

if __name__ == "__main__":
    main()
