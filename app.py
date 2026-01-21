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
SABIT_DOSYA_ADI = "lpg.xlsx" # 1'e 1 Dosya Değişimi

# --- 3. CSS ÖZELLEŞTİRME (AKARYAKIT İLE AYNI YAPI) ---
st.markdown("""
<style>
    .stMetric {
        background-color: #f0f2f6;
        border-left: 5px solid #e67e22; 
        padding: 15px;
        border-radius: 5px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    .block-container { padding-top: 2rem; }
    .crm-box {
        background-color: #fff9c4;
        padding: 10px;
        border-radius: 5px;
        border: 1px solid #fbc02d;
        margin-bottom: 10px;
    }
    .warning-box {
        padding: 1rem;
        background-color: #ffeba0;
        border-left: 6px solid #ffa500;
        color: #5c3a00;
        border-radius: 4px;
        font-weight: bold;
    }
    .year-box {
        background-color: #e8f4f8;
        padding: 10px;
        border-radius: 5px;
        text-align: center;
        border: 1px solid #b3e5fc;
        margin-bottom: 5px;
    }
    .year-title { font-weight: bold; color: #0277bd; font-size: 1.1em; }
    .year-count { font-size: 1.5em; font-weight: bold; color: #01579b; }
    
    .insight-box-success { padding: 15px; border-radius: 8px; background-color: #d4edda; border-left: 5px solid #28a745; color: #155724; margin-bottom: 10px; }
    .insight-box-warning { padding: 15px; border-radius: 8px; background-color: #fff3cd; border-left: 5px solid #ffc107; color: #856404; margin-bottom: 10px; }
    .insight-box-danger { padding: 15px; border-radius: 8px; background-color: #f8d7da; border-left: 5px solid #dc3545; color: #721c24; margin-bottom: 10px; }
    .insight-box-info { padding: 15px; border-radius: 8px; background-color: #d1ecf1; border-left: 5px solid #17a2b8; color: #0c5460; margin-bottom: 10px; }
    .district-chip { display: inline-block; background-color: #f1f3f5; padding: 5px 10px; margin: 3px; border-radius: 15px; font-size: 0.9em; border: 1px solid #ddd; cursor: help; }
    .district-chip:hover { background-color: #e2e6ea; border-color: #adb5bd; }
</style>
""", unsafe_allow_html=True)

# --- 4. KOORDİNAT VERİTABANI ---
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

# --- CRM SESSION ---
if 'crm_notes' not in st.session_state:
    st.session_state.crm_notes = {}

# --- 6. EXCEL VERİ YÜKLEME ---
@st.cache_data
def load_data(file_path):
    if not os.path.exists(file_path): return None, None, None
    try:
        df = pd.read_excel(file_path)
        df.columns = [str(c).strip() for c in df.columns]
        if 'Dağıtıcı' in df.columns and 'Dağıtım Şirketi' not in df.columns:
            df.rename(columns={'Dağıtıcı': 'Dağıtım Şirketi'}, inplace=True)
        
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
            df['Bitis_Ayi'] = np.nan
            df['Bitis_Ayi_No'] = np.nan

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
        st.info("Seçilen kriterlere uygun kayıt bulunamadı.")
        return
    record_count = len(dataframe)
    
    if record_count > MAX_ROW_DISPLAY:
        st.markdown(f"<div class='warning-box'>⚠️ <b>Performans Uyarısı:</b> Listede toplam <b>{record_count:,}</b> kayıt var.<br>Aşağıda sadece ilk <b>{MAX_ROW_DISPLAY:,}</b> tanesi gösterilmektedir.</div>", unsafe_allow_html=True)
        display_df_limit = dataframe.head(MAX_ROW_DISPLAY)
    else:
        display_df_limit = dataframe

    cols = ['Unvan', 'İl', 'İlçe', 'Dağıtım Şirketi', target_date_col, 'Kalan_Gun', 'Sozlesme_Suresi_Gun', 'Risk_Durumu']
    if extra_cols: cols.extend(extra_cols)
    
    seen = set()
    final_cols = [c for c in cols if c in display_df_limit.columns and not (c in seen or seen.add(c))]
    display_df = display_df_limit[final_cols].copy()
    
    date_columns = [col for col in display_df.columns if "Tarihi" in col or "Tarih" in col]
    for date_col in date_columns:
        try: display_df[date_col] = pd.to_datetime(display_df[date_col]).dt.strftime('%d.%m.%Y')
        except: pass

    if 'Kalan_Gun' in display_df.columns: display_df = display_df.sort_values('Kalan_Gun')
    
    st.markdown(f"**📋 Listelenen Bayi Sayısı:** {len(display_df)}")
    
    if record_count > 0:
        buffer = io.BytesIO()
        try:
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                dataframe.to_excel(writer, index=False, sheet_name='LPG_Bayi_Listesi')
            st.download_button(label=f"📥 Tüm Listeyi Excel İndir ({record_count} Kayıt)", data=buffer.getvalue(), file_name="LPG_Bayi_Listesi.xlsx", mime="application/vnd.ms-excel")
        except: pass

    st.dataframe(display_df, use_container_width=True, hide_index=True)

