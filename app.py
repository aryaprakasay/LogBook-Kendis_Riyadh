import streamlit as st
import datetime
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from zoneinfo import ZoneInfo

# 1. Mengatur konfigurasi awal halaman agar mendukung tampilan lebar
st.set_page_config(page_title="Log Book Kendis KBRI Riyadh", page_icon="🚗", layout="wide")

# 2. Menghubungkan ke Google Sheets dengan hak akses tulis (Service Account)
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. Menangkap ID Mobil dari parameter URL (?mobil=MBL01)
query_params = st.query_params
id_mobil_terdeteksi = query_params.get("mobil", None)

try:
    # Membaca data status mobil secara real-time dari Google Sheets
    df_mobil = conn.read(worksheet="Status_Mobil", ttl="0s")
    df_mobil['ID_Mobil'] = df_mobil['ID_Mobil'].astype(str).str.strip()

    # ==============================================================================
    # 📊 HALAMAN DASBOR UTAMA ADMIN (Jika link utama diakses tanpa ?mobil=...)
    # ==============================================================================
    if id_mobil_terdeteksi is None:
        st.title("📊 Fleet Monitor Dashboard")
        st.subheader("Ringkasan dan Status Real-Time Kendis KBRI Riyadh")
        st.divider()

        # --- A. LOGIKA HITUNG RINGKASAN DATA ---
        total_mobil = len(df_mobil)
        mobil_tersedia = len(df_mobil[df_mobil['Status'].str.strip() == 'Tersedia'])
        mobil_dipakai = len(df_mobil[df_mobil['Status'].str.strip() == 'Dipakai'])

        # --- B. TAMPILKAN METRIK RINGKASAN DI BAGIAN ATAS ---
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="🚌 Total Armada Kendis", value=total_mobil)
        with col2:
            st.metric(label="✅ Tersedia di Pool KBRI", value=mobil_tersedia)
        with col3:
            st.metric(label="⚠️ Sedang Digunakan/Dinas", value=mobil_dipakai)

        st.divider()

        # --- C. FITUR FILTER STATUS ---
        st.write("### 🔍 Daftar Penggunaan & Status Kendaraan")
        filter_status = st.selectbox("Filter Tampilan Berdasarkan Status:", ["Semua Kendaraan", "Tersedia", "Dipakai"])
        
        # Salinan data untuk dimodifikasi sebelum ditampilkan
        df_display = df_mobil.copy()
        
        # Mengambil informasi tujuan dari Tab Log_Aktivitas secara real-time
        try:
            df_log = conn.read(worksheet="Log_Aktivitas", ttl="0s")
            df_active_logs = df_log[df_log['KM_Akhir'].isna() | (df_log['KM_Akhir'] == "") | (df_log['KM_Akhir'] == "-")]
            df_active_logs = df_active_logs.drop_duplicates(subset=['ID_Mobil'], keep='last')
            
            tujuan_map = dict(zip(df_active_logs['ID_Mobil'].astype(str).str.strip(), df_active_logs['Tujuan']))
            df_display['Tujuan_Perjalanan'] = df_display['ID_Mobil'].map(tujuan_map).fillna("-")
        except:
            df_display['Tujuan_Perjalanan'] = "-"

        # Memilih kolom-kolom yang mau ditampilkan (Kolom ID_Mobil Sengaja DIHAPUS dari list ini)
        df_display = df_display[['Nama_Kendaraan', 'Plat_Nomor', 'Status', 'Driver_Sekarang', 'Tujuan_Perjalanan', 'KM_Terakhir']]
        df_display.columns = ["Nama Kendaraan", "Plat Nomor", "Status Terkini", "Supir Sekarang", "Tujuan Perjalanan", "KM Terakhir"]

        # 🔧 SOLUSI POIN 2: Memaksa KM Terakhir menjadi angka bulat bulat (menghilangkan desimal/koma)
        df_display["KM Terakhir"] = pd.to_numeric(df_display["KM Terakhir"], errors='coerce').fillna(0).astype(int)

        # Menjalankan filter berdasarkan pilihan box admin
        if filter_status != "Semua Kendaraan":
            df_display = df_display[df_display['Status Terkini'].str.strip() == filter_status]

        # --- D. TAMPILKAN TABEL UTAMA TANPA SCROLL & TANPA INDEKS ID ---
        # 🔧 SOLUSI POIN 1: Menggunakan pandas styler .hide() untuk menyembunyikan kolom angka indeks bawaan
        st.write(df_display.style.hide(axis="index").to_html(), unsafe_allow_html=True)
        st.write("") # Memberi jarak spasial bawah
        
        if st.button("🔄 Segarkan Data Dashboard"):
            st.rerun()

    # ==============================================================================
    # 📱 HALAMAN LOG BOOK DRIVER (Jika mendeteksi kode mobil dari QR Code / URL)
    # ==============================================================================
    else:
        df_mobil_form = df_mobil.set_index("ID_Mobil")
        
        if id_mobil_terdeteksi in df_mobil_form.index:
            mobil = df_mobil_form.loc[id_mobil_terdeteksi]
            
            # Agar form pengisian supir di HP terlihat rapi di tengah layar (tidak terlalu melar ke samping)
            _, center_col, _ = st.columns()
            with center_col:
                st.title("🚗 Log Book Kendis KBRI Riyadh")
                st.subheader(f"Kendaraan Terdeteksi: {mobil['Nama_Kendaraan']} ({mobil['Plat_Nomor']})")
                st.divider()

                # --- 3. LOGIKA FORM CHECK-OUT (MULAI PERJALANAN) ---
                if str(mobil["Status"]).strip() == "Tersedia":
                    st.success("✅ STATUS: KENDARAAN TERSEDIA DI KBRI")
                    
                    with st.form("form_checkout"):
                        st.write("### 📝 Form Mulai Penggunaan (Check-Out)")
                        nama_driver = st.text_input("Nama Pengendara / Driver")
                        tujuan = st.text_input("Tujuan Perjalanan")
                        km_awal = st.number_input("Kilometer (KM) Awal", min_value=0, value=int(pd.to_numeric(mobil['KM_Terakhir'], errors='coerce').fillna(0)), step=1)
                        waktu_mulai = datetime.datetime.now(ZoneInfo("Asia/Riyadh")).strftime("%Y-%m-%d %H:%M:%S")
                        
                        submit_out = st.form_submit_button("Simpan & Mulai Perjalanan")
                        
                        if submit_out:
                            if nama_driver and tujuan:
                                df_log = conn.read(worksheet="Log_Aktivitas", ttl="0s")
                                new_log = pd.DataFrame([{
                                    "Timestamp": waktu_mulai, "ID_Mobil": id_mobil_terdeteksi, "Nama_Driver": nama_driver,
                                    "Tujuan": tujuan, "KM_Awal": int(km_awal), "Waktu_Mulai": waktu_mulai,
                                    "KM_Akhir": None, "Waktu_Selesai": "", "Total_Jarak": None
                                }])
                                df_log_updated = pd.concat([df_log, new_log], ignore_index=True)
                                conn.update(worksheet="Log_Aktivitas", data=df_log_updated)
                                
                                df_mobil_reset = df_mobil_form.reset_index()
                                df_mobil_reset.loc[df_mobil_reset['ID_Mobil'] == id_mobil_terdeteksi, ['Status', 'Driver_Sekarang', 'KM_Terakhir']] = ["Dipakai", nama_driver, int(km_awal)]
                                conn.update(worksheet="Status_Mobil", data=df_mobil_reset)
                                
                                st.success(f"Berhasil! Data Check-Out disimpan ke Google Sheets (Waktu KSA).")
                                st.rerun()
                            else:
                                st.error("Semua kolom formulir wajib diisi!")

                # --- 4. LOGIKA FORM CHECK-IN (SELESAI PERJALANAN) ---
                else:
                    st.warning(f"⚠️ STATUS: SEDANG DIPAKAI oleh {mobil['Driver_Sekarang']}")
                    
                    with st.form("form_checkin"):
                        st.write("### 🔚 Form Selesai Penggunaan (Check-In)")
                        km_akhir = st.number_input("Kilometer (KM) Akhir", min_value=0, value=int(pd.to_numeric(mobil['KM_Terakhir'], errors='coerce').fillna(0))+1, step=1)
                        waktu_selesai = datetime.datetime.now(ZoneInfo("Asia/Riyadh")).strftime("%Y-%m-%d %H:%M:%S")
                        
                        submit_in = st.form_submit_button("Simpan & Selesai Perjalanan")
                        
                        if submit_in:
                            km_terakhir_val = int(pd.to_numeric(mobil['KM_Terakhir'], errors='coerce').fillna(0))
                            if km_akhir >= km_terakhir_val:
                                jarak_tempuh = km_akhir - km_terakhir_val
                                df_log = conn.read(worksheet="Log_Aktivitas", ttl="0s")
                                idx = df_log[(df_log['ID_Mobil'] == id_mobil_terdeteksi) & (df_log['KM_Akhir'].isna() | (df_log['KM_Akhir'] == "") | (df_log['KM_Akhir'] == "-"))].index
                                
                                if not idx.empty:
                                    df_log = df_log.astype(object)
                                    df_log.loc[idx, 'KM_Akhir'] = int(km_akhir)
                                    df_log.loc[idx, 'Waktu_Selesai'] = waktu_selesai
                                    df_log.loc[idx, 'Total_Jarak'] = int(jarak_tempuh)
                                    conn.update(worksheet="Log_Aktivitas", data=df_log)
                                
                                df_mobil_reset = df_mobil_form.reset_index()
                                df_mobil_reset.loc[df_mobil_reset['ID_Mobil'] == id_mobil_terdeteksi, ['Status', 'Driver_Sekarang', 'KM_Terakhir']] = ["Tersedia", "-", int(km_akhir)]
                                conn.update(worksheet="Status_Mobil", data=df_mobil_reset)
                                
                                st.balloons()
                                st.success(f"Berhasil! Data Check-In disimpan ke Google Sheets (Waktu KSA).")
                                st.rerun()
                            else:
                                st.error(f"KM Akhir tidak boleh lebih kecil dari KM Awal ({km_terakhir_val} KM)!")
        else:
