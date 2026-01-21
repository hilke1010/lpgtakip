import streamlit as st
import pandas as pd
import datetime
import os
s
# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="Sözleşme Takip Raporu", layout="wide")

# --- 2. SABİTLER ---
SABIT_DOSYA_ADI = "lpg.xlsx"

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
    ],
    "Ege Bölgesi": ["İZMİR", "MANİSA", "AYDIN", "DENİZLİ", "MUĞLA", "AFYONKARAHİSAR", "KÜTAHYA", "UŞAK"],
    "Akdeniz Bölgesi": ["ADANA", "ANTALYA", "BURDUR", "HATAY", "ISPARTA", "MERSİN", "KAHRAMANMARAŞ", "OSMANİYE"],
    "Karadeniz Bölgesi": ["AMASYA", "ARTVİN", "BOLU", "ÇORUM", "GİRESUN", "GÜMÜŞHANE", "KASTAMONU", "ORDU", "RİZE", "SAMSUN", "SİNOP", "TOKAT", "TRABZON", "ZONGULDAK", "BAYBURT", "BARTIN", "KARABÜK", "DÜZCE"],
    "Doğu Anadolu": ["AĞRI", "BİNGÖL", "BİTLİS", "ELAZIĞ", "ERZİNCAN", "ERZURUM", "HAKKARİ", "KARS", "MALATYA", "MUŞ", "TUNCELİ", "VAN", "ARDAHAN", "IĞDIR"],
    "Güneydoğu Anadolu": ["ADIYAMAN", "DİYARBAKIR", "GAZİANTEP", "KİLİS", "MARDİN", "SİİRT", "ŞANLIURFA", "BATMAN", "ŞIRNAK"]
}

# --- 4. VERİ YÜKLEME VE İŞLEME ---
@st.cache_data
def load_data(file_path):
    if not os.path.exists(file_path): return None
    try:
        df = pd.read_excel(file_path)
        # Sütun isimlerini temizle
        df.columns = [str(c).strip() for c in df.columns]
        
        # Esnek Sütun Bulucu
        def find_col(keywords):
            for k in keywords:
                for col in df.columns:
                    if k.lower() in col.lower(): return col
            return None

        # Sütunları Eşleştir
        col_unvan = find_col(['Unvan', 'Lisans Sahibi', 'Bayi Adı'])
        col_adres = find_col(['Adres', 'İletişim Adresi'])
        col_il = find_col(['İl', 'Şehir'])
        col_ilce = find_col(['İlçe', 'Bucak'])
        col_baslangic = find_col(['Başlangıç', 'Veriliş Tarihi'])
        col_bitis = find_col(['Bitiş', 'Sona Erme', 'Geçerlilik'])
        col_dagitici = find_col(['Dağıtıcı', 'Dağıtım'])

        # Tarih Formatlama
        today = pd.to_datetime(datetime.date.today())
        
        for c in [col_baslangic, col_bitis]:
            if c: df[c] = pd.to_datetime(df[c], dayfirst=True, errors='coerce')

        # Kalan Gün Hesapla
        if col_bitis:
            df['Kalan_Gun'] = (df[col_bitis] - today).dt.days
            df['Yil'] = df[col_bitis].dt.year
        
        # İli standartlaştır
        if col_il:
            df[col_il] = df[col_il].astype(str).str.upper().str.replace('i', 'İ').str.replace('ı', 'I')

        # Kullanılacak Sütunları Seç ve Yeniden Adlandır
        cols_to_keep = {}
        if col_unvan: cols_to_keep[col_unvan] = 'Unvan'
        if col_dagitici: cols_to_keep[col_dagitici] = 'Dağıtıcı'
        if col_adres: cols_to_keep[col_adres] = 'Adres'
        if col_il: cols_to_keep[col_il] = 'İl'
        if col_ilce: cols_to_keep[col_ilce] = 'İlçe'
        if col_baslangic: cols_to_keep[col_baslangic] = 'Başlangıç Tarihi'
        if col_bitis: cols_to_keep[col_bitis] = 'Bitiş Tarihi'
        
        # Ana tabloyu oluştur
        final_df = df[list(cols_to_keep.keys()) + (['Kalan_Gun', 'Yil'] if col_bitis else [])].copy()
        final_df.rename(columns=cols_to_keep, inplace=True)
        
        return final_df
    except Exception as e:
        st.error(f"Hata: {e}")
        return None

