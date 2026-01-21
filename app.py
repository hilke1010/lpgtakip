import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import numpy as np
import os
import io

# --- 1. SAYFA VE GENEL AYARLAR ---
st.set_page_config(
    page_title="EPDK LPG Pazar Analizi",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. DOSYA İSİMLERİ & SABİTLER ---
SABIT_DOSYA_ADI = "lpg.xlsx"
MY_COMPANY = "LİKİTGAZ DAĞITIM VE ENDÜSTRİ ANONİM ŞİRKETİ"

# --- PERFORMANS ---
MAX_ROW_DISPLAY = 1000  

# --- CRM & ÖZEL NOTLAR SESSION STATE ---
if 'crm_notes' not in st.session_state:
    st.session_state.crm_notes = {}
if 'likitgaz_custom_notes' not in st.session_state:
    st.session_state.likitgaz_custom_notes = pd.DataFrame(columns=['Unvan', 'Not'])

# --- 3. CSS ÖZELLEŞTİRME ---
st.markdown("""
<style>
    .stMetric { background-color: #f0f2f6; border-left: 5px solid #e67e22; padding: 15px; border-radius: 5px; }
    .insight-box-success { padding: 15px; border-radius: 8px; background-color: #d4edda; border-left: 5px solid #28a745; margin-bottom: 10px; }
    .insight-box-warning { padding: 15px; border-radius: 8px; background-color: #fff3cd; border-left: 5px solid #ffc107; margin-bottom: 10px; }
    .insight-box-danger { padding: 15px; border-radius: 8px; background-color: #f8d7da; border-left: 5px solid #dc3545; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# --- 4. KOORDİNAT VERİTABANI ---
CITY_COORDINATES = {
    "ADANA": [37.00, 35.32], "ADIYAMAN": [37.76, 38.27], "AFYONKARAHİSAR": [38.75, 30.55],
    "ANKARA": [39.93, 32.85], "ANTALYA": [36.89, 30.71], "BURSA": [40.18, 29.06],
    "İSTANBUL": [41.00, 28.97], "İZMİR": [38.41, 27.12], "KOCAELİ": [40.85, 29.88],
    "TEKİRDAĞ": [40.98, 27.51], "BALIKESİR": [39.64, 27.88], "SAKARYA": [40.75, 30.37],
    "EDİRNE": [41.67, 26.56], "BİLECİK": [40.14, 29.97], "ÇANAKKALE": [40.15, 26.41],
    "KIRKLARELİ": [41.73, 27.21], "YALOVA": [40.65, 29.26]
    # ... Diğer iller akaryakıt kodundaki ile aynıdır ...
}

# --- 5. BÖLGE TANIMLARI (MARMARA EKLENDİ) ---
BOLGE_TANIMLARI = {
    "Marmara Bölgesi": [
        "İSTANBUL", "BALIKESİR", "BURSA", "SAKARYA", "EDİRNE", 
        "BİLECİK", "ÇANAKKALE", "TEKİRDAĞ", "KIRKLARELİ", "KOCAELİ", "YALOVA"
    ],
    "Orta Anadolu": [
        "DÜZCE", "KARABÜK", "KONYA", "BOLU", "AFYONKARAHİSAR",
        "AKSARAY", "ESKİŞEHİR", "ANKARA", "KIRIKKALE", "KASTAMONU",
        "ÇANKIRI", "YOZGAT", "KIRŞEHİR", "KAYSERİ", "NEVŞEHİR", "NİĞDE", "ZONGULDAK", "BARTIN"
    ]
}

# --- 6. VERİ YÜKLEME ---
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

        today = pd.to_datetime(datetime.date.today())
        if target_col in df.columns:
            df['Kalan_Gun'] = (df[target_col] - today).dt.days
            df['Bitis_Yili'] = df[target_col].dt.year
            df['Bitis_Ayi_No'] = df[target_col].dt.month
            month_map = {1:'Ocak', 2:'Şubat', 3:'Mart', 4:'Nisan', 5:'Mayıs', 6:'Haziran', 
                         7:'Temmuz', 8:'Ağustos', 9:'Eylül', 10:'Ekim', 11:'Kasım', 12:'Aralık'}
            df['Bitis_Ayi'] = df['Bitis_Ayi_No'].map(month_map)
        
        if start_col in df.columns and target_col in df.columns:
            df['Sozlesme_Suresi_Gun'] = (df[target_col] - df[start_col]).dt.days

        # Yazım düzeltmeleri
        for c in ['İl', 'İlçe']:
            if c in df.columns: df[c] = df[c].astype(str).str.upper().str.replace('i', 'İ').str.replace('ı', 'I')
            
        return df, target_col, start_col
    except Exception as e: return None, str(e), None

# --- DETAY TABLOSU ---
def show_details_table(dataframe, target_date_col):
    if dataframe is None or dataframe.empty:
        st.info("Kayıt bulunamadı.")
        return
    cols = ['Unvan', 'İl', 'İlçe', 'Dağıtım Şirketi', target_date_col, 'Kalan_Gun', 'Risk_Durumu']
    final_cols = [c for c in cols if c in dataframe.columns]
    st.dataframe(dataframe[final_cols].sort_values('Kalan_Gun'), use_container_width=True, hide_index=True)

# --- ANA UYGULAMA ---
def main():
    data_result = load_data(SABIT_DOSYA_ADI)
    if data_result is None or data_result[0] is None:
        st.error("Veri dosyası (lpg.xlsx) yüklenemedi.")
        st.stop()
    df, target_date_col, start_date_col = data_result

    # Sidebar Filtreleri
    with st.sidebar:
        st.title("🔍 LPG Filtre Paneli")
        selected_region = st.selectbox("🌍 Bölge Seç", ["Tümü"] + list(BOLGE_TANIMLARI.keys()))
        
        filtered_df = df.copy()
        if selected_region != "Tümü":
            filtered_df = filtered_df[filtered_df['İl'].isin(BOLGE_TANIMLARI[selected_region])]

        selected_cities = st.multiselect("🏢 Şehir Seç", sorted(filtered_df['İl'].unique().tolist()))
        if selected_cities: filtered_df = filtered_df[filtered_df['İl'].isin(selected_cities)]

        selected_companies = st.multiselect("⛽ Şirket Seç", sorted(df['Dağıtım Şirketi'].dropna().unique().tolist()))
        if selected_companies: filtered_df = filtered_df[filtered_df['Dağıtım Şirketi'].isin(selected_companies)]

    st.title("🚀 LPG Pazar & Sözleşme Analizi")
    c1, c2, c3 = st.columns(3)
    c1.metric("Toplam İstasyon", f"{len(filtered_df):,}")
    c2.metric("Likitgaz İstasyon", f"{len(filtered_df[filtered_df['Dağıtım Şirketi']==MY_COMPANY]):,}")
    c3.metric("Kritik Bayi (<90 Gün)", len(filtered_df[filtered_df['Kalan_Gun'] < 90]))

    st.divider()

    # --- SEKMELER ---
    tabs = st.tabs([
        "📊 Bölgesel Durum", 
        "🤖 Makine Analizi", 
        "📅 Takvim", 
        "📋 Likitgaz Sözleşme Takibi", # Yeni Tab
        "📡 Radar", 
        "📍 İlçe Analizi", 
        "📋 Ham Veri"
    ])

    # 1. BÖLGESEL DURUM
    with tabs[0]:
        st.subheader("📊 Şehir Dağılımı")
        city_counts = filtered_df['İl'].value_counts().reset_index().head(20)
        city_counts.columns = ['İl', 'Adet']
        # Üzerine sayı eklenmiş çubuk grafik
        fig_city = px.bar(city_counts, x='İl', y='Adet', text='Adet', color='Adet', title="En Çok İstasyon Olan İller")
        fig_city.update_traces(textposition='outside')
        st.plotly_chart(fig_city, use_container_width=True)
        show_details_table(filtered_df, target_date_col)

    # 2. MAKİNE ANALİZİ
    with tabs[1]:
        st.subheader("🤖 Stratejik Analiz Notları")
        my_df = filtered_df[filtered_df['Dağıtım Şirketi'] == MY_COMPANY]
        if not my_df.empty:
            st.markdown(f"<div class='insight-box-success'>✅ <b>Hakimiyet:</b> Bu bölgede <b>{len(my_df)}</b> adet Likitgaz bayisi aktif.</div>", unsafe_allow_html=True)
            missing = sorted(list(set(filtered_df['İlçe'].unique()) - set(my_df['İlçe'].unique())))
            if missing:
                st.markdown(f"<div class='insight-box-warning'>🚀 <b>Fırsat:</b> Hiç bayinizin olmadığı <b>{len(missing)}</b> ilçe var.</div>", unsafe_allow_html=True)
                with st.expander("İlçeleri Gör"): st.write(", ".join(missing))
        else: st.info("Seçili filtrelerde Likitgaz verisi yok.")

    # 3. TAKVİM (SIRALAMA DÜZELTİLDİ)
    with tabs[2]:
        st.subheader("📅 Aylık Sözleşme Bitiş Takvimi")
        yrs = sorted(filtered_df['Bitis_Yili'].dropna().unique().astype(int).tolist())
        if yrs:
            sel_yr = st.selectbox("Yıl Seçin", yrs, index=yrs.index(datetime.date.today().year) if datetime.date.today().year in yrs else 0)
            df_yr = filtered_df[filtered_df['Bitis_Yili'] == sel_yr]
            
            # Ay sırasına göre grupla (Bitis_Ayi_No ile sırala)
            m_cnt = df_yr.groupby(['Bitis_Ayi_No', 'Bitis_Ayi']).size().reset_index(name='Adet').sort_values('Bitis_Ayi_No')
            
            fig_cal = px.bar(m_cnt, x='Bitis_Ayi', y='Adet', text='Adet', title=f"{sel_yr} Yılı Bitiş Dağılımı")
            fig_cal.update_traces(textposition='outside')
            # Grafik üzerinde sıralamayı zorla
            fig_cal.update_xaxes(categoryorder='array', categoryarray=m_cnt['Bitis_Ayi'].tolist())
            st.plotly_chart(fig_cal, use_container_width=True)
            show_details_table(df_yr, target_date_col)

    # 4. LİKİTGAZ SÖZLEŞME TAKİBİ (YENİ TAB)
    with tabs[3]:
        st.subheader(f"📋 {MY_COMPANY} Sözleşme & Not Takibi")
        st.info("Bu tabloda sadece şirketinizin bayileri listelenir. Sağdaki 'Not' sütununa tıklayarak özel notlarınızı ekleyebilirsiniz.")
        
        # Sadece Likitgaz ve filtreye göre
        likit_df_all = df[df['Dağıtım Şirketi'] == MY_COMPANY].copy()
        
        # Yıl filtresi (Tab içine özel)
        likit_yrs = sorted(likit_df_all['Bitis_Yili'].dropna().unique().astype(int).tolist())
        sel_likit_yr = st.selectbox("Sözleşme Bitiş Yılı Seçin", ["Tümü"] + likit_yrs, key="likit_yr_sel")
        
        likit_display = likit_df_all.copy()
        if sel_likit_yr != "Tümü":
            likit_display = likit_display[likit_display['Bitis_Yili'] == sel_likit_yr]

        # Gerekli Sütunlar
        cols_to_show = ['Unvan', 'İletişim Adresi', 'Lisans Başlangıç Tarihi', 'Lisans Bitiş Tarihi', 'Kalan_Gun']
        likit_table = likit_display[cols_to_show].copy()
        likit_table.rename(columns={'İletişim Adresi': 'Adres', 'Lisans Başlangıç Tarihi': 'Başlangıç', 'Lisans Bitiş Tarihi': 'Bitiş'}, inplace=True)
        
        # Tarih formatlama
        for c in ['Başlangıç', 'Bitiş']: 
            likit_table[c] = likit_table[c].dt.strftime('%d.%m.%Y')

        # Not sütunu ekle (Session state'den çek)
        if 'notlar_df' not in st.session_state:
            st.session_state.notlar_df = pd.DataFrame(columns=['Unvan', 'Özel Not'])

        # Mevcut notları birleştir
        likit_table = pd.merge(likit_table, st.session_state.notlar_df, on='Unvan', how='left').fillna("")

        # İnteraktif Tablo (Data Editor)
        edited_df = st.data_editor(
            likit_table,
            column_config={
                "Özel Not": st.column_config.TextColumn("Özel Not (Düzenlemek için tıklayın)", width="large"),
                "Kalan_Gun": st.column_config.NumberColumn("Kalan Gün", format="%d")
            },
            disabled=["Unvan", "Adres", "Başlangıç", "Bitiş", "Kalan Gün"],
            hide_index=True,
            use_container_width=True,
            key="likit_editor"
        )

        # Değişiklikleri kaydet butonu
        if st.button("Notları Sisteme Kaydet"):
            st.session_state.notlar_df = edited_df[['Unvan', 'Özel Not']]
            st.success("Notlar başarıyla güncellendi!")

    # 5. RADAR
    with tabs[4]:
        st.subheader("📡 Radar (Kritik Dönem)")
        radar_df = filtered_df[filtered_df['Kalan_Gun'] < 180]
        show_details_table(radar_df, target_date_col)

    # 6. İLÇE ANALİZİ
    with tabs[5]:
        st.subheader("📍 İlçe Bazlı Dağılım")
        ilce_counts = filtered_df['İlçe'].value_counts().reset_index().head(20)
        ilce_counts.columns = ['İlçe', 'Adet']
        fig_ilce = px.bar(ilce_counts, x='Adet', y='İlçe', text='Adet', orientation='h', title="En Çok İstasyon Olan 20 İlçe")
        fig_ilce.update_traces(textposition='outside')
        st.plotly_chart(fig_ilce, use_container_width=True)

    # 7. HAM VERİ
    with tabs[6]:
        st.subheader("📋 Tüm Liste")
        st.dataframe(filtered_df, use_container_width=True)

if __name__ == "__main__":
    main()
