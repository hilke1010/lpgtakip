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

# --- 2. SABİTLER ---
SABIT_DOSYA_ADI = "lpg.xlsx"
MY_COMPANY = "LİKİTGAZ DAĞITIM VE ENDÜSTRİ ANONİM ŞİRKETİ"

# --- NOTLAR İÇİN SESSION STATE ---
if 'notlar_df' not in st.session_state:
    st.session_state.notlar_df = pd.DataFrame(columns=['Unvan', 'Özel Not'])

# --- 3. CSS ---
st.markdown("""
<style>
    .stMetric { background-color: #f0f2f6; border-left: 5px solid #e67e22; padding: 15px; border-radius: 5px; }
    .insight-box-success { padding: 15px; border-radius: 8px; background-color: #d4edda; border-left: 5px solid #28a745; margin-bottom: 10px; color: #155724; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 4. BÖLGE TANIMLARI (18 İL ORTA ANADOLU) ---
BOLGE_TANIMLARI = {
    "Marmara Bölgesi": [
        "İSTANBUL", "BALIKESİR", "BURSA", "SAKARYA", "EDİRNE", 
        "BİLECİK", "ÇANAKKALE", "TEKİRDAĞ", "KIRKLARELİ", "KOCAELİ", "YALOVA"
    ],
    "Orta Anadolu": [
        "ANKARA", "KONYA", "KAYSERİ", "ESKİŞEHİR", "YOZGAT", "KASTAMONU", 
        "ZONGULDAK", "KARABÜK", "KIRIKKALE", "AFYONKARAHİSAR", "KIRŞEHİR", 
        "NİĞDE", "NEVŞEHİR", "ÇANKIRI", "AKSARAY", "DÜZCE", "BOLU", "BARTIN"
    ]
}

# --- 5. VERİ YÜKLEME VE SÜTUN BULMA ---
@st.cache_data
def load_data(file_path):
    if not os.path.exists(file_path): return None, None, None
    try:
        df = pd.read_excel(file_path)
        df.columns = [str(c).strip() for c in df.columns]
        
        def find_col(keywords):
            for k in keywords:
                for col in df.columns:
                    if k.lower() in col.lower(): return col
            return None

        dagitici_col = find_col(['Dağıtım Şirketi', 'Dağıtıcı'])
        if dagitici_col: df.rename(columns={dagitici_col: 'Dağıtım Şirketi'}, inplace=True)
        
        bitis_col = find_col(['Sözleşme Bitiş', 'Bitiş Tarihi', 'Bitiş Tarih', 'Lisans Bitiş'])
        baslangic_col = find_col(['Sözleşme Başlangıç', 'Başlangıç Tarihi', 'Başlangıç Tarih', 'Lisans Başlangıç'])
        adres_col = find_col(['İletişim Adresi', 'Adres'])

        for col in [bitis_col, baslangic_col]:
            if col: df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce')

        today = pd.to_datetime(datetime.date.today())
        if bitis_col:
            df['Kalan_Gun'] = (df[bitis_col] - today).dt.days
            df['Bitis_Yili'] = df[bitis_col].dt.year
            df['Bitis_Ayi_No'] = df[bitis_col].dt.month
            month_map = {1:'Ocak', 2:'Şubat', 3:'Mart', 4:'Nisan', 5:'Mayıs', 6:'Haziran', 
                         7:'Temmuz', 8:'Ağustos', 9:'Eylül', 10:'Ekim', 11:'Kasım', 12:'Aralık'}
            df['Bitis_Ayi'] = df['Bitis_Ayi_No'].map(month_map)
        
        if 'İl' in df.columns:
            df['İl'] = df['İl'].astype(str).str.upper().str.replace('i', 'İ').str.replace('ı', 'I')
            
        return df, bitis_col, baslangic_col, adres_col
    except Exception as e: return None, str(e), None, None

# --- ANA UYGULAMA ---
def main():
    data_result = load_data(SABIT_DOSYA_ADI)
    if data_result is None or data_result[0] is None:
        st.error("Lütfen lpg.xlsx dosyasını kontrol edin.")
        st.stop()
    df, bitis_tarih_col, baslangic_tarih_col, adres_col = data_result

    # --- SIDEBAR (FİLTRELER) ---
    with st.sidebar:
        st.title("🔍 Filtre Paneli")
        selected_region = st.selectbox("🌍 Bölge Seç", ["Tümü"] + list(BOLGE_TANIMLARI.keys()))
        
        # Filtreleme Başlıyor
        filtered_df = df.copy()
        if selected_region != "Tümü":
            filtered_df = filtered_df[filtered_df['İl'].isin(BOLGE_TANIMLARI[selected_region])]

        selected_cities = st.multiselect("🏢 Şehir Seç", sorted(filtered_df['İl'].unique().tolist()))
        if selected_cities: filtered_df = filtered_df[filtered_df['İl'].isin(selected_cities)]

        # Buradaki şirket seçimi diğer sekmeleri etkiler ama Likitgaz sekmesi zaten şirkete özeldir
        selected_companies = st.multiselect("⛽ Şirket Seç (Genel Analiz İçin)", sorted(df['Dağıtım Şirketi'].dropna().unique().tolist()))
        
        # Genel sekmeler için şirket filtresi
        general_filtered_df = filtered_df.copy()
        if selected_companies: general_filtered_df = general_filtered_df[general_filtered_df['Dağıtım Şirketi'].isin(selected_companies)]

    # --- KPI ---
    st.title("🚀 LPG Pazar & Sözleşme Analizi")
    c1, c2, c3 = st.columns(3)
    c1.metric("Toplam İstasyon", f"{len(general_filtered_df):,}")
    
    # Likitgaz bayilerini sadece seçili bölge/ile göre filtrele
    likit_on_region = filtered_df[filtered_df['Dağıtım Şirketi'] == MY_COMPANY]
    c2.metric("Likitgaz Bayi", f"{len(likit_on_region):,}")
    c3.metric("Kritik Sözleşme (<90 G)", len(general_filtered_df[general_filtered_df['Kalan_Gun'] < 90]))

    st.divider()

    tabs = st.tabs(["📊 Bölgesel Durum", "🤖 Makine Analizi", "📅 Takvim", "📋 LİKİTGAZ SÖZLEŞME TAKİBİ", "📡 Radar"])

    # --- 4. SEKME: LİKİTGAZ SÖZLEŞME TAKİBİ (FİLTRE ÇALIŞIYOR) ---
    with tabs[3]:
        st.subheader(f"📋 {MY_COMPANY} Sözleşme & Not Takibi")
        
        # KRİTİK NOKTA: Sidebar'da seçilen Bölge ve İllere göre filtreleme yapar
        # Altuğ Petrol (Uşak) ise ve sen Orta Anadolu seçtiysen burada çıkmayacak!
        likit_display = filtered_df[filtered_df['Dağıtım Şirketi'] == MY_COMPANY].copy()
        
        if likit_display.empty:
            st.warning("Seçili Bölge/İl kriterlerinde Likitgaz bayisi bulunamadı.")
        else:
            likit_yrs = sorted(likit_display['Bitis_Yili'].dropna().unique().astype(int).tolist())
            sel_l_yr = st.selectbox("Sözleşme Bitiş Yılı Filtrele", ["Tümü"] + likit_yrs)
            if sel_l_yr != "Tümü": likit_display = likit_display[likit_display['Bitis_Yili'] == sel_l_yr]

            # Tablo Sütunları
            final_table_cols = ['Unvan']
            if adres_col: final_table_cols.append(adres_col)
            if baslangic_tarih_col: final_table_cols.append(baslangic_tarih_col)
            if bitis_tarih_col: final_table_cols.append(bitis_tarih_col)
            if 'Kalan_Gun' in likit_display.columns: final_table_cols.append('Kalan_Gun')

            likit_table = likit_display[final_table_cols].copy()
            renames = {adres_col: 'Adres', baslangic_tarih_col: 'Başlangıç', bitis_tarih_col: 'Bitiş'}
            likit_table.rename(columns={k:v for k,v in renames.items() if k in likit_table.columns}, inplace=True)

            # Tarihleri düzelt
            for col in ['Başlangıç', 'Bitiş']:
                if col in likit_table.columns: likit_table[col] = pd.to_datetime(likit_table[col]).dt.strftime('%d.%m.%Y')

            # Notları Birleştir
            likit_table = pd.merge(likit_table, st.session_state.notlar_df, on='Unvan', how='left').fillna("")

            # İnteraktif Editör
            edited = st.data_editor(
                likit_table,
                column_config={
                    "Özel Not": st.column_config.TextColumn("Özel Not Ekle", width="large"),
                    "Kalan_Gun": st.column_config.NumberColumn("Kalan Gün", format="%d")
                },
                disabled=[c for c in likit_table.columns if c != "Özel Not"],
                hide_index=True, use_container_width=True
            )

            if st.button("📝 Tüm Notları Kaydet"):
                st.session_state.notlar_df = edited[['Unvan', 'Özel Not']]
                st.success("Notlar başarıyla güncellendi!")

    # Diğer sekmeler (Bölgesel Durum, Makine, Takvim, Radar) general_filtered_df kullanır
    with tabs[0]:
        st.subheader("📊 İl Bazlı İstasyon Sayıları")
        city_counts = general_filtered_df['İl'].value_counts().reset_index().head(20)
        city_counts.columns = ['İl', 'Adet']
        fig_city = px.bar(city_counts, x='İl', y='Adet', text='Adet', color='Adet')
        fig_city.update_traces(textposition='outside')
        st.plotly_chart(fig_city, use_container_width=True)

if __name__ == "__main__":
    main()
