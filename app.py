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
WORD_GUNCEL = "satis.docx"       
WORD_ONCEKI = "bionceki.docx"    
WORD_GECEN_YIL = "gecensene.docx" 

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

# --- 5. GELİŞMİŞ WORD OKUYUCU ---
def iter_block_items(parent):
    if isinstance(parent, _Document):
        parent_elm = parent.element.body
    elif isinstance(parent, _Cell):
        parent_elm = parent._tc
    else:
        raise ValueError("something's not right")

    for child in parent_elm.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)

@st.cache_data
def load_word_tables_robust(file_path):
    if not os.path.exists(file_path): return None

    try:
        doc = Document(file_path)
        sehir_tablolari = {}
        current_city = None 
        city_pattern = re.compile(r"Tablo\s+[\d\.]+\s*:\s*(.+)", re.IGNORECASE)

        for block in iter_block_items(doc):
            if isinstance(block, Paragraph):
                text = block.text.strip()
                match = city_pattern.search(text)
                if match:
                    raw_city = match.group(1).strip()
                    raw_city = re.sub(r'\d+$', '', raw_city).strip()
                    current_city = raw_city.upper().replace('i', 'İ').replace('ı', 'I')
            
            elif isinstance(block, Table):
                if current_city:
                    data = []
                    for row in block.rows:
                        row_data = []
                        seen_cells = set()
                        for cell in row.cells:
                            if id(cell) not in seen_cells:
                                row_data.append(cell.text.strip())
                                seen_cells.add(id(cell))
                        if not any(row_data): continue
                        data.append(row_data)
                    
                    if len(data) > 3:
                        headers = [
                            "Lisans Sahibinin Unvanı", 
                            "Tüplü Satış(ton)", "Tüplü Pay(%)",
                            "Dökme Satış(ton)", "Dökme Pay(%)",
                            "Otogaz Satış(ton)", "Otogaz Pay(%)",
                            "Toplam Satış(ton)", "Toplam Pay(%)"
                        ]
                        cleaned_body = []
                        for r in data[2:]:
                            if len(r) >= 9: cleaned_body.append(r[:9])
                            else: cleaned_body.append(r)

                        df_table = pd.DataFrame(cleaned_body)
                        if df_table.shape[1] == 9: df_table.columns = headers
                        
                        for col in df_table.columns:
                            if "Satış" in str(col) or "Pay" in str(col):
                                try:
                                    df_table[col] = df_table[col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
                                    df_table[col] = pd.to_numeric(df_table[col], errors='coerce').fillna(0)
                                except: pass
                        
                        sehir_tablolari[current_city] = df_table
                    
                    current_city = None
        return sehir_tablolari

    except Exception as e:
        st.error(f"Word okuma hatası ({file_path}): {e}")
        return None

def main():
    # --- VERİ ÇEKME ---
    df, target_date_col = load_data(SABIT_DOSYA_ADI)
    
    word_guncel = load_word_tables_robust(WORD_GUNCEL)
    word_onceki = load_word_tables_robust(WORD_ONCEKI)
    word_gecenyil = load_word_tables_robust(WORD_GECEN_YIL)
    
    if df is None:
        st.error(f"❌ HATA: '{SABIT_DOSYA_ADI}' bulunamadı.")
        st.stop()

    # --- SIDEBAR ---
    with st.sidebar:
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
        
        st.info(f"Excel Kayıt: {len(df)}")

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

    # --- SEKMELER ---
    tab_risk, tab_detay, tab_market, tab_trend, tab_epdk, tab_kiyas, tab_data = st.tabs([
        "⚡ Sözleşme & Risk", "🔢 Detaylı Bayi", "🏢 Pazar & Rekabet", "📈 Zaman Analizi", "📄 EPDK Satış Raporu", "📊 Detaylı Kıyaslama", "📋 Ham Veri"
    ])

    # 1. RİSK
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
            st.plotly_chart(px.pie(risk_counts, values='Adet', names='Durum', hole=0.4, title="Risk Dağılımı",
                                   color_discrete_map={"SÜRESİ DOLDU 🚨":"red", "KRİTİK (<3 Ay) ⚠️":"orange", "YAKLAŞIYOR (<6 Ay) ⏳": "#FFD700", "GÜVENLİ ✅":"green"}), use_container_width=True)

    # 2. DETAY
    with tab_detay:
        if not selected_companies:
            comp_stats = df_filtered['Dağıtım Şirketi'].value_counts().reset_index()
            comp_stats.columns = ['Şirket', 'Toplam Bayi']
            comp_stats.index = np.arange(1, len(comp_stats) + 1)
            c_d1, c_d2 = st.columns(2)
            with c_d1: st.dataframe(comp_stats, use_container_width=True, height=600)
            with c_d2: 
                fig_comp = px.bar(comp_stats.head(30), x='Toplam Bayi', y='Şirket', orientation='h', height=600, text='Toplam Bayi')
                fig_comp.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_comp, use_container_width=True)
        else:
            city_stats = df_filtered['İl'].value_counts().reset_index()
            city_stats.columns = ['Şehir', 'Bayi Sayısı']
            city_stats.index = np.arange(1, len(city_stats) + 1)
            c_d1, c_d2 = st.columns(2)
            with c_d1: st.dataframe(city_stats, use_container_width=True, height=600)
            with c_d2: 
                fig_city = px.bar(city_stats, x='Bayi Sayısı', y='Şehir', orientation='h', height=600, text='Bayi Sayısı')
                fig_city.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_city, use_container_width=True)

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

    # 4. ZAMAN
    with tab_trend:
        st.subheader("📈 Yıllık Yeni Bayi Girişi")
        if 'Dağıtıcı ile Yapılan Sözleşme Başlangıç Tarihi' in df_filtered.columns:
            dy = df_filtered.copy()
            dy['Yil'] = dy['Dağıtıcı ile Yapılan Sözleşme Başlangıç Tarihi'].dt.year
            yg = dy['Yil'].value_counts().sort_index().reset_index()
            yg.columns=['Yıl','Yeni Bayi']
            st.plotly_chart(px.line(yg[yg['Yıl']>=2000], x='Yıl', y='Yeni Bayi', markers=True), use_container_width=True)

    # 5. EPDK RAPORU (Sadece Güncel)
    with tab_epdk:
        st.header("📄 EPDK Satış Raporu (Güncel Ay)")
        if word_guncel:
            sehirler = sorted(list(word_guncel.keys()))
            secilen_il_word = st.selectbox("İl Seçin:", sehirler)
            if secilen_il_word:
                tablo_df = word_guncel[secilen_il_word]
                st.markdown(f"### 📍 {secilen_il_word} Satış Tablosu")
                tablo_df.index = np.arange(1, len(tablo_df) + 1)
                try:
                    st.dataframe(tablo_df.style.format(precision=2).background_gradient(cmap="Blues", subset=["Toplam Satış(ton)"]), use_container_width=True, height=600)
                except:
                    st.dataframe(tablo_df, use_container_width=True, height=600)
        else: st.error("Güncel Word dosyası bulunamadı.")

    # 6. DETAYLI KIYASLAMA (İSTEĞİNİZE GÖRE GÜNCELLENDİ)
    with tab_kiyas:
        st.header("📊 Detaylı Ürün Bazlı Kıyaslama")
        st.info("Otogaz, Tüplü ve Dökme verilerinin Güncel, Önceki Ay ve Geçen Yıl karşılaştırması.")

        if word_guncel:
            sehirler_kiyas = sorted(list(word_guncel.keys()))
            secilen_il_kiyas = st.selectbox("Kıyaslama İçin İl Seçin:", sehirler_kiyas, index=0)

            if secilen_il_kiyas:
                df_guncel = word_guncel.get(secilen_il_kiyas)
                df_onceki = word_onceki.get(secilen_il_kiyas) if word_onceki else None
                df_gecenyil = word_gecenyil.get(secilen_il_kiyas) if word_gecenyil else None

                if df_guncel is not None:
                    # Tüm satış tiplerini alıyoruz
                    cols_map = {
                        "Lisans Sahibinin Unvanı": "Firma",
                        "Otogaz Satış(ton)": "Otogaz",
                        "Tüplü Satış(ton)": "Tüplü",
                        "Dökme Satış(ton)": "Dökme",
                        "Toplam Satış(ton)": "Toplam"
                    }
                    
                    # --- GÜNCEL VERİ ---
                    base_df = df_guncel[list(cols_map.keys())].copy()
                    base_df.columns = ["Firma", "Otogaz_G", "Tüplü_G", "Dökme_G", "Toplam_G"]

                    # --- ÖNCEKİ AY ---
                    if df_onceki is not None:
                        temp_prev = df_onceki[list(cols_map.keys())].copy()
                        temp_prev.columns = ["Firma", "Otogaz_Ö", "Tüplü_Ö", "Dökme_Ö", "Toplam_Ö"]
                        base_df = pd.merge(base_df, temp_prev, on="Firma", how="left")
                    else:
                        for c in ["Otogaz_Ö", "Tüplü_Ö", "Dökme_Ö", "Toplam_Ö"]: base_df[c] = 0

                    # --- GEÇEN YIL ---
                    if df_gecenyil is not None:
                        temp_last = df_gecenyil[list(cols_map.keys())].copy()
                        temp_last.columns = ["Firma", "Otogaz_Y", "Tüplü_Y", "Dökme_Y", "Toplam_Y"]
                        base_df = pd.merge(base_df, temp_last, on="Firma", how="left")
                    else:
                        for c in ["Otogaz_Y", "Tüplü_Y", "Dökme_Y", "Toplam_Y"]: base_df[c] = 0
                    
                    base_df = base_df.fillna(0)

                    # Satır Sıralama (Toplam Güncel Satışa Göre)
                    toplam_row = base_df[base_df["Firma"] == "TOPLAM"]
                    main_rows = base_df[base_df["Firma"] != "TOPLAM"].sort_values("Toplam_G", ascending=False)
                    final_df = pd.concat([main_rows, toplam_row])
                    final_df.index = np.arange(1, len(final_df) + 1)

                    # Sütunları Mantıklı Sıraya Sokalım (Ürün Bazlı Gruplama)
                    # Firma | OTOGAZ (G, Ö, Y) | TÜPLÜ (G, Ö, Y) | DÖKME (G, Ö, Y) | TOPLAM (G, Ö, Y)
                    ordered_cols = ["Firma"] + \
                                   ["Otogaz_G", "Otogaz_Ö", "Otogaz_Y"] + \
                                   ["Tüplü_G", "Tüplü_Ö", "Tüplü_Y"] + \
                                   ["Dökme_G", "Dökme_Ö", "Dökme_Y"] + \
                                   ["Toplam_G", "Toplam_Ö", "Toplam_Y"]
                    
                    final_df = final_df[ordered_cols]
                    
                    # Okunaklı Başlıklar
                    final_df.columns = [
                        "Firma", 
                        "Otogaz (Güncel)", "Otogaz (Önceki Ay)", "Otogaz (Geçen Yıl)",
                        "Tüplü (Güncel)", "Tüplü (Önceki Ay)", "Tüplü (Geçen Yıl)",
                        "Dökme (Güncel)", "Dökme (Önceki Ay)", "Dökme (Geçen Yıl)",
                        "Toplam (Güncel)", "Toplam (Önceki Ay)", "Toplam (Geçen Yıl)"
                    ]

                    st.markdown(f"### {secilen_il_kiyas} Detaylı Satış Karşılaştırması (Ton)")
                    st.dataframe(final_df.style.format(precision=2), use_container_width=True, height=600)

        else:
            st.error("Güncel Word dosyası eksik.")

    # 7. HAM VERİ
    with tab_data:
        st.dataframe(df_filtered, use_container_width=True)

if __name__ == "__main__":
    main()
