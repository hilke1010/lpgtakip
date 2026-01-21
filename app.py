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
MAX_ROW_DISPLAY = 1000  

# --- SESSION STATE ---
if 'notlar_df' not in st.session_state:
    st.session_state.notlar_df = pd.DataFrame(columns=['Unvan', 'Özel Not'])

# --- 3. CSS ÖZELLEŞTİRME ---
st.markdown("""
<style>
    .stMetric { background-color: #f0f2f6; border-left: 5px solid #e67e22; padding: 15px; border-radius: 5px; }
    .insight-box-success { padding: 15px; border-radius: 8px; background-color: #d4edda; border-left: 5px solid #28a745; margin-bottom: 10px; }
    .insight-box-warning { padding: 15px; border-radius: 8px; background-color: #fff3cd; border-left: 5px solid #ffc107; margin-bottom: 10px; }
    .insight-box-danger { padding: 15px; border-radius: 8px; background-color: #f8d7da; border-left: 5px solid #dc3545; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# --- 4. BÖLGE TANIMLARI (MARMARA EKLENDİ) ---
BOLGE_TANIMLARI = {
    "Marmara Bölgesi": [
        "İSTANBUL", "BALIKESİR", "BURSA", "SAKARYA", "EDİRNE", 
        "BİLECİK", "ÇANAKKALE", "TEKİRDAĞ", "KIRKLARELİ", "KOCAELİ", "YALOVA"
    ],
    "Orta Anadolu": [
        "ANKARA", "KONYA", "KAYSERİ", "ESKİŞEHİR", "SİVAS", "KIRIKKALE", "AKSARAY", "KARAMAN", "KIRŞEHİR", "NEVŞEHİR", "NİĞDE", "YOZGAT", "ÇANKIRI"
    ]
}

# --- 5. VERİ YÜKLEME ---
@st.cache_data
def load_data(file_path):
    if not os.path.exists(file_path): return None, None, None
    try:
        df = pd.read_excel(file_path)
        df.columns = [str(c).strip() for c in df.columns]
        
        # Sütun İsimlerini Yakalama (Esnek Yapı)
        if 'Dağıtıcı' in df.columns and 'Dağıtım Şirketi' not in df.columns:
            df.rename(columns={'Dağıtıcı': 'Dağıtım Şirketi'}, inplace=True)
        
        # Tarih Sütunlarını Tespit Et
        target_col = None
        for c in ['Dağıtıcı ile Yapılan Sözleşme Bitiş Tarihi', 'Bitiş Tarihi', 'Bitiş Tarih', 'Lisans Bitiş Tarihi']:
            if c in df.columns:
                target_col = c
                break
        
        start_col = None
        for c in ['Dağıtıcı ile Yapılan Sözleşme Başlangıç Tarihi', 'Başlangıç Tarihi', 'Başlangıç Tarih', 'Lisans Başlangıç Tarihi']:
            if c in df.columns:
                start_col = c
                break

        # Tarih Dönüşümü
        for col in [target_col, start_col]:
            if col: df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce')

        today = pd.to_datetime(datetime.date.today())
        if target_col:
            df['Kalan_Gun'] = (df[target_col] - today).dt.days
            df['Bitis_Yili'] = df[target_col].dt.year
            df['Bitis_Ayi_No'] = df[target_col].dt.month
            month_map = {1:'Ocak', 2:'Şubat', 3:'Mart', 4:'Nisan', 5:'Mayıs', 6:'Haziran', 
                         7:'Temmuz', 8:'Ağustos', 9:'Eylül', 10:'Ekim', 11:'Kasım', 12:'Aralık'}
            df['Bitis_Ayi'] = df['Bitis_Ayi_No'].map(month_map)
        
        # Risk Durumu
        def get_risk(days):
            if pd.isna(days): return "Bilinmiyor"
            if days < 0: return "SÜRESİ DOLDU 🚨"
            if days < 90: return "KRİTİK (<3 Ay) ⚠️"
            return "GÜVENLİ ✅"
        df['Risk_Durumu'] = df['Kalan_Gun'].apply(get_risk)

        # Şehir Yazımları
        for c in ['İl', 'İlçe']:
            if c in df.columns: df[c] = df[c].astype(str).str.upper().str.replace('i', 'İ').str.replace('ı', 'I')
            
        return df, target_col, start_col
    except Exception as e: return None, str(e), None

# --- ANA UYGULAMA ---
def main():
    data_result = load_data(SABIT_DOSYA_ADI)
    if data_result is None or data_result[0] is None:
        st.error(f"Hata: {SABIT_DOSYA_ADI} dosyası düzgün yüklenemedi. Lütfen dosya adını ve sütunları kontrol et.")
        st.stop()
    df, target_date_col, start_date_col = data_result

    with st.sidebar:
        st.title("🔍 Filtre Paneli")
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

    tabs = st.tabs(["📊 Bölgesel Durum", "🤖 Makine Analizi", "📅 Takvim", "📋 LİKİTGAZ SÖZLEŞME TAKİBİ", "📡 Radar", "📋 Ham Veri"])

    # 1. BÖLGESEL DURUM
    with tabs[0]:
        st.subheader("📊 Şehir Dağılımı")
        city_counts = filtered_df['İl'].value_counts().reset_index().head(20)
        city_counts.columns = ['İl', 'Adet']
        fig_city = px.bar(city_counts, x='İl', y='Adet', text='Adet', color='Adet', title="İstasyon Sayıları")
        fig_city.update_traces(textposition='outside')
        st.plotly_chart(fig_city, use_container_width=True)

    # 2. MAKİNE ANALİZİ
    with tabs[1]:
        st.subheader("🤖 Stratejik Analiz")
        my_df = filtered_df[filtered_df['Dağıtım Şirketi'] == MY_COMPANY]
        if not my_df.empty:
            st.markdown(f"<div class='insight-box-success'>✅ <b>Hakimiyet:</b> Bu bölgede <b>{len(my_df)}</b> adet bayiniz var.</div>", unsafe_allow_html=True)
        else: st.info("Seçili filtrelerde Likitgaz bayisi bulunamadı.")

    # 3. TAKVİM (SIRALAMA DÜZELTİLDİ)
    with tabs[2]:
        st.subheader("📅 Aylık Sözleşme Bitiş Takvimi")
        yrs = sorted(filtered_df['Bitis_Yili'].dropna().unique().astype(int).tolist())
        if yrs:
            sel_yr = st.selectbox("Yıl Seçin", yrs, index=yrs.index(datetime.date.today().year) if datetime.date.today().year in yrs else 0)
            df_yr = filtered_df[filtered_df['Bitis_Yili'] == sel_yr]
            m_cnt = df_yr.groupby(['Bitis_Ayi_No', 'Bitis_Ayi']).size().reset_index(name='Adet').sort_values('Bitis_Ayi_No')
            fig_cal = px.bar(m_cnt, x='Bitis_Ayi', y='Adet', text='Adet', title=f"{sel_yr} Aylık Dağılım")
            fig_cal.update_traces(textposition='outside')
            fig_cal.update_xaxes(categoryorder='array', categoryarray=m_cnt['Bitis_Ayi'].tolist())
            st.plotly_chart(fig_cal, use_container_width=True)

    # 4. LİKİTGAZ SÖZLEŞME TAKİBİ (HATA GİDERİLDİ)
    with tabs[3]:
        st.subheader(f"📋 {MY_COMPANY} Sözleşme & Not Takibi")
        
        # Filtreye Göre Sadece Likitgaz Verisi
        likit_display = df[df['Dağıtım Şirketi'] == MY_COMPANY].copy()
        
        # Yıl Filtresi
        likit_yrs = sorted(likit_display['Bitis_Yili'].dropna().unique().astype(int).tolist())
        sel_l_yr = st.selectbox("Sözleşme Bitiş Yılı", ["Tümü"] + likit_yrs)
        if sel_l_yr != "Tümü":
            likit_display = likit_display[likit_display['Bitis_Yili'] == sel_l_yr]

        # Sütunları Güvenli Seçelim (HATA ALAN KISIM BURASIYDI)
        potential_cols = ['Unvan', 'İletişim Adresi', start_date_col, target_date_col, 'Kalan_Gun']
        existing_cols = [c for c in potential_cols if c and c in likit_display.columns]
        
        likit_table = likit_display[existing_cols].copy()
        
        # Yeniden Adlandırma
        rename_dict = {}
        if 'İletişim Adresi' in likit_table.columns: rename_dict['İletişim Adresi'] = 'Adres'
        if start_date_col in likit_table.columns: rename_dict[start_date_col] = 'Başlangıç'
        if target_date_col in likit_table.columns: rename_dict[target_date_col] = 'Bitiş'
        likit_table.rename(columns=rename_dict, inplace=True)
        
        # Tarihleri Formatla
        for col in ['Başlangıç', 'Bitiş']:
            if col in likit_table.columns:
                likit_table[col] = pd.to_datetime(likit_table[col]).dt.strftime('%d.%m.%Y')

        # Notları Session State'den Birleştir
        likit_table = pd.merge(likit_table, st.session_state.notlar_df, on='Unvan', how='left').fillna("")

        # İNTERAKTİF TABLO
        edited = st.data_editor(
            likit_table,
            column_config={
                "Özel Not": st.column_config.TextColumn("Özel Not (Buraya yazın)", width="large"),
                "Kalan_Gun": st.column_config.NumberColumn("Kalan Gün", format="%d")
            },
            disabled=[c for c in likit_table.columns if c != "Özel Not"],
            hide_index=True, use_container_width=True
        )

        if st.button("📝 Notları Kaydet"):
            st.session_state.notlar_df = edited[['Unvan', 'Özel Not']]
            st.success("Notlar kaydedildi!")

    # 5. RADAR & HAM VERİ
    with tabs[4]:
        st.subheader("📡 Radar")
        st.dataframe(filtered_df[filtered_df['Kalan_Gun'] < 180], use_container_width=True)

if __name__ == "__main__":
    main()
