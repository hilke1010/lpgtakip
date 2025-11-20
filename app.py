import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import numpy as np
import os

# --- 1. SAYFA VE GENEL AYARLAR ---
st.set_page_config(
    page_title="EPDK LPG Pazar Analizi",
    page_icon="⛽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. SABİT VE KONFİGÜRASYON ---
SABIT_DOSYA_ADI = "lpg_veri.xlsx"

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
    h1 { color: #0e1117; }
    h3 { color: #262730; }
</style>
""", unsafe_allow_html=True)

# --- 4. VERİ YÜKLEME VE İŞLEME ---
@st.cache_data
def load_data(file_path):
    if not os.path.exists(file_path):
        return None
    
    try:
        df = pd.read_excel(file_path)
        df.columns = [c.strip() for c in df.columns]
        
        date_cols = [
            'Lisans Başlangıç Tarihi', 'Lisans Bitiş Tarihi',
            'Dağıtıcı ile Yapılan Sözleşme Başlangıç Tarihi',
            'Dağıtıcı ile Yapılan Sözleşme Bitiş Tarihi'
        ]
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce')

        target_col = 'Dağıtıcı ile Yapılan Sözleşme Bitiş Tarihi'
        if target_col not in df.columns:
            target_col = 'Lisans Bitiş Tarihi'
        
        today = pd.to_datetime(datetime.date.today())
        if target_col in df.columns:
            df['Kalan_Gun'] = (df[target_col] - today).dt.days
        else:
            df['Kalan_Gun'] = np.nan

        def get_risk(days):
            if pd.isna(days): return "Bilinmiyor"
            if days < 0: return "SÜRESİ DOLDU 🚨"
            if days < 90: return "KRİTİK (<3 Ay) ⚠️"
            if days < 180: return "YAKLAŞIYOR (<6 Ay) ⏳"
            return "GÜVENLİ ✅"

        df['Risk_Durumu'] = df['Kalan_Gun'].apply(get_risk)
        
        if 'İl' in df.columns:
            df['İl'] = df['İl'].astype(str).str.upper().str.replace('i', 'İ').str.replace('ı', 'I')
        if 'İlçe' in df.columns:
            df['İlçe'] = df['İlçe'].astype(str).str.upper().str.replace('i', 'İ').str.replace('ı', 'I')

        return df, target_col

    except Exception as e:
        st.error(f"Veri okuma hatası: {e}")
        return None, None

def main():
    # --- VERİYİ OKU ---
    df, target_date_col = load_data(SABIT_DOSYA_ADI)
    
    if df is None:
        st.error(f"❌ HATA: '{SABIT_DOSYA_ADI}' dosyası bulunamadı.")
        st.stop()

    # --- SIDEBAR FİLTRELERİ ---
    with st.sidebar:
        st.title("🔍 Filtre Paneli")
        
        # 1. İl Filtresi
        all_cities = sorted(df['İl'].unique().tolist())
        selected_cities = st.multiselect("🏢 Şehir Seç", all_cities)
        
        # 2. İlçe Filtresi
        if selected_cities:
            filtered_districts = sorted(df[df['İl'].isin(selected_cities)]['İlçe'].unique().tolist())
        else:
            filtered_districts = sorted(df['İlçe'].unique().tolist())
        selected_districts = st.multiselect("📍 İlçe Seç", filtered_districts)

        # 3. Şirket Filtresi
        all_companies = sorted(df['Dağıtım Şirketi'].dropna().unique().tolist())
        selected_companies = st.multiselect("⛽ Şirket Seç", all_companies)

        # 4. Risk Filtresi
        all_risks = sorted(df['Risk_Durumu'].unique().tolist())
        selected_risks = st.multiselect("⚠️ Risk Durumu", all_risks)

        st.info(f"Toplam Kayıt: {len(df)}")

    # --- FİLTRE UYGULAMA ---
    df_filtered = df.copy()
    if selected_cities:
        df_filtered = df_filtered[df_filtered['İl'].isin(selected_cities)]
    if selected_districts:
        df_filtered = df_filtered[df_filtered['İlçe'].isin(selected_districts)]
    if selected_companies:
        df_filtered = df_filtered[df_filtered['Dağıtım Şirketi'].isin(selected_companies)]
    if selected_risks:
        df_filtered = df_filtered[df_filtered['Risk_Durumu'].isin(selected_risks)]

    # --- ANA EKRAN ---
    st.title("🚀 Otogaz (LPG) Pazar & Risk Analizi")
    
    # KPI KARTLARI
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Toplam İstasyon", f"{len(df_filtered):,}")
    with col2:
        riskli_sayi = len(df_filtered[df_filtered['Kalan_Gun'] < 90])
        st.metric("Acil Sözleşme (<90 Gün)", riskli_sayi, delta="Acil Aksiyon", delta_color="inverse")
    with col3:
        active_companies = df_filtered['Dağıtım Şirketi'].nunique()
        st.metric("Aktif Dağıtıcı", active_companies)
    with col4:
        avg_days = df_filtered['Kalan_Gun'].mean()
        st.metric("Ort. Sözleşme Ömrü", f"{avg_days/365:.1f} Yıl" if not pd.isna(avg_days) else "-")

    st.divider()

    # --- SEKMELER ---
    # NOT: Coğrafi Analiz kaldırıldı, yerine Detaylı Bayi Sayıları geldi
    tab_risk, tab_detay, tab_market, tab_trend, tab_data = st.tabs([
        "⚡ Sözleşme & Risk", 
        "🔢 Detaylı Bayi Sayıları", 
        "🏢 Pazar & Rekabet", 
        "📈 Zaman Analizi",
        "📋 Ham Veri"
    ])

    # =================================================
    # TAB 1: RİSK ANALİZİ
    # =================================================
    with tab_risk:
        st.subheader("🚨 Kritik ve Yaklaşan Sözleşmeler (İlk 6 Ay)")
        critical_df = df_filtered[df_filtered['Kalan_Gun'] < 180].sort_values('Kalan_Gun')
        
        if not critical_df.empty:
            critical_df['Bitis_Tarih_Str'] = critical_df[target_date_col].dt.strftime('%Y-%m-%d')
            st.dataframe(
                critical_df[['Unvan', 'İl', 'İlçe', 'Dağıtım Şirketi', 'Bitis_Tarih_Str', 'Kalan_Gun', 'Risk_Durumu']],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Unvan": st.column_config.TextColumn("Bayi Adı", width="large"),
                    "Kalan_Gun": st.column_config.ProgressColumn("Kalan Gün", format="%d Gün", min_value=0, max_value=180),
                    "Bitis_Tarih_Str": "Bitiş Tarihi"
                }
            )
        else:
            st.success("Önümüzdeki 180 gün içinde bitecek sözleşme bulunmuyor.")

        c1, c2 = st.columns(2)
        with c1:
            df_filtered['Bitis_Yili'] = df_filtered[target_date_col].dt.year
            year_counts = df_filtered['Bitis_Yili'].value_counts().sort_index().reset_index()
            year_counts.columns = ['Yıl', 'Adet']
            curr_year = datetime.date.today().year
            year_counts = year_counts[(year_counts['Yıl'] >= curr_year) & (year_counts['Yıl'] <= curr_year + 10)]
            st.plotly_chart(px.bar(year_counts, x='Yıl', y='Adet', text='Adet', color='Adet', title="Yıllara Göre Bitişler", color_continuous_scale='Oranges'), use_container_width=True)
            
        with c2:
            risk_counts = df_filtered['Risk_Durumu'].value_counts().reset_index()
            risk_counts.columns = ['Durum', 'Adet']
            st.plotly_chart(px.pie(risk_counts, values='Adet', names='Durum', hole=0.4, title="Risk Dağılımı", 
                                  color_discrete_map={"SÜRESİ DOLDU 🚨":"red", "KRİTİK (<3 Ay) ⚠️":"orange", "YAKLAŞIYOR (<6 Ay) ⏳": "#FFD700", "GÜVENLİ ✅":"green"}), use_container_width=True)

    # =================================================
    # TAB 2: DETAYLI BAYİ SAYILARI (YENİ EKLENEN KISIM)
    # =================================================
    with tab_detay:
        # Senaryo kontrolü: Kullanıcı sol menüden şirket seçti mi?
        
        if not selected_companies:
            # SENARYO 1: Şirket seçilmedi -> TÜM ŞİRKETLERİ LİSTELE
            st.subheader("🏢 Tüm Dağıtım Şirketleri ve Bayi Sayıları")
            st.info("Sol menüden belirli bir şirket seçerek o şirketin şehir dağılımını görebilirsiniz.")
            
            # Veriyi hazırla
            comp_stats = df_filtered['Dağıtım Şirketi'].value_counts().reset_index()
            comp_stats.columns = ['Dağıtım Şirketi', 'Toplam Bayi Sayısı']
            
            col_d1, col_d2 = st.columns([1, 1])
            
            with col_d1:
                # Uzun bir tablo (Scroll edilebilir)
                st.dataframe(
                    comp_stats, 
                    use_container_width=True, 
                    height=600, # Tabloyu uzun tuttum ki hepsi görünsün
                    hide_index=True,
                    column_config={
                        "Dağıtım Şirketi": st.column_config.TextColumn("Şirket Adı", width="large"),
                        "Toplam Bayi Sayısı": st.column_config.NumberColumn("Bayi Sayısı", format="%d")
                    }
                )
                
            with col_d2:
                # Görsel olarak ilk 30'u gösterelim ki grafik patlamasın (ama tablo hepsini gösteriyor)
                st.write("**Grafiksel Gösterim (İlk 30 Şirket)**")
                fig_bar = px.bar(comp_stats.head(30), x='Toplam Bayi Sayısı', y='Dağıtım Şirketi', 
                                 text='Toplam Bayi Sayısı', orientation='h', height=600)
                fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_bar, use_container_width=True)

        else:
            # SENARYO 2: Şirket seçildi -> O ŞİRKETİN ŞEHİR DAĞILIMINI LİSTELE
            st.subheader(f"📍 Seçilen Şirketlerin Şehir Dağılımı")
            st.success(f"Şu an filtrelenen şirketler: {', '.join(selected_companies)}")
            
            # Şehir bazlı grupla
            city_stats = df_filtered['İl'].value_counts().reset_index()
            city_stats.columns = ['Şehir', 'Bayi Sayısı']
            
            col_d1, col_d2 = st.columns([1, 1])
            
            with col_d1:
                st.dataframe(
                    city_stats, 
                    use_container_width=True, 
                    height=600,
                    hide_index=True
                )
            
            with col_d2:
                st.write("**Grafiksel Dağılım**")
                fig_bar_city = px.bar(city_stats, x='Bayi Sayısı', y='Şehir', 
                                      text='Bayi Sayısı', orientation='h', height=600)
                fig_bar_city.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_bar_city, use_container_width=True)

    # =================================================
    # TAB 3: PAZAR & REKABET
    # =================================================
    with tab_market:
        c_tree, c_pie = st.columns([2, 1])
        with c_tree:
            st.subheader("Pazar Hakimiyet Haritası")
            st.plotly_chart(px.treemap(df_filtered, path=['Dağıtım Şirketi', 'İl'], color='Dağıtım Şirketi'), use_container_width=True)
        with c_pie:
            st.subheader("Pazar Payı")
            comp_counts = df_filtered['Dağıtım Şirketi'].value_counts().reset_index()
            comp_counts.columns = ['Şirket', 'Adet']
            if len(comp_counts) > 10:
                top_10 = comp_counts.iloc[:10]
                others = pd.DataFrame({'Şirket': ['DİĞERLERİ'], 'Adet': [comp_counts.iloc[10:]['Adet'].sum()]})
                comp_counts = pd.concat([top_10, others], ignore_index=True)
            st.plotly_chart(px.pie(comp_counts, values='Adet', names='Şirket', hole=0.4), use_container_width=True)

    # =================================================
    # TAB 4: ZAMAN ANALİZİ
    # =================================================
    with tab_trend:
        st.subheader("Yıllık Yeni Bayi Girişi")
        if 'Dağıtıcı ile Yapılan Sözleşme Başlangıç Tarihi' in df_filtered.columns:
            trend_df = df_filtered.copy()
            trend_df['Yil'] = trend_df['Dağıtıcı ile Yapılan Sözleşme Başlangıç Tarihi'].dt.year
            yearly_growth = trend_df['Yil'].value_counts().sort_index().reset_index()
            yearly_growth.columns = ['Yıl', 'Yeni Bayi Sayısı']
            yearly_growth = yearly_growth[yearly_growth['Yıl'] >= 2000]
            st.plotly_chart(px.line(yearly_growth, x='Yıl', y='Yeni Bayi Sayısı', markers=True), use_container_width=True)

    # =================================================
    # TAB 5: HAM VERİ
    # =================================================
    with tab_data:
        st.subheader("📋 Veri Listesi")
        show_cols = ['Lisans No', 'Unvan', 'İl', 'İlçe', 'Dağıtım Şirketi', target_date_col, 'Kalan_Gun', 'Risk_Durumu']
        existing_cols = [c for c in show_cols if c in df_filtered.columns]
        export_df = df_filtered[existing_cols].sort_values('Kalan_Gun')
        
        if target_date_col in export_df.columns:
            export_df[target_date_col] = export_df[target_date_col].dt.strftime('%Y-%m-%d')
        
        st.download_button("📥 Listeyi İndir (CSV)", export_df.to_csv(index=False).encode('utf-8'), "filtrelenmis_bayi_listesi.csv", "text/csv")
        
        def highlight_risk(val):
            if val == 'SÜRESİ DOLDU 🚨': return 'background-color: #ffcccc; color: black'
            if val == 'KRİTİK (<3 Ay) ⚠️': return 'background-color: #ffeebb; color: black'
            if val == 'YAKLAŞIYOR (<6 Ay) ⏳': return 'background-color: #fff8c4; color: black'
            return ''
        st.dataframe(export_df.style.applymap(highlight_risk, subset=['Risk_Durumu']), use_container_width=True, height=600)

if __name__ == "__main__":
    main()
