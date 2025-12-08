import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import numpy as np
import os
from docx import Document
from docx.document import Document as _Document
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
from docx.table import _Cell, Table
from docx.text.paragraph import Paragraph
import re

# --- 1. SAYFA VE GENEL AYARLAR ---
st.set_page_config(
    page_title="EPDK LPG Pazar Analizi",
    page_icon="⛽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. DOSYA İSİMLERİ ---
SABIT_DOSYA_ADI = "lpg_veri.xlsx"
# Word dosyası artık kullanılmadığı için işlem yapılmayacak

# --- 3. CSS ÖZELLEŞTİRME ---
st.markdown("""
<style>
    .stMetric {
        background-color: #f0f2f6;
        border-left: 5px solid #ff4b4b;
        padding: 15px;
        border-radius: 5px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    .block-container { padding-top: 2rem; }
</style>
""", unsafe_allow_html=True)

# --- 4. EXCEL VERİ YÜKLEME ---
@st.cache_data
def load_data(file_path):
    if not os.path.exists(file_path): return None, None
    try:
        df = pd.read_excel(file_path)
        df.columns = [c.strip() for c in df.columns]
        
        date_cols = ['Lisans Başlangıç Tarihi', 'Lisans Bitiş Tarihi', 
                     'Dağıtıcı ile Yapılan Sözleşme Başlangıç Tarihi', 
                     'Dağıtıcı ile Yapılan Sözleşme Bitiş Tarihi']
        for col in date_cols:
            if col in df.columns: df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce')

        target_col = 'Dağıtıcı ile Yapılan Sözleşme Bitiş Tarihi'
        if target_col not in df.columns: target_col = 'Lisans Bitiş Tarihi'
        
        today = pd.to_datetime(datetime.date.today())
        if target_col in df.columns: df['Kalan_Gun'] = (df[target_col] - today).dt.days
        else: df['Kalan_Gun'] = np.nan

        def get_risk(days):
            if pd.isna(days): return "Bilinmiyor"
            if days < 0: return "SÜRESİ DOLDU 🚨"
            if days < 90: return "KRİTİK (<3 Ay) ⚠️"
            if days < 180: return "YAKLAŞIYOR (<6 Ay) ⏳"
            return "GÜVENLİ ✅"

        df['Risk_Durumu'] = df['Kalan_Gun'].apply(get_risk)
        
        if 'İl' in df.columns: df['İl'] = df['İl'].astype(str).str.upper().str.replace('i', 'İ').str.replace('ı', 'I')
        if 'İlçe' in df.columns: df['İlçe'] = df['İlçe'].astype(str).str.upper().str.replace('i', 'İ').str.replace('ı', 'I')
        return df, target_col
    except Exception as e:
        st.error(f"Excel okuma hatası: {e}"); return None, None

def main():
    # --- VERİ ÇEKME ---
    df, target_date_col = load_data(SABIT_DOSYA_ADI)
    
    if df is None:
        st.error(f"❌ HATA: '{SABIT_DOSYA_ADI}' bulunamadı.")
        st.stop()

    # --- SIDEBAR ---
    with st.sidebar:
        # 1. Bilgi Notu (En Üstte)
        st.info("🕒 Not: Veriler her gün saat 10:00'da yenilenmektedir.")
        st.markdown("---")

        st.title("🔍 Filtre Paneli")
        all_cities = sorted(df['İl'].unique().tolist())
        selected_cities = st.multiselect("🏢 Şehir Seç", all_cities)
        
        if selected_cities:
            filtered_districts = sorted(df[df['İl'].isin(selected_cities)]['İlçe'].unique().tolist())
        else:
            filtered_districts = sorted(df['İlçe'].unique().tolist())
        selected_districts = st.multiselect("📍 İlçe Seç", filtered_districts)

        all_companies = sorted(df['Dağıtım Şirketi'].dropna().unique().tolist())
        selected_companies = st.multiselect("⛽ Şirket Seç", all_companies)
        
        all_risks = sorted(df['Risk_Durumu'].unique().tolist())
        selected_risks = st.multiselect("⚠️ Risk Durumu", all_risks)
        
        st.caption(f"Kayıt Sayısı: {len(df)}")
        
        # 2. Linkler ve İletişim (En Altta)
        st.markdown("---")
        st.header("🔗 Rapor Bağlantıları")
        st.markdown("⛽ [Akaryakıt Lisans Raporu](https://akartakip.streamlit.app/)")
        st.markdown("📊 [EPDK Sektör Raporu](https://pazarpayi.streamlit.app/)")
        
        st.markdown("---")
        st.header("📧 İletişim")
        st.info("kerim.aksu@milangaz.com.tr")

    # --- FİLTRELEME ---
    df_filtered = df.copy()
    if selected_cities: df_filtered = df_filtered[df_filtered['İl'].isin(selected_cities)]
    if selected_districts: df_filtered = df_filtered[df_filtered['İlçe'].isin(selected_districts)]
    if selected_companies: df_filtered = df_filtered[df_filtered['Dağıtım Şirketi'].isin(selected_companies)]
    if selected_risks: df_filtered = df_filtered[df_filtered['Risk_Durumu'].isin(selected_risks)]

    # --- BAŞLIK VE KPI ---
    st.title("🚀 Otogaz (LPG) Pazar & Risk Analizi")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam İstasyon", f"{len(df_filtered):,}")
    c2.metric("Acil Sözleşme", len(df_filtered[df_filtered['Kalan_Gun'] < 90]), delta="Acil", delta_color="inverse")
    c3.metric("Aktif Dağıtıcı", df_filtered['Dağıtım Şirketi'].nunique())
    c4.metric("Ort. Kalan Gün", f"{df_filtered['Kalan_Gun'].mean():.0f}")
    st.divider()

    # --- SEKMELER (EPDK ve Ham Veri Kaldırıldı) ---
    tab_risk, tab_detay, tab_market, tab_trend = st.tabs([
        "⚡ Sözleşme & Risk", "🔢 Detaylı Bayi", "🏢 Pazar & Rekabet", "📈 Zaman Analizi"
    ])

    # 1. RİSK TABLOSU
    with tab_risk:
        st.subheader("🚨 Kritik Sözleşmeler (İlk 6 Ay)")
        critical_df = df_filtered[df_filtered['Kalan_Gun'] < 180].sort_values('Kalan_Gun')
        critical_df.index = np.arange(1, len(critical_df) + 1)
        
        if not critical_df.empty:
            critical_df['Bitis'] = critical_df[target_date_col].dt.strftime('%Y-%m-%d')
            st.dataframe(critical_df[['Unvan', 'İl', 'Dağıtım Şirketi', 'Bitis', 'Kalan_Gun', 'Risk_Durumu']], use_container_width=True)
        else: st.success("Riskli sözleşme yok.")
        
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            df_filtered['Yil'] = df_filtered[target_date_col].dt.year
            y_cnt = df_filtered['Yil'].value_counts().sort_index().reset_index()
            y_cnt.columns=['Yıl','Adet']
            curr_year = datetime.date.today().year
            y_cnt = y_cnt[(y_cnt['Yıl'] >= curr_year) & (y_cnt['Yıl'] <= curr_year+10)]
            st.plotly_chart(px.bar(y_cnt, x='Yıl', y='Adet', text='Adet', color='Adet', color_continuous_scale='Oranges'), use_container_width=True)
        
        with col_r2:
            risk_counts = df_filtered['Risk_Durumu'].value_counts().reset_index()
            risk_counts.columns = ['Durum', 'Adet']
            st.plotly_chart(
                px.pie(risk_counts, values='Adet', names='Durum', hole=0.4, title="Risk Dağılımı",
                       color_discrete_map={"SÜRESİ DOLDU 🚨":"red", "KRİTİK (<3 Ay) ⚠️":"orange", "YAKLAŞIYOR (<6 Ay) ⏳": "#FFD700", "GÜVENLİ ✅":"green"}), 
                use_container_width=True
            )

    # 2. DETAY (Grafikler Kaldırıldı, Sadece Tablo)
    with tab_detay:
        st.subheader("📊 Bayi Dağılım Listesi")
        if not selected_companies:
            # Şirket Seçili Değilse: Dağıtıcı Bazlı Liste
            comp_stats = df_filtered['Dağıtım Şirketi'].value_counts().reset_index()
            comp_stats.columns = ['Şirket', 'Toplam Bayi']
            comp_stats.index = np.arange(1, len(comp_stats) + 1)
            st.dataframe(comp_stats, use_container_width=True, height=600)
        else:
            # Şirket Seçiliyse: İl Bazlı Liste
            city_stats = df_filtered['İl'].value_counts().reset_index()
            city_stats.columns = ['Şehir', 'Bayi Sayısı']
            city_stats.index = np.arange(1, len(city_stats) + 1)
            st.dataframe(city_stats, use_container_width=True, height=600)

    # 3. PAZAR
    with tab_market:
        c_m1, c_m2 = st.columns(2)
        with c_m1: st.plotly_chart(px.treemap(df_filtered, path=['Dağıtım Şirketi', 'İl'], color='Dağıtım Şirketi'), use_container_width=True)
        with c_m2:
            cc = df_filtered['Dağıtım Şirketi'].value_counts().reset_index()
            cc.columns=['Şirket','Adet']
            tot = cc['Adet'].sum()
            if len(cc)>10: cc = pd.concat([cc.iloc[:10], pd.DataFrame({'Şirket':['DİĞER'],'Adet':[cc.iloc[10:]['Adet'].sum()]})])
            fig = px.pie(cc, values='Adet', names='Şirket', hole=0.5)
            fig.add_annotation(text=f"{tot}", x=0.5, y=0.5, font_size=20, showarrow=False)
            st.plotly_chart(fig, use_container_width=True)

    # 4. ZAMAN ANALİZİ
    with tab_trend:
        st.subheader("📈 Yıllık Yeni Bayi Girişi ve Trendler")
        
        st.markdown("""
        <div style="background-color: #e8f4f8; padding: 15px; border-radius: 5px; margin-bottom: 20px; border-left: 5px solid #3498db;">
            <strong>ℹ️ Analiz Bilgisi:</strong><br>
            Bu grafik, <strong>yıllara göre sisteme yeni katılan (lisans alan) bayi sayılarını</strong> göstermektedir. 
        </div>
        """, unsafe_allow_html=True)

        if 'Dağıtıcı ile Yapılan Sözleşme Başlangıç Tarihi' in df_filtered.columns:
            dy = df_filtered.copy()
            dy['Yil'] = dy['Dağıtıcı ile Yapılan Sözleşme Başlangıç Tarihi'].dt.year
            yg = dy['Yil'].value_counts().sort_index().reset_index()
            yg.columns=['Yıl','Yeni Bayi']
            st.plotly_chart(px.line(yg[yg['Yıl']>=2000], x='Yıl', y='Yeni Bayi', markers=True), use_container_width=True)

if __name__ == "__main__":
    main()
