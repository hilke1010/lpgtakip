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

# --- 4. BÖLGE TANIMLARI (Senin 18 İllik Orta Anadolu Listen) ---
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

# --- 5. VERİ YÜKLEME VE SÜTUN YAKALAMA ---
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
        
        bitis_col = find_col(['Bitiş Tarihi', 'Bitiş Tarih', 'Lisans Bitiş', 'Sözleşme Bitiş'])
        baslangic_col = find_col(['Başlangıç Tarihi', 'Başlangıç Tarih', 'Lisans Başlangıç', 'Sözleşme Başlangıç'])
        adres_col = find_col(['İletişim Adresi', 'Adres'])

        for col in [bitis_col, baslangic_col]:
            if col and col in df.columns:
                df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce')

        today = pd.to_datetime(datetime.date.today())
        if bitis_col and bitis_col in df.columns:
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
        st.error("Dosya yüklenemedi. Lütfen 'lpg.xlsx' dosyasını kontrol et.")
        st.stop()
    df, bitis_tarih_col, baslangic_tarih_col, adres_col = data_result

    # --- SIDEBAR (FİLTRE PANELİ) ---
    with st.sidebar:
        st.title("🔍 Filtre Paneli")
        
        # 1. BÖLGE FİLTRESİ
        selected_region = st.selectbox("🌍 Bölge Seç", ["Tümü"] + list(BOLGE_TANIMLARI.keys()))
        
        filtered_df = df.copy()
        if selected_region != "Tümü":
            filtered_df = filtered_df[filtered_df['İl'].isin(BOLGE_TANIMLARI[selected_region])]

        # 2. ŞEHİR FİLTRESİ (Bölgeye göre güncellenir)
        all_cities_in_scope = sorted(filtered_df['İl'].unique().tolist())
        selected_cities = st.multiselect("🏢 Şehir Seç", all_cities_in_scope)
        if selected_cities:
            filtered_df = filtered_df[filtered_df['İl'].isin(selected_cities)]

        # 3. ŞİRKET FİLTRESİ
        all_comps = sorted(df['Dağıtım Şirketi'].dropna().unique().tolist())
        selected_companies = st.multiselect("⛽ Şirket Seç", all_comps)
        
        # KPI'lar ve genel sekmeler için şirket filtresini uygula
        general_filtered_df = filtered_df.copy()
        if selected_companies:
            general_filtered_df = general_filtered_df[general_filtered_df['Dağıtım Şirketi'].isin(selected_companies)]

    # --- KPI EKRANI ---
    st.title("🚀 LPG Pazar & Sözleşme Analizi")
    c1, c2, c3 = st.columns(3)
    
    # KPI 1: Seçili Bölge/Şehir/Şirket'e göre toplam istasyon
    c1.metric("Toplam İstasyon", f"{len(general_filtered_df):,}")
    
    # KPI 2: Seçili Bölge/Şehir'e göre sadece LİKİTGAZ sayısı
    likit_in_scope = filtered_df[filtered_df['Dağıtım Şirketi'] == MY_COMPANY]
    c2.metric("Likitgaz Bayi", f"{len(likit_in_scope):,}")
    
    # KPI 3: Kritik sözleşmeler
    c3.metric("Kritik Sözleşme (<90 G)", len(general_filtered_df[general_filtered_df['Kalan_Gun'] < 90]))

    st.divider()

    # --- SEKMELER ---
    tabs = st.tabs(["📊 Bölgesel Durum", "🤖 Makine Analizi", "📅 Takvim", "📋 LİKİTGAZ SÖZLEŞME TAKİBİ", "📡 Radar"])

    # --- 4. SEKME: LİKİTGAZ SÖZLEŞME TAKİBİ (FİLTREYE BAĞLANDI!) ---
    with tabs[3]:
        st.subheader(f"📋 {MY_COMPANY} Sözleşme & Not Takibi")
        
        # BURASI KRİTİK: Tablo verisini sidebar'da filtrelenmiş 'filtered_df' üzerinden alıyoruz!
        # Eğer Orta Anadolu seçiliyse, Altuğ Petrol (başka ildeyse) artık burada ÇIKMAYACAK.
        likit_display = filtered_df[filtered_df['Dağıtım Şirketi'] == MY_COMPANY].copy()
        
        if likit_display.empty:
            st.warning("Seçili Bölge/Şehir kriterlerinde şirket bayisi bulunamadı.")
        else:
            # Tablo içi Yıl Filtresi
            likit_yrs = sorted(likit_display['Bitis_Yili'].dropna().unique().astype(int).tolist())
            sel_l_yr = st.selectbox("Bitiş Yılı Filtrele", ["Tümü"] + likit_yrs, key="tab_yr_filter")
            if sel_l_yr != "Tümü":
                likit_display = likit_display[likit_display['Bitis_Yili'] == sel_l_yr]

            # Görüntülenecek sütunları hazırla
            show_cols = ['Unvan']
            if adres_col: show_cols.append(adres_col)
            if baslangic_tarih_col: show_cols.append(baslangic_tarih_col)
            if bitis_tarih_col: show_cols.append(bitis_tarih_col)
            if 'Kalan_Gun' in likit_display.columns: show_cols.append('Kalan_Gun')

            final_table = likit_display[show_cols].copy()
            
            # Başlıkları güzelleştir
            renames = {adres_col: 'Adres', baslangic_tarih_col: 'Başlangıç', bitis_tarih_col: 'Bitiş'}
            final_table.rename(columns={k:v for k,v in renames.items() if k in final_table.columns}, inplace=True)

            # Tarih formatlama
            for col in ['Başlangıç', 'Bitiş']:
                if col in final_table.columns:
                    final_table[col] = pd.to_datetime(final_table[col]).dt.strftime('%d.%m.%Y')

            # Notları Session State'den eşle
            final_table = pd.merge(final_table, st.session_state.notlar_df, on='Unvan', how='left').fillna("")

            # İNTERAKTİF TABLO
            edited = st.data_editor(
                final_table,
                column_config={
                    "Özel Not Ekle": st.column_config.TextColumn("Özel Not Ekle (Düzenlemek için çift tıkla)", width="large"),
                    "Kalan_Gun": st.column_config.NumberColumn("Kalan Gün", format="%d")
                },
                disabled=[c for c in final_table.columns if c != "Özel Not Ekle"],
                hide_index=True, use_container_width=True, key="likit_editor"
            )

            if st.button("📝 Notları Kalıcı Kaydet"):
                st.session_state.notlar_df = edited[['Unvan', 'Özel Not Ekle']]
                st.success("Notlar kaydedildi!")

    # --- DİĞER SEKMELER (Genel filtreleri kullanır) ---
    with tabs[0]:
        city_counts = general_filtered_df['İl'].value_counts().reset_index().head(20)
        city_counts.columns = ['İl', 'Adet']
        fig = px.bar(city_counts, x='İl', y='Adet', text='Adet', color='Adet', title="İl Bazlı Dağılım")
        fig.update_traces(textposition='outside')
        st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()
