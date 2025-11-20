import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import numpy as np
import os
from docx import Document # Word okumak için
import re # Metin ayıklamak için

# --- 1. SAYFA VE GENEL AYARLAR ---
st.set_page_config(
    page_title="EPDK LPG Pazar Analizi",
    page_icon="⛽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. DOSYA İSİMLERİ ---
SABIT_DOSYA_ADI = "lpg_veri.xlsx"
WORD_DOSYA_ADI = "satis.docx"

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

# --- 4. VERİ YÜKLEME (EXCEL) ---
@st.cache_data
def load_data(file_path):
    if not os.path.exists(file_path):
        return None, None
    
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
        st.error(f"Excel okuma hatası: {e}")
        return None, None

# --- 5. VERİ YÜKLEME (WORD) ---
@st.cache_data
def load_word_tables(file_path):
    if not os.path.exists(file_path):
        return None

    try:
        doc = Document(file_path)
        sehir_tablolari = {}
        
        # Word içindeki "Tablo X: Şehir" yazılarını bul
        pattern = re.compile(r"Tablo\s+[\d\.]+\s*:\s*(.+)", re.IGNORECASE)
        
        bulunan_sehirler = []
        for para in doc.paragraphs:
            match = pattern.search(para.text)
            if match:
                bulunan_sehirler.append(match.group(1).strip().upper().replace('i', 'İ').replace('ı', 'I'))
        
        tables = doc.tables
        min_len = min(len(bulunan_sehirler), len(tables))
        
        for i in range(min_len):
            city = bulunan_sehirler[i]
            table = tables[i]
            
            data = []
            for row_idx, row in enumerate(table.rows):
                text = [cell.text.strip() for cell in row.cells]
                # Başlık satırlarını atla (Genelde ilk 2 satır başlıktır)
                if row_idx >= 2: 
                    data.append(text)
            
            # Standart Başlıklar
            custom_headers = [
                "Lisans Sahibinin Unvanı", 
                "Tüplü Satış(ton)", "Tüplü Pay(%)",
                "Dökme Satış(ton)", "Dökme Pay(%)",
                "Otogaz Satış(ton)", "Otogaz Pay(%)",
                "Toplam Satış(ton)", "Toplam Pay(%)"
            ]
            
            if len(table.rows[0].cells) == len(custom_headers):
                 df_table = pd.DataFrame(data, columns=custom_headers)
            else:
                df_table = pd.DataFrame(data)
            
            # Sayısal dönüşüm
            for col in df_table.columns[1:]:
                try:
                    df_table[col] = df_table[col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
                    df_table[col] = pd.to_numeric(df_table[col], errors='coerce').fillna(0)
                except:
                    pass
                
            sehir_tablolari[city] = df_table
            
        return sehir_tablolari

    except Exception as e:
        st.error(f"Word okuma hatası: {e}")
        return None

def main():
    # --- VERİLERİ ÇEK ---
    df, target_date_col = load_data(SABIT_DOSYA_ADI)
    word_data = load_word_tables(WORD_DOSYA_ADI)
    
    if df is None:
        st.error(f"❌ HATA: '{SABIT_DOSYA_ADI}' bulunamadı.")
        st.stop()

    # --- SIDEBAR FİLTRELERİ (EXCEL İÇİN) ---
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

        st.info(f"Excel Kayıt Sayısı: {len(df)}")

    # --- FİLTRELEME MOTORU ---
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
        st.metric("Acil Sözleşme (<90 Gün)", riskli_sayi, delta="Acil", delta_color="inverse")
    with col3:
        active_companies = df_filtered['Dağıtım Şirketi'].nunique()
        st.metric("Aktif Dağıtıcı", active_companies)
    with col4:
        avg_days = df_filtered['Kalan_Gun'].mean()
        st.metric("Ort. Sözleşme Ömrü", f"{avg_days/365:.1f} Yıl" if not pd.isna(avg_days) else "-")

    st.divider()

    # --- SEKMELER ---
    tab_risk, tab_detay, tab_market, tab_trend, tab_epdk, tab_data = st.tabs([
        "⚡ Sözleşme & Risk", 
        "🔢 Detaylı Bayi", 
        "🏢 Pazar & Rekabet", 
        "📈 Zaman Analizi",
        "📄 EPDK Satış Raporu", # WORD BURADA
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
            st.success("Filtrelenen veride önümüzdeki 180 gün içinde bitecek sözleşme bulunmuyor.")

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
    # TAB 2: DETAYLI BAYİ SAYILARI
    # =================================================
    with tab_detay:
        if not selected_companies:
            st.subheader("🏢 Tüm Dağıtım Şirketleri ve Bayi Sayıları")
            st.info("Sol menüden şirket seçerseniz, o şirketin şehir dağılımını görürsünüz.")
            comp_stats = df_filtered['Dağıtım Şirketi'].value_counts().reset_index()
            comp_stats.columns = ['Dağıtım Şirketi', 'Toplam Bayi Sayısı']
            col_d1, col_d2 = st.columns([1, 1])
            with col_d1:
                st.dataframe(comp_stats, use_container_width=True, height=600, hide_index=True,
                             column_config={"Dağıtım Şirketi": st.column_config.TextColumn("Şirket Adı", width="large"), "Toplam Bayi Sayısı": st.column_config.NumberColumn("Bayi Sayısı", format="%d")})
            with col_d2:
                st.plotly_chart(px.bar(comp_stats.head(30), x='Toplam Bayi Sayısı', y='Dağıtım Şirketi', text='Toplam Bayi Sayısı', orientation='h', height=600, title="İlk 30 Şirket"), use_container_width=True)
        else:
            st.subheader(f"📍 Seçilen Şirketlerin Şehir Dağılımı")
            city_stats = df_filtered['İl'].value_counts().reset_index()
            city_stats.columns = ['Şehir', 'Bayi Sayısı']
            col_d1, col_d2 = st.columns([1, 1])
            with col_d1:
                st.dataframe(city_stats, use_container_width=True, height=600, hide_index=True)
            with col_d2:
                st.plotly_chart(px.bar(city_stats, x='Bayi Sayısı', y='Şehir', text='Bayi Sayısı', orientation='h', height=600), use_container_width=True)

    # =================================================
    # TAB 3: PAZAR & REKABET (DONUT GRAFİK DAHİL)
    # =================================================
    with tab_market:
        c_tree, c_pie = st.columns([2, 1])
        with c_tree:
            st.subheader("Pazar Hakimiyet Haritası (Treemap)")
            st.plotly_chart(px.treemap(df_filtered, path=['Dağıtım Şirketi', 'İl'], 
                                      color='Dağıtım Şirketi', color_discrete_sequence=px.colors.qualitative.Set3), use_container_width=True)
        
        with c_pie:
            st.subheader("🍰 Pazar Payı (Donut)")
            comp_counts = df_filtered['Dağıtım Şirketi'].value_counts().reset_index()
            comp_counts.columns = ['Şirket', 'Adet']
            total_bayi = comp_counts['Adet'].sum()
            
            if len(comp_counts) > 10:
                top_10 = comp_counts.iloc[:10]
                other_val = comp_counts.iloc[10:]['Adet'].sum()
                comp_counts = pd.concat([top_10, pd.DataFrame({'Şirket': ['DİĞERLERİ'], 'Adet': [other_val]})], ignore_index=True)
            
            fig_pie = px.pie(comp_counts, values='Adet', names='Şirket', hole=0.5, color_discrete_sequence=px.colors.qualitative.Set3)
            fig_pie.update_traces(textposition='inside', textinfo='percent+label', textfont_size=13)
            fig_pie.add_annotation(text=f"{total_bayi}", x=0.5, y=0.5, font_size=24, showarrow=False, font_weight='bold')
            fig_pie.add_annotation(text="TOPLAM", x=0.5, y=0.4, font_size=12, showarrow=False)
            fig_pie.update_layout(showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5))
            st.plotly_chart(fig_pie, use_container_width=True)

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
    # TAB 5: EPDK SATIŞ RAPORU (WORD DOSYASINDAN)
    # =================================================
    with tab_epdk:
        st.header("📄 EPDK Satış Raporları (Word)")
        st.markdown("Word dosyasından çekilen güncel satış verileri.")
        
        if word_data:
            # Şehir listesi (Word'den gelen)
            sehirler = sorted(list(word_data.keys()))
            
            if not sehirler:
                st.warning(f"'{WORD_DOSYA_ADI}' içinde 'Tablo X: Şehir' formatında başlık bulunamadı.")
            else:
                col_w1, col_w2 = st.columns([1, 2])
                with col_w1:
                    secilen_il_word = st.selectbox("📊 Satış Raporunu Görmek İstediğiniz İli Seçin:", sehirler)
                
                if secilen_il_word:
                    tablo_df = word_data[secilen_il_word]
                    
                    st.markdown(f"### 📍 {secilen_il_word} İli LPG Satış Tablosu")
                    
                    # TABLOYU RENKLENDİRMEDEN (HATA OLMASIN DİYE) DÜZ GÖSTERİYORUZ
                    st.dataframe(
                        tablo_df,
                        use_container_width=True,
                        height=500
                    )
                    
                    # ALTINA GRAFİĞİNİ ÇİZİYORUZ (GÖRSELİ GÜÇLENDİRMEK İÇİN)
                    if "Toplam Satış(ton)" in tablo_df.columns and "Lisans Sahibinin Unvanı" in tablo_df.columns:
                        # Toplam satırını çıkarıp grafik çizelim
                        grafik_data = tablo_df[tablo_df["Lisans Sahibinin Unvanı"] != "TOPLAM"].copy()
                        # En yüksekten düşüğe sırala
                        grafik_data = grafik_data.sort_values("Toplam Satış(ton)", ascending=True).tail(15) # En büyük 15
                        
                        fig_word = px.bar(
                            grafik_data, 
                            x="Toplam Satış(ton)", 
                            y="Lisans Sahibinin Unvanı", 
                            text="Toplam Satış(ton)", 
                            orientation='h', 
                            title=f"{secilen_il_word} - Şirket Bazlı Satış Miktarları (Ton)",
                            color="Toplam Satış(ton)",
                            color_continuous_scale="Blues"
                        )
                        st.plotly_chart(fig_word, use_container_width=True)
        else:
            st.error(f"Word dosyası ({WORD_DOSYA_ADI}) okunamadı veya bulunamadı.")

    # =================================================
    # TAB 6: HAM VERİ
    # =================================================
    with tab_data:
        st.subheader("📋 Excel Ham Veri")
        show_cols = ['Lisans No', 'Unvan', 'İl', 'İlçe', 'Dağıtım Şirketi', target_date_col, 'Kalan_Gun', 'Risk_Durumu']
        existing_cols = [c for c in show_cols if c in df_filtered.columns]
        export_df = df_filtered[existing_cols].sort_values('Kalan_Gun')
        
        if target_date_col in export_df.columns:
            export_df[target_date_col] = export_df[target_date_col].dt.strftime('%Y-%m-%d')
        
        st.download_button("📥 Excel Listesini İndir (CSV)", export_df.to_csv(index=False).encode('utf-8'), "bayi_listesi.csv", "text/csv")
        
        def highlight_risk(val):
            if val == 'SÜRESİ DOLDU 🚨': return 'background-color: #ffcccc; color: black'
            if val == 'KRİTİK (<3 Ay) ⚠️': return 'background-color: #ffeebb; color: black'
            if val == 'YAKLAŞIYOR (<6 Ay) ⏳': return 'background-color: #fff8c4; color: black'
            return ''
        st.dataframe(export_df.style.applymap(highlight_risk, subset=['Risk_Durumu']), use_container_width=True, height=600)

if __name__ == "__main__":
    main()
