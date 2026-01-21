import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import numpy as np
import os

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="EPDK LPG Analiz", layout="wide")

# --- 2. SABİTLER ---
SABIT_DOSYA_ADI = "lpg.xlsx"
MY_COMPANY = "LİKİTGAZ DAĞITIM VE ENDÜSTRİ ANONİM ŞİRKETİ"

# --- NOTLAR İÇİN SESSION STATE ---
if 'notlar_df' not in st.session_state:
    st.session_state.notlar_df = pd.DataFrame(columns=['Unvan', 'Özel Not Ekle'])

# --- 3. BÖLGE TANIMLARI ---
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
        # Sütun isimlerindeki boşlukları temizle
        df.columns = [str(c).strip() for c in df.columns]
        
        def find_col(keywords):
            for k in keywords:
                for col in df.columns:
                    # Büyük küçük harf duyarlılığını kaldırıp arar
                    if k.lower() in col.lower(): return col
            return None

        # Dağıtıcı Sütunu
        dagitici_col = find_col(['Dağıtım Şirketi', 'Dağıtıcı'])
        if dagitici_col: df.rename(columns={dagitici_col: 'Dağıtım Şirketi'}, inplace=True)
        
        # --- DÜZELTME YAPILAN YER ---
        # Resimdeki tam isimleri listenin EN BAŞINA ekledik.
        bitis_col = find_col([
            'Dağıtıcı ile Yapılan Sözleşme Bitiş Tarihi', # <-- ÖNCELİKLİ
            'Sözleşme Bitiş', 
            'Bitiş Tarihi',
            'Lisans Bitiş'
        ])
        
        baslangic_col = find_col([
            'Dağıtıcı ile Yapılan Sözleşme Başlangıç Tarihi', # <-- ÖNCELİKLİ
            'Sözleşme Başlangıç', 
            'Başlangıç Tarihi'
        ])
        # -----------------------------

        adres_col = find_col(['İletişim Adresi', 'Adres'])

        # Tarih formatlama
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
        st.error(f"Veri dosyası ({SABIT_DOSYA_ADI}) bulunamadı veya okunamadı!")
        if isinstance(bitis_col, str): # Hata mesajı döndüyse
            st.error(f"Hata Detayı: {bitis_col}")
        st.stop()

    # --- GENEL SİDEBAR FİLTRESİ ---
    with st.sidebar:
        st.header("🔍 Genel Filtre Paneli")
        st.info("Burada yapılan seçimler TÜM sekmeleri etkiler.")
        
        # 1. Bölge Seçimi
        sel_region = st.selectbox("🌍 Genel Bölge Seç", ["Tümü"] + list(BOLGE_TANIMLARI.keys()))
        
        # general_df: Sidebar seçimlerine göre filtrelenmiş ANA veri
        general_df = df_raw.copy()
        if sel_region != "Tümü":
            general_df = general_df[general_df['İl'].isin(BOLGE_TANIMLARI[sel_region])]

        # 2. Şehir Seçimi (Seçilen bölgeye göre daralır)
        available_cities = sorted(general_df['İl'].unique().tolist())
        sel_cities = st.multiselect("🏢 Genel Şehir Seç", available_cities)
        
        if sel_cities:
            general_df = general_df[general_df['İl'].isin(sel_cities)]

    st.title("🚀 LPG Pazar & Sözleşme Analizi")
    
    tabs = st.tabs(["📊 Bölgesel Analiz", "📅 Takvim", "📋 LİKİTGAZ SÖZLEŞME TAKİBİ", "📡 Radar"])

    # --- LİKİTGAZ SÖZLEŞME TAKİBİ ---
    with tabs[2]:
        st.subheader(f"📋 {MY_COMPANY} Sözleşme Takip")
        
        # Veriyi Sidebar ile filtrelenmiş 'general_df'den alıyoruz.
        likit_base = general_df[general_df['Dağıtım Şirketi'] == MY_COMPANY].copy()
        
        # Ekstra sadece YIL filtresi
        col_y1, col_y2 = st.columns([1, 3])
        with col_y1:
            if 'Bitis_Yili' in likit_base.columns:
                l_yrs = sorted(likit_base['Bitis_Yili'].dropna().unique().astype(int).tolist())
                if not l_yrs:
                    tab_yr = "Veri Yok"
                else:
                    tab_yr = st.selectbox("📅 Bitiş Yılı Filtrele", ["Tümü"] + l_yrs, key="tab_yr_sb")
                
                if tab_yr != "Tümü" and tab_yr != "Veri Yok":
                    likit_base = likit_base[likit_base['Bitis_Yili'] == tab_yr]
            else:
                st.warning("Bitiş Yılı verisi okunamadı.")

        st.markdown(f"**Seçili Filtrelere Göre Bayi Sayısı:** `{len(likit_base)}`")
        st.divider()

        # Tabloyu Göster
        if likit_base.empty:
            st.warning("Sol menüdeki filtrelere uygun Likitgaz bayisi bulunamadı.")
        else:
            # Sütunları seç
            display_cols = ['Unvan', 'İl'] 
            if adres_col: display_cols.append(adres_col)
            if baslangic_col: display_cols.append(baslangic_col)
            if bitis_col: display_cols.append(bitis_col)
            if 'Kalan_Gun' in likit_base.columns: display_cols.append('Kalan_Gun')

            final_table = likit_base[display_cols].copy()
            
            # Başlıkları Türkçeleştir/Düzenle
            renames = {adres_col: 'Adres', baslangic_col: 'Başlangıç', bitis_col: 'Bitiş'}
            final_table.rename(columns={k:v for k,v in renames.items() if k in final_table.columns}, inplace=True)
            
            # Tarihleri formatla (Sadece gösterim için string yapıyoruz)
            for c in ['Başlangıç', 'Bitiş']:
                if c in final_table.columns:
                    final_table[c] = pd.to_datetime(final_table[c]).dt.strftime('%d.%m.%Y')

            # Notları Session State ile eşleştir
            final_table = pd.merge(final_table, st.session_state.notlar_df, on='Unvan', how='left').fillna("")

            # İNTERAKTİF EDİTÖR
            edited = st.data_editor(
                final_table,
                column_config={
                    "Özel Not Ekle": st.column_config.TextColumn("Özel Not (Çift tıkla yaz)", width="large"),
                    "Kalan_Gun": st.column_config.NumberColumn("Kalan Gün", help="Sözleşme bitimine kalan gün")
                },
                disabled=[c for c in final_table.columns if c != "Özel Not Ekle"],
                hide_index=True, use_container_width=True, key="likit_data_editor"
            )
            
            if st.button("📝 Notları Kalıcı Olarak Kaydet"):
                # Notları state'e kaydet
                current_notes = edited[['Unvan', 'Özel Not Ekle']]
                merged_notes = pd.concat([st.session_state.notlar_df, current_notes]).drop_duplicates(subset='Unvan', keep='last')
                st.session_state.notlar_df = merged_notes
                st.success("Notlar bu oturum için kaydedildi!")

    # --- DİĞER SEKMELER ---
    with tabs[0]:
        st.subheader("📊 Genel Bölgesel Analiz")
        if general_df.empty:
            st.warning("Veri yok.")
        else:
            city_counts = general_df['İl'].value_counts().reset_index().head(20)
            city_counts.columns = ['İl', 'Adet']
            fig = px.bar(city_counts, x='İl', y='Adet', text='Adet', color='Adet', title="Filtrelenen Bölgedeki İstasyonlar")
            fig.update_traces(textposition='outside')
            st.plotly_chart(fig, use_container_width=True)

    with tabs[1]:
        st.subheader("📅 Sözleşme Bitiş Takvimi (Genel)")
        if 'Bitis_Yili' in general_df.columns:
            takvim_df = general_df.groupby('Bitis_Yili').size().reset_index(name='Bayi Sayısı')
            fig_cal = px.bar(takvim_df, x='Bitis_Yili', y='Bayi Sayısı', title="Yıllara Göre Bitecek Sözleşmeler")
            st.plotly_chart(fig_cal, use_container_width=True)
        else:
            st.warning("Tarih verisi bulunamadı.")
            
    with tabs[3]:
        st.info("Radar analizi henüz eklenmedi.")

if __name__ == "__main__":
    main()