# --- ANA UYGULAMA ---
def main():
    data_result = load_data(SABIT_DOSYA_ADI)
    if data_result is None or data_result[0] is None:
        st.error(f"⚠️ Hata: {SABIT_DOSYA_ADI} dosyası bulunamadı.")
        st.stop()
    df, target_date_col, start_date_col = data_result

    # ÖNEMLİ: Şirket Adı Güncellemesi
    MY_COMPANY = "LİKİTGAZ DAĞITIM VE ENDÜSTRİ ANONİM ŞİRKETİ"

    with st.sidebar:
        st.info("🕒 LPG verileri her gün saat 10:00'da yenilenmektedir.")
        st.markdown("---")
        st.title("🔍 Filtre Paneli")
        
        region_options = ["Tümü"] + list(BOLGE_TANIMLARI.keys())
        selected_region = st.selectbox("🌍 Bölge Seç", region_options)
        if selected_region != "Tümü":
            target_cities = BOLGE_TANIMLARI[selected_region]
            df_for_sidebar = df[df['İl'].isin(target_cities)]
        else: df_for_sidebar = df.copy()

        all_cities = sorted(df_for_sidebar['İl'].unique().tolist()) if 'İl' in df_for_sidebar.columns else []
        selected_cities = st.multiselect("🏢 Şehir Seç", all_cities)

        if selected_cities:
            filtered_districts = sorted(df_for_sidebar[df_for_sidebar['İl'].isin(selected_cities)]['İlçe'].unique().tolist())
        else:
            filtered_districts = sorted(df_for_sidebar['İlçe'].unique().tolist()) if 'İlçe' in df_for_sidebar.columns else []
        selected_districts = st.multiselect("📍 İlçe Seç", filtered_districts)

        all_companies = sorted(df['Dağıtım Şirketi'].dropna().astype(str).unique().tolist()) if 'Dağıtım Şirketi' in df.columns else []
        selected_companies = st.multiselect("⛽ Şirket Seç", all_companies)

        st.markdown("---")
        st.header("🔗 Uygulamalar")
        st.markdown("[📊 EPDK LPG Sektör Raporu](https://pazarpayi.streamlit.app/)")

    # Filtreleme
    df_filtered = df.copy()
    if selected_region != "Tümü": df_filtered = df_filtered[df_filtered['İl'].isin(BOLGE_TANIMLARI[selected_region])]
    if selected_cities: df_filtered = df_filtered[df_filtered['İl'].isin(selected_cities)]
    if selected_districts: df_filtered = df_filtered[df_filtered['İlçe'].isin(selected_districts)]
    
    df_filtered_geo_only = df_filtered.copy()
    if selected_companies: df_filtered = df_filtered[df_filtered['Dağıtım Şirketi'].isin(selected_companies)]

    # --- KPI ---
    st.title("🔥 LPG Pazar & Risk Analizi")
    c1, c2, c3 = st.columns(3)
    c1.metric("Toplam LPG İstasyonu", f"{len(df_filtered):,}")
    acil_durum = len(df_filtered[df_filtered['Kalan_Gun'] < 90]) if 'Kalan_Gun' in df_filtered.columns else 0
    c2.metric("Acil Sözleşme", acil_durum, delta="Kritik", delta_color="inverse")
    aktif_dagitici = df_filtered['Dağıtım Şirketi'].nunique() if 'Dağıtım Şirketi' in df_filtered.columns else 0
    c3.metric("Aktif Dağıtıcı", aktif_dagitici)
    
    st.divider()

    # --- SEKMELER ---
    tab_overview, tab_machine, tab_compare, tab_sim, tab_calendar, tab_radar, tab_ilce, tab_report, tab_crm, tab_data = st.tabs([
        "📊 Bölgesel & Durum",
        "🤖 Makine Analizi",     
        "⚔️ Karşılaştırma", 
        "🔮 Simülasyon",         
        "📅 Takvim",
        "📡 Sözleşme Radar", 
        "📍 İlçe Analizi",
        "📄 İl Karnesi", 
        "📝 CRM Lite",           
        "📋 Ham Veri"
    ])

    # 1. BÖLGESEL & DURUM
    with tab_overview:
        st.subheader("🗺️ LPG Yoğunluk Haritası")
        if not df_filtered.empty:
            map_data = df_filtered['İl'].value_counts().reset_index()
            map_data.columns = ['İl', 'Adet']
            map_data['lat'] = map_data['İl'].map(lambda x: CITY_COORDINATES.get(x, [None, None])[0])
            map_data['lon'] = map_data['İl'].map(lambda x: CITY_COORDINATES.get(x, [None, None])[1])
            map_data = map_data.dropna(subset=['lat', 'lon'])
            fig_map = px.scatter_mapbox(map_data, lat="lat", lon="lon", size="Adet", color="Adet",
                                        hover_name="İl", size_max=35, zoom=4.8, 
                                        mapbox_style="open-street-map", color_continuous_scale='Bluered')
            st.plotly_chart(fig_map, use_container_width=True)

        st.divider()
        city_stats = df_filtered['İl'].value_counts().reset_index()
        city_stats.columns = ['İl', 'Total']
        my_df = df_filtered[df_filtered['Dağıtım Şirketi'] == MY_COMPANY]
        my_counts = my_df['İl'].value_counts().reset_index()
        my_counts.columns = ['İl', 'My_Count']
        merged = pd.merge(city_stats, my_counts, on='İl', how='left').fillna(0)
        
        fig_city = px.bar(merged, x='İl', y='Total', title=f"Şehir Sıralaması (Toplam & {MY_COMPANY} Payı)", color='Total')
        st.plotly_chart(fig_city, use_container_width=True)
        show_details_table(df_filtered, target_date_col)

    # 2. MAKİNE ANALİZİ
    with tab_machine:
        st.subheader("🤖 Makine Analizi")
        st.caption(f"📍 **Odak Şirket:** {MY_COMPANY}")
        
        my_scope_df = df_filtered[df_filtered['Dağıtım Şirketi'] == MY_COMPANY]
        
        if not my_scope_df.empty:
            top_city = my_scope_df['İl'].value_counts().idxmax()
            top_count = my_scope_df['İl'].value_counts().max()
            st.markdown(f"<div class='insight-box-success'><b>🏆 En Güçlü Kale:</b> {top_city} ({top_count} Bayi).</div>", unsafe_allow_html=True)

            all_dists = df_filtered['İlçe'].unique()
            my_dists = my_scope_df['İlçe'].unique()
            missing = sorted(list(set(all_dists) - set(my_dists)))
            if missing:
                st.markdown(f"<div class='insight-box-warning'><b>🚀 Boş Noktalar:</b> {len(missing)} ilçede bayiniz yok.</div>", unsafe_allow_html=True)
                with st.expander("İlçeleri Listele"):
                    st.write(", ".join(missing))
            
            if 'Bitis_Yili' in my_scope_df.columns:
                cur_yr = datetime.date.today().year
                exp = my_scope_df[my_scope_df['Bitis_Yili'] >= cur_yr]['Bitis_Yili'].value_counts().sort_index()
                if not exp.empty:
                    st.markdown(f"<div class='insight-box-danger'><b>⚠️ Yakın Bitişler:</b> {exp.sum()} adet sözleşme yenileme bekliyor.</div>", unsafe_allow_html=True)
        else: st.warning("Bu filtrelerde şirket verisi bulunamadı.")

    # 3. KARŞILAŞTIRMA
    with tab_compare:
        st.subheader("⚔️ Rakip Analizi")
        comp_list = sorted(df['Dağıtım Şirketi'].dropna().unique().tolist())
        if len(comp_list) >= 2:
            c_sel1, c_sel2 = st.columns(2)
            comp_a = c_sel1.selectbox("1. Şirket", comp_list, index=comp_list.index(MY_COMPANY) if MY_COMPANY in comp_list else 0)
            comp_b = c_sel2.selectbox("2. Şirket", comp_list, index=1)
            
            df_a = df_filtered_geo_only[df_filtered_geo_only['Dağıtım Şirketi'] == comp_a]
            df_b = df_filtered_geo_only[df_filtered_geo_only['Dağıtım Şirketi'] == comp_b]

            k1, k2 = st.columns(2)
            k1.metric(comp_a, len(df_a))
            k2.metric(comp_b, len(df_b), delta=len(df_b)-len(df_a))
            
            st.divider()
            df_vs = df_filtered_geo_only[df_filtered_geo_only['Dağıtım Şirketi'].isin([comp_a, comp_b])]
            fig_vs = px.bar(df_vs.groupby(['İl', 'Dağıtım Şirketi']).size().reset_index(name='Adet'), 
                            x='İl', y='Adet', color='Dağıtım Şirketi', barmode='group')
            st.plotly_chart(fig_vs, use_container_width=True)

    # 4. SİMÜLASYON
    with tab_sim:
        st.subheader("🔮 Dönüşüm Simülasyonu")
        all_comps = sorted(df['Dağıtım Şirketi'].dropna().unique().tolist())
        target_comps = [c for c in all_comps if c != MY_COMPANY]
        
        cc1, cc2 = st.columns(2)
        target = cc1.selectbox("Hedef Rakip", target_comps)
        rate = cc2.slider("Kazanma Oranı (%)", 0, 100, 10)
        
        if target:
            curr = len(df_filtered[df_filtered['Dağıtım Şirketi'] == MY_COMPANY])
            targ = len(df_filtered[df_filtered['Dağıtım Şirketi'] == target])
            gain = int(targ * rate / 100)
            st.metric("Potansiyel Yeni Toplam", curr + gain, delta=f"+{gain}")

    # 5. TAKVİM
    with tab_calendar:
        st.subheader("📅 Sözleşme Bitiş Takvimi")
        if 'Bitis_Yili' in df_filtered.columns:
            yrs = sorted(df_filtered['Bitis_Yili'].dropna().unique().astype(int).tolist())
            if yrs:
                sel_yr = st.selectbox("Yıl", yrs, index=yrs.index(datetime.date.today().year) if datetime.date.today().year in yrs else 0)
                df_yr = df_filtered[df_filtered['Bitis_Yili'] == sel_yr]
                m_cnt = df_yr.groupby(['Bitis_Ayi']).size().reset_index(name='Adet')
                st.plotly_chart(px.bar(m_cnt, x='Bitis_Ayi', y='Adet', title=f"{sel_yr} Aylık Dağılım"), use_container_width=True)
                show_details_table(df_yr, target_date_col)

    # 6. RADAR
    with tab_radar:
        st.subheader("📡 Sözleşme Radar")
        st.caption("3 aydan kısa süreli (şüpheli/yenilenmiş) sözleşmeleri tarar.")
        if 'Sozlesme_Suresi_Gun' in df_filtered.columns:
            radar_df = df_filtered[(df_filtered['Sozlesme_Suresi_Gun'] < 90) & (df_filtered['Sozlesme_Suresi_Gun'] >= 0)]
            show_details_table(radar_df, target_date_col)

    # 7. İLÇE ANALİZİ
    with tab_ilce:
        st.subheader("📍 İlçe Bazlı Derinlik")
        if not df_filtered.empty:
            d_cnt = df_filtered['İlçe'].value_counts().reset_index().head(20)
            d_cnt.columns = ['İlçe', 'Adet']
            st.plotly_chart(px.bar(d_cnt, x='Adet', y='İlçe', orientation='h'), use_container_width=True)

    # 8. İL KARNESİ
    with tab_report:
        st.subheader("📄 İl Karnesi")
        rep_city = st.selectbox("İl Seçin", sorted(df['İl'].unique()))
        if rep_city:
            city_df = df[df['İl'] == rep_city]
            rk1, rk2 = st.columns(2)
            rk1.metric("Toplam İstasyon", len(city_df))
            rk2.metric(f"{MY_COMPANY}", len(city_df[city_df['Dağıtım Şirketi'] == MY_COMPANY]))
            st.divider()
            st.plotly_chart(px.pie(city_df['Dağıtım Şirketi'].value_counts().head(5).reset_index(), values='count', names='Dağıtım Şirketi', title="Pazar Dağılımı"), use_container_width=True)

    # 9. CRM LITE
    with tab_crm:
        st.subheader("📝 CRM Notları")
        bayiler = sorted(df_filtered['Unvan'].unique().tolist())
        sel_b = st.selectbox("Bayi Seç", bayiler)
        note = st.text_area("Görüşme Notu")
        if st.button("Kaydet"):
            ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            if sel_b not in st.session_state.crm_notes: st.session_state.crm_notes[sel_b] = []
            st.session_state.crm_notes[sel_b].append(f"[{ts}] {note}")
            st.success("Not kaydedildi.")
        
        for b, ns in st.session_state.crm_notes.items():
            with st.expander(f"🏢 {b}"):
                for n in ns: st.write(n)

    # 10. HAM VERİ
    with tab_data:
        st.subheader("📋 Ham Veri")
        st.dataframe(df_filtered.head(PREVIEW_ROW_LIMIT), use_container_width=True)

if __name__ == "__main__":
    main()
