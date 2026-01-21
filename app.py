import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import numpy as np
import os
import io

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="EPDK LPG Analiz", layout="wide")

# --- 2. SABİTLER ---
SABIT_DOSYA_ADI = "lpg.xlsx"
MY_COMPANY = "LİKİTGAZ DAĞITIM VE ENDÜSTRİ ANONİM ŞİRKETİ"

# --- NOTLAR İÇİN SESSION STATE ---
if 'notlar_df' not in st.session_state:
    st.session_state.notlar_df = pd.DataFrame(columns=['Unvan', 'Özel Not Ekle'])

# --- 3. BÖLGE TANIMLARI (Senin 18 İllik Listen) ---
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

# --- 4. VERİ YÜKLEME ---
@st.cache_data
def load_data(file_path):
    if not os.path.exists(file_path): return None, None, None, None
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
        
        bitis_col = find_col(['Bitiş Tarihi', 'Lisans Bitiş', 'Sözleşme Bitiş'])
        baslangic_col = find_col(['Başlangıç Tarihi', 'Lisans Başlangıç', 'Sözleşme Başlangıç'])
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
    df_raw, bitis_col, baslangic_col, adres_col = load_data(SABIT_DOSYA_ADI)
    if df_raw is None:
        st.error("Veri dosyası (lpg.xlsx) bulunamadı!")
        st.stop()

    # --- GENEL SİDEBAR FİLTRESİ ---
    with st.sidebar:
        st.header("🔍 Genel Filtre Paneli")
        sel_region = st.selectbox("🌍 Genel Bölge Seç", ["Tümü"] + list(BOLGE_TANIMLARI.keys()))
        
        general_df = df_raw.copy()
        if sel_region != "Tümü":
            general_df = general_df[general_df['İl'].isin(BOLGE_TANIMLARI[sel_region])]

        sel_cities = st.multiselect("🏢 Genel Şehir Seç", sorted(general_df['İl'].unique().tolist()))
        if sel_cities:
            general_df = general_df[general_df['İl'].isin(sel_cities)]

    st.title("🚀 LPG Pazar & Sözleşme Analizi")
    
    tabs = st.tabs(["📊 Bölgesel Analiz", "📅 Takvim", "📋 LİKİTGAZ SÖZLEŞME TAKİBİ", "📡 Radar"])

    # --- LİKİTGAZ SÖZLEŞME TAKİBİ (ÖZEL FİLTRELİ SEKME) ---
    with tabs[2]:
        st.subheader(f"📋 {MY_COMPANY} Özel Takip Alanı")
        
        # --- SEKME İÇİ ÖZEL FİLTRELEME ---
        st.markdown("#### 🎯 Bu Tabloya Özel Filtre")
        col_f1, col_f2, col_f3 = st.columns(3)
        
        with col_f1:
            # Sekmeye özel Bölge Filtresi
            tab_region = st.selectbox("📍 Bölge (Sadece Bu Tablo)", ["Tümü"] + list(BOLGE_TANIMLARI.keys()), key="tab_reg_sb")
        
        # Likitgaz verisini hazırla
        likit_base = df_raw[df_raw['Dağıtım Şirketi'] == MY_COMPANY].copy()
        
        # Bölgeye göre daralt
        if tab_region != "Tümü":
            likit_base = likit_base[likit_base['İl'].isin(BOLGE_TANIMLARI[tab_region])]
        
        with col_f2:
            # Sekmeye özel Şehir Filtresi
            tab_cities = st.multiselect("🏙️ Şehir (Sadece Bu Tablo)", sorted(likit_base['İl'].unique().tolist()), key="tab_city_ms")
            if tab_cities:
                likit_base = likit_base[likit_base['İl'].isin(tab_cities)]
        
        with col_f3:
            # Yıl Filtresi
            l_yrs = sorted(likit_base['Bitis_Yili'].dropna().unique().astype(int).tolist())
            tab_yr = st.selectbox("📅 Bitiş Yılı", ["Tümü"] + l_yrs, key="tab_yr_sb")
            if tab_yr != "Tümü":
                likit_base = likit_base[likit_base['Bitis_Yili'] == tab_yr]

        st.divider()

        # Tabloyu Göster
        if likit_base.empty:
            st.warning("Seçtiğiniz özel filtre kriterlerinde Likitgaz bayisi bulunamadı.")
        else:
            # Sütunları seç
            display_cols = ['Unvan']
            if adres_col: display_cols.append(adres_col)
            if baslangic_col: display_cols.append(baslangic_col)
            if bitis_col: display_cols.append(bitis_col)
            if 'Kalan_Gun' in likit_base.columns: display_cols.append('Kalan_Gun')

            final_table = likit_base[display_cols].copy()
            
            # Başlıkları Türkçeleştir
            renames = {adres_col: 'Adres', baslangic_col: 'Başlangıç', bitis_col: 'Bitiş'}
            final_table.rename(columns={k:v for k,v in renames.items() if k in final_table.columns}, inplace=True)
            
            # Tarihleri formatla
            for c in ['Başlangıç', 'Bitiş']:
                if c in final_table.columns:
                    final_table[c] = pd.to_datetime(final_table[c]).dt.strftime('%d.%m.%Y')

            # Notları Session State ile eşleştir
            final_table = pd.merge(final_table, st.session_state.notlar_df, on='Unvan', how='left').fillna("")

            # İNTERAKTİF EDİTÖR
            edited = st.data_editor(
                final_table,
                column_config={"Özel Not Ekle": st.column_config.TextColumn("Özel Not (Çift tıkla yaz)", width="large")},
                disabled=[c for c in final_table.columns if c != "Özel Not Ekle"],
                hide_index=True, use_container_width=True, key="likit_data_editor"
            )
            
            if st.button("📝 Notları Kalıcı Olarak Kaydet"):
                st.session_state.notlar_df = edited[['Unvan', 'Özel Not Ekle']]
                st.success("Notlar bu oturum için kaydedildi!")

    # --- DİĞER SEKMELER (GENEL FİLTREYİ KULLANIR) ---
    with tabs[0]:
        st.subheader("📊 Genel Bölgesel Analiz")
        city_counts = general_df['İl'].value_counts().reset_index().head(20)
        city_counts.columns = ['İl', 'Adet']
        fig = px.bar(city_counts, x='İl', y='Adet', text='Adet', color='Adet', title="En Çok İstasyon Olan İller")
        fig.update_traces(textposition='outside')
        st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()
