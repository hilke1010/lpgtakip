import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import numpy as np
import os

# --- 1. SAYFA VE TASARIM AYARLARI ---
st.set_page_config(
    page_title="LPG Bayi Takip Paneli",
    page_icon="⛽",
    layout="wide",
    initial_sidebar_state="collapsed"  # Menüyü varsayılan olarak kapalı tutar
)

# --- 2. SABİT EXCEL DOSYASININ ADI ---
# DİKKAT: Excel dosyasını bu isimle python dosyasıyla yan yana koymalısın!
SABIT_DOSYA_ADI = "lpg_veri.xlsx"

# --- 3. KOORDİNATLAR (HARİTA İÇİN) ---
IL_KOORDINATLARI = {
    'ADANA': [37.0000, 35.3213], 'ADIYAMAN': [37.7648, 38.2786], 'AFYONKARAHİSAR': [38.7507, 30.5567],
    'AĞRI': [39.7191, 43.0503], 'AKSARAY': [38.3687, 34.0370], 'AMASYA': [40.6499, 35.8353],
    'ANKARA': [39.9334, 32.8597], 'ANTALYA': [36.8969, 30.7133], 'ARDAHAN': [41.1105, 42.7022],
    'ARTVİN': [41.1828, 41.8183], 'AYDIN': [37.8560, 27.8416], 'BALIKESİR': [39.6484, 27.8826],
    'BARTIN': [41.6344, 32.3375], 'BATMAN': [37.8812, 41.1351], 'BAYBURT': [40.2552, 40.2249],
    'BİLECİK': [40.1451, 29.9798], 'BİNGÖL': [38.8854, 40.498], 'BİTLİS': [38.3938, 42.1232],
    'BOLU': [40.7392, 31.6089], 'BURDUR': [37.7204, 30.2908], 'BURSA': [40.1885, 29.0610],
    'ÇANAKKALE': [40.1553, 26.4142], 'ÇANKIRI': [40.6013, 33.6134], 'ÇORUM': [40.5506, 34.9556],
    'DENİZLİ': [37.7765, 29.0864], 'DİYARBAKIR': [37.9144, 40.2306], 'DÜZCE': [40.8438, 31.1565],
    'EDİRNE': [41.6771, 26.5557], 'ELAZIĞ': [38.6810, 39.2264], 'ERZİNCAN': [39.7500, 39.5000],
    'ERZURUM': [39.9000, 41.2700], 'ESKİŞEHİR': [39.7767, 30.5206], 'GAZİANTEP': [37.0662, 37.3833],
    'GİRESUN': [40.9128, 38.3895], 'GÜMÜŞHANE': [40.4600, 39.4700], 'HAKKARİ': [37.5833, 43.7333],
    'HATAY': [36.4018, 36.3498], 'IĞDIR': [39.9167, 44.0333], 'ISPARTA': [37.7648, 30.5566],
    'İSTANBUL': [41.0082, 28.9784], 'İZMİR': [38.4192, 27.1287], 'KAHRAMANMARAŞ': [37.5858, 36.9371],
    'KARABÜK': [41.2061, 32.6204], 'KARAMAN': [37.1759, 33.2287], 'KARS': [40.6167, 43.1000],
    'KASTAMONU': [41.3887, 33.7827], 'KAYSERİ': [38.7312, 35.4787], 'KIRIKKALE': [39.8468, 33.5153],
    'KIRKLARELİ': [41.7333, 27.2167], 'KIRŞEHİR': [39.1425, 34.1709], 'KİLİS': [36.7184, 37.1212],
    'KOCAELİ': [40.8533, 29.8815], 'KONYA': [37.8667, 32.4833], 'KÜTAHYA': [39.4167, 29.9833],
    'MALATYA': [38.3552, 38.3095], 'MANİSA': [38.6191, 27.4289], 'MARDİN': [37.3212, 40.7245],
    'MERSİN': [36.8000, 34.6333], 'MUĞLA': [37.2153, 28.3636], 'MUŞ': [38.9462, 41.7539],
    'NEVŞEHİR': [38.6939, 34.6857], 'NİĞDE': [37.9667, 34.6833], 'ORDU': [40.9839, 37.8764],
    'OSMANİYE': [37.0742, 36.2476], 'RİZE': [41.0201, 40.5234], 'SAKARYA': [40.7569, 30.3783],
    'SAMSUN': [41.2867, 36.3300], 'SİİRT': [37.9333, 41.9500], 'SİNOP': [42.0231, 35.1531],
    'SİVAS': [39.7477, 37.0179], 'ŞANLIURFA': [37.1591, 38.7969], 'ŞIRNAK': [37.5164, 42.4611],
    'TEKİRDAĞ': [40.9833, 27.5167], 'TOKAT': [40.3167, 36.5500], 'TRABZON': [41.0027, 39.7168],
    'TUNCELİ': [39.1079, 39.5401], 'UŞAK': [38.6823, 29.4082], 'VAN': [38.4891, 43.4089],
    'YALOVA': [40.6500, 29.2667], 'YOZGAT': [39.8181, 34.8147], 'ZONGULDAK': [41.4564, 31.7987]
}

