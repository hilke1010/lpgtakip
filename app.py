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
            month_map = {1:'Ocak', 2:'Şubat', 3:'Mart', 4:'Nisan', 5:'Mayıs', 6:'Haziran', 7:'Temmuz', 8:'Ağustos', 9:'Eylül', 10:'Ekim', 11:'Kasım', 12:'Aralık'}
            df['Bitis_Ayi'] = df['Bitis_Ayi_No'].map(month_map)
        
        if 'İl' in df.columns:
            df['İl'] = df['İl'].astype(str).str.upper().str.replace('i', 'İ').str.replace('ı', 'I')
            
        return df, bitis_col, baslangic_col, adres_col
    except Exception as e: return None, str(e), None, None

# --- ANA UYGULAMA ---
def main():
    df_raw, bitis_col, baslangic_col, adres_col = load_data(SABIT_DOSYA_ADI)
    if df_raw is None:
        st.error("Dosya bulunamadı!")
        st.stop()

    # --- SİDEBAR (MASTER FİLTRE) ---
    with st.sidebar:
        st.header("🔍 Filtre Paneli")
        
        # 1. BÖLGE SEÇİMİ
        sel_region = st.selectbox("🌍 Bölge Seç", ["Tümü"] + list(BOLGE_TANIMLARI.keys()))
        
        # BÖLGEYE GÖRE FİLTRELEME (BU ADIM ÇOK KRİTİK)
        if sel_region != "Tümü":
            master_filtered = df_raw[df_raw['İl'].isin(BOLGE_TANIMLARI[sel_region])].copy()
        else:
            master_filtered = df_raw.copy()

        # 2. ŞEHİR SEÇİMİ (Bölgeye göre daralır)
        sel_cities = st.multiselect("🏢 Şehir Seç", sorted(master_filtered['İl'].unique().tolist()))
        if sel_cities:
            master_filtered = master_filtered[master_filtered['İl'].isin(sel_cities)]

        # 3. ŞİRKET SEÇİMİ
        sel_comps = st.multiselect("⛽ Şirket Seç (Genel Analiz)", sorted(df_raw['Dağıtım Şirketi'].dropna().unique().tolist()))

    # --- KPI EKRANI ---
    st.title("🚀 LPG Pazar & Sözleşme Analizi")
    k1, k2, k3 = st.columns(3)
    
    # Şirket filtresi eklenmiş hali (Genel tablolar için)
    general_filtered = master_filtered.copy()
    if sel_comps:
        general_filtered = general_filtered[general_filtered['Dağıtım Şirketi'].isin(sel_comps)]

    k1.metric("Toplam İstasyon", f"{len(general_filtered):,}")
    
    # Likitgaz bayilerini SADECE sidebar'daki bölge/şehir filtresine göre sayıyoruz
    likit_in_scope = master_filtered[master_filtered['Dağıtım Şirketi'] == MY_COMPANY]
    k2.metric("Likitgaz Bayi", f"{len(likit_in_scope):,}")
    k3.metric("Kritik (<90 G)", len(general_filtered[general_filtered['Kalan_Gun'] < 90]))

    st.divider()

    tabs = st.tabs(["📊 Bölgesel", "🤖 Makine Analizi", "📅 Takvim", "📋 LİKİTGAZ SÖZLEŞME TAKİBİ", "📡 Radar"])

    # --- LİKİTGAZ SEKİMESİ (TAMAMEN MASTER FİLTREYE BAĞLANDI) ---
    with tabs[3]:
        st.subheader(f"📋 {MY_COMPANY} Sözleşme & Not Takibi")
        
        # SADECE Sidebar'da filtrelenmiş 'master_filtered' üzerinden veriyi çekiyoruz!
        # Orta Anadolu seçiliyse Altuğ Petrol (İzmir) master_filtered içinde yok, o yüzden burada da ASLA çıkamaz.
        likit_tablo_verisi = master_filtered[master_filtered['Dağıtım Şirketi'] == MY_COMPANY].copy()
        
        if likit_tablo_verisi.empty:
            st.warning("Seçili Bölge/Şehir kriterlerinde şirket bayisi bulunamadı.")
        else:
            # Yıl Filtresi
            l_yrs = sorted(likit_tablo_verisi['Bitis_Yili'].dropna().unique().astype(int).tolist())
            s_yr = st.selectbox("Bitiş Yılı Filtrele", ["Tümü"] + l_yrs, key="tab_filter")
            if s_yr != "Tümü": 
                likit_tablo_verisi = likit_tablo_verisi[likit_tablo_verisi['Bitis_Yili'] == s_yr]

            # Sütunları hazırla
            cols = ['Unvan']
            if adres_col: cols.append(adres_col)
            if baslangic_col: cols.append(baslangic_col)
            if bitis_col: cols.append(bitis_col)
            if 'Kalan_Gun' in likit_tablo_verisi.columns: cols.append('Kalan_Gun')

            likit_table = likit_tablo_verisi[cols].copy()
            renames = {adres_col: 'Adres', baslangic_col: 'Başlangıç', bitis_col: 'Bitiş'}
            likit_table.rename(columns={k:v for k,v in renames.items() if k in likit_table.columns}, inplace=True)
            
            for c in ['Başlangıç', 'Bitiş']:
                if c in likit_table.columns: likit_table[c] = pd.to_datetime(likit_table[c]).dt.strftime('%d.%m.%Y')

            # Notları eşle
            likit_table = pd.merge(likit_table, st.session_state.notlar_df, on='Unvan', how='left').fillna("")

            # EDİTÖR
            edited = st.data_editor(
                likit_table,
                column_config={"Özel Not Ekle": st.column_config.TextColumn("Özel Not", width="large")},
                disabled=[c for c in likit_table.columns if c != "Özel Not Ekle"],
                hide_index=True, use_container_width=True
            )
            if st.button("📝 Notları Kaydet"):
                st.session_state.notlar_df = edited[['Unvan', 'Özel Not Ekle']]
                st.success("Kaydedildi!")

    with tabs[0]: # Bölgesel durum sekmesi
        city_counts = general_filtered['İl'].value_counts().reset_index().head(20)
        city_counts.columns = ['İl', 'Adet']
        st.plotly_chart(px.bar(city_counts, x='İl', y='Adet', text='Adet', title="İl Dağılımı"), use_container_width=True)

if __name__ == "__main__":
    main()