# --- 5. ANA EKRAN ---
def main():
    st.title("📋 Sözleşme Takip Raporu")
    
    df = load_data(SABIT_DOSYA_ADI)
    if df is None:
        st.error(f"'{SABIT_DOSYA_ADI}' dosyası bulunamadı. Lütfen klasöre ekleyin.")
        st.stop()

    # --- FİLTRE PANELİ (ÜST KISIM) ---
    st.markdown("### 🔍 Filtreler")
    c1, c2, c3, c4 = st.columns(4)

    # 1. YIL FİLTRESİ
    with c1:
        yillar = sorted(df['Yil'].dropna().astype(int).unique())
        secilen_yil = st.selectbox("📅 Bitiş Yılı Seçiniz", ["Tümü"] + yillar)

    # 2. BÖLGE FİLTRESİ
    with c2:
        bolgeler = ["Tümü"] + list(BOLGE_TANIMLARI.keys())
        secilen_bolge = st.selectbox("🌍 Bölge Seçiniz", bolgeler)

    # 3. İL FİLTRESİ (Bölgeye göre değişir)
    with c3:
        if secilen_bolge != "Tümü":
            filtre_iller = BOLGE_TANIMLARI[secilen_bolge]
            mevcut_iller = sorted(df[df['İl'].isin(filtre_iller)]['İl'].unique())
        else:
            mevcut_iller = sorted(df['İl'].unique())
            
        secilen_iller = st.multiselect("🏙️ İl Seçiniz (Çoklu)", mevcut_iller)

    # 4. DAĞITICI FİLTRESİ (Opsiyonel: Sadece kendi firmanı veya rakibi görmek istersen)
    with c4:
        if 'Dağıtıcı' in df.columns:
            dagiticilar = sorted(df['Dağıtıcı'].astype(str).unique())
            secilen_dagitici = st.multiselect("⛽ Dağıtıcı Şirket", dagiticilar)
        else:
            secilen_dagitici = []

    # --- FİLTRELEME MANTIĞI ---
    filtreli_df = df.copy()

    # Yıl Filtresi Uygula
    if secilen_yil != "Tümü":
        filtreli_df = filtreli_df[filtreli_df['Yil'] == secilen_yil]

    # Bölge Filtresi Uygula
    if secilen_bolge != "Tümü":
        filtreli_df = filtreli_df[filtreli_df['İl'].isin(BOLGE_TANIMLARI[secilen_bolge])]

    # İl Filtresi Uygula
    if secilen_iller:
        filtreli_df = filtreli_df[filtreli_df['İl'].isin(secilen_iller)]

    # Dağıtıcı Filtresi Uygula
    if secilen_dagitici:
        filtreli_df = filtreli_df[filtreli_df['Dağıtıcı'].isin(secilen_dagitici)]

    # --- TABLOYU GÖSTER ---
    st.divider()
    st.subheader(f"📄 Rapor Sonucu: {len(filtreli_df)} Kayıt Bulundu")
    
    if not filtreli_df.empty:
        # Görünecek Sütunları Düzenle (İstenen Sıra)
        gosterilecek_kolonlar = ['Unvan', 'Adres', 'İl', 'İlçe', 'Başlangıç Tarihi', 'Bitiş Tarihi', 'Kalan_Gun', 'Dağıtıcı']
        # Veri setinde var olanları seç (Hata almamak için)
        final_cols = [c for c in gosterilecek_kolonlar if c in filtreli_df.columns]
        
        gosterim_df = filtreli_df[final_cols].copy()

        # Tarih Formatı (Görsel Güzellik İçin)
        for col in ['Başlangıç Tarihi', 'Bitiş Tarihi']:
            if col in gosterim_df.columns:
                gosterim_df[col] = gosterim_df[col].dt.strftime('%d.%m.%Y')

        # Tabloyu Çiz
        st.dataframe(
            gosterim_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Kalan_Gun": st.column_config.NumberColumn(
                    "Kalan Gün",
                    format="%d Gün",
                    help="Sözleşme bitimine kalan gün sayısı"
                )
            }
        )
    else:
        st.warning("Seçilen kriterlere uygun veri bulunamadı.")

if __name__ == "__main__":
    main()