# --- 4. STİL AYARLARI ---
st.markdown("""
<style>
    .stMetric { background-color: #f4f6f9; border: 1px solid #e0e0e0; border-radius: 8px; padding: 10px; }
    .block-container { padding-top: 1rem; }
</style>
""", unsafe_allow_html=True)


# --- 5. VERİ YÜKLEME FONKSİYONU (CACHE İLE HIZLANDIRILMIŞ) ---
@st.cache_data
def veriyi_yukle(dosya_yolu):
    """Excel dosyasını okur ve önbelleğe alır."""
    if not os.path.exists(dosya_yolu):
        return None

    df = pd.read_excel(dosya_yolu)
    df.columns = [c.strip() for c in df.columns]  # Boşluk temizleme

    # Tarih Dönüşümleri
    date_cols = ['Başlangıç Tarih', 'Bitiş Tarih', 'Dağıtıcı ile Yapılan Sözleşme Başlangıç Tarihi',
                 'Dağıtıcı ile Yapılan Sözleşme Bitiş Tarihi']
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce')

    return df


def main():
    st.title("🚀 LPG Bayi & Sözleşme Analiz Paneli")

    # --- DOSYAYI OKU ---
    df = veriyi_yukle(SABIT_DOSYA_ADI)

    if df is None:
        st.error(f"HATA: '{SABIT_DOSYA_ADI}' dosyası bulunamadı!")
        st.warning("Lütfen Excel dosyasını proje klasörüne yüklediğinizden emin olun.")
        st.stop()  # Kodun geri kalanını çalıştırma

    # --- VERİ İŞLEME ---
    target_date_col = 'Dağıtıcı ile Yapılan Sözleşme Bitiş Tarihi'
    if target_date_col not in df.columns:
        st.error("Hata: 'Dağıtıcı ile Yapılan Sözleşme Bitiş Tarihi' sütunu Excel'de yok.")
        st.stop()

    # Kalan Gün ve Risk Hesaplama
    today = pd.to_datetime(datetime.date.today())
    df['Kalan_Gun'] = (df[target_date_col] - today).dt.days

    def risk_durumu(gun):
        if pd.isna(gun): return "Belirsiz"
        if gun < 0: return "Sözleşme Bitmiş! 🚨"
        if gun < 90: return "Kritik (<3 Ay) ⚠️"
        if gun < 180: return "Yaklaşıyor (<6 Ay) ⏳"
        return "Güvenli ✅"

    df['Risk_Durumu'] = df['Kalan_Gun'].apply(risk_durumu)

    # --- SIDEBAR FILTRELER ---
    with st.sidebar:
        st.image("https://lisans.epdk.gov.tr/epvys-web/images/epdk_logo.png", width=100)  # Logo Opsiyonel
        st.header("🔍 Filtreleme")

        cities = sorted(df['İl'].dropna().unique().tolist())
        sel_city = st.multiselect("İl Seçimi", cities)

        companies = sorted(df['Dağıtım Şirketi'].dropna().unique().tolist())
        sel_comp = st.multiselect("Şirket Seçimi", companies)

    # Filtre Uygulama
    df_filtered = df.copy()
    if sel_city: df_filtered = df_filtered[df_filtered['İl'].isin(sel_city)]
    if sel_comp: df_filtered = df_filtered[df_filtered['Dağıtım Şirketi'].isin(sel_comp)]

    # --- KPI METRİKLERİ ---
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Toplam Bayi", len(df_filtered))

    riskli_adet = len(df_filtered[df_filtered['Kalan_Gun'] < 90])
    k2.metric("Riskli Sözleşme (<90 Gün)", riskli_adet, delta="-Acil", delta_color="inverse")

    ort_gun = df_filtered['Kalan_Gun'].mean()
    k3.metric("Ort. Kalan Gün", f"{ort_gun:.0f}" if not pd.isna(ort_gun) else "-")

    k4.metric("Şirket Sayısı", df_filtered['Dağıtım Şirketi'].nunique())

    st.divider()

    # --- SEKMELER ---
    tab_risk, tab_harita, tab_pazar, tab_veri = st.tabs(
        ["⏳ Sözleşme & Risk", "🗺️ Harita Analizi", "📊 Pazar Payı", "📋 Detaylı Veri"])

    # ==============================================
    # TAB 1: RİSK VE SÖZLEŞME ANALİZİ
    # ==============================================
    with tab_risk:
        st.subheader("🚨 ACİL DURUM TABLOSU: İlk 90 Günde Bitenler")

        acil_df = df_filtered[df_filtered['Kalan_Gun'] < 90].sort_values('Kalan_Gun').copy()

        if not acil_df.empty:
            acil_df['Bitis_Str'] = acil_df[target_date_col].dt.strftime('%Y-%m-%d')
            st.dataframe(
                acil_df[['Unvan', 'İl', 'Dağıtım Şirketi', 'Bitis_Str', 'Kalan_Gun']],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Unvan": st.column_config.TextColumn("Bayi Unvanı", width="large"),
                    "Kalan_Gun": st.column_config.ProgressColumn(
                        "Kalan Gün", format="%d Gün", min_value=0, max_value=90,
                    ),
                    "Bitis_Str": "Bitiş Tarihi"
                }
            )
        else:
            st.success("Riskli sözleşme bulunmamaktadır.")

        st.write("---")
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.subheader("📅 Yıllara Göre Bitişler")
            df_filtered['Yil'] = df_filtered[target_date_col].dt.year
            y_data = df_filtered['Yil'].value_counts().sort_index().reset_index()
            y_data.columns = ['Yıl', 'Adet']
            st.plotly_chart(px.bar(y_data, x='Yıl', y='Adet', text='Adet', color='Adet', color_continuous_scale='Reds'),
                            use_container_width=True)

        with col_g2:
            st.subheader("⏳ Başlangıç vs Bitiş")
            st.plotly_chart(
                px.scatter(df_filtered, x='Dağıtıcı ile Yapılan Sözleşme Başlangıç Tarihi', y=target_date_col,
                           color='Risk_Durumu'), use_container_width=True)

    # ==============================================
    # TAB 2: HARİTA
    # ==============================================
    with tab_harita:
        c_map, c_heat = st.columns([3, 1])
        with c_map:
            st.subheader("📍 Bayi Konumları")
            map_data = df_filtered.copy()
            lats, lons = [], []
            for il in map_data['İl']:
                k = str(il).upper().replace('İ', 'I')
                c = None
                for city, coord in IL_KOORDINATLARI.items():
                    if city in k: c = coord; break
                if c:
                    lats.append(c[0] + np.random.uniform(-0.02, 0.02))
                    lons.append(c[1] + np.random.uniform(-0.02, 0.02))
                else:
                    lats.append(None);
                    lons.append(None)

            map_data['lat'] = lats;
            map_data['lon'] = lons
            map_data = map_data.dropna(subset=['lat'])

            if not map_data.empty:
                fig_m = px.scatter_mapbox(map_data, lat='lat', lon='lon', color='Dağıtım Şirketi', hover_name='Unvan',
                                          zoom=5, height=600, mapbox_style="carto-positron")
                st.plotly_chart(fig_m, use_container_width=True)
            else:
                st.warning("Şehir eşleştirmesi yapılamadı.")

        with c_heat:
            st.subheader("🔥 Yoğunluk")
            top_c = df_filtered['İl'].value_counts().head(15).index
            heat_d = df_filtered[df_filtered['İl'].isin(top_c)]
            st.plotly_chart(px.density_heatmap(heat_d, x='İl', y='Dağıtım Şirketi', color_continuous_scale='Blues'),
                            use_container_width=True)

    # ==============================================
    # TAB 3: PAZAR PAYI
    # ==============================================
    with tab_pazar:
        col_tree, col_pie = st.columns(2)

        with col_tree:
            st.subheader("🏢 Marka Hiyerarşisi")
            fig_tree = px.treemap(df_filtered, path=['Dağıtım Şirketi', 'İl'])
            st.plotly_chart(fig_tree, use_container_width=True)

        with col_pie:
            st.subheader("🍰 Pazar Payı")
            pie_source = df_filtered['Dağıtım Şirketi'].value_counts().reset_index()
            pie_source.columns = ['Şirket', 'Adet']

            if len(pie_source) > 12:
                top_12 = pie_source.iloc[:12]
                other_val = pie_source.iloc[12:]['Adet'].sum()
                other_row = pd.DataFrame({'Şirket': ['DİĞERLERİ'], 'Adet': [other_val]})
                pie_source = pd.concat([top_12, other_row], ignore_index=True)

            fig_pie = px.pie(pie_source, values='Adet', names='Şirket', hole=0.4)
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            fig_pie.update_layout(showlegend=True,
                                  legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5))
            st.plotly_chart(fig_pie, use_container_width=True)

    # ==============================================
    # TAB 4: DETAYLI VERİ
    # ==============================================
    with tab_veri:
        st.subheader("📋 Veri Listesi")

        export_df = df_filtered[['Lisans No', 'Unvan', 'İl', 'İlçe', 'Dağıtım Şirketi', target_date_col, 'Kalan_Gun',
                                 'Risk_Durumu']].sort_values('Kalan_Gun')
        export_df[target_date_col] = export_df[target_date_col].dt.strftime('%Y-%m-%d')

        st.download_button("📥 Listeyi İndir (Excel/CSV)", export_df.to_csv(index=False).encode('utf-8'),
                           "lpg_bayi_listesi.csv", "text/csv")

        def color_row(val):
            if "🚨" in val: return 'background-color: #ffcccc'
            if "⚠️" in val: return 'background-color: #ffeebb'
            return ''

        st.dataframe(export_df.style.applymap(color_row, subset=['Risk_Durumu']), use_container_width=True, height=600)


if __name__ == "__main__":
    main()
