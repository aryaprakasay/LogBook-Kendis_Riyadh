import streamlit as st
import datetime
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from zoneinfo import ZoneInfo

st.set_page_config(page_title="Fleet Log Book & Dashboard", page_icon="🚗", layout="wide")

# 1. Menghubungkan ke Google Sheets dengan hak akses tulis (Service Account)
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. Menangkap ID Mobil dari parameter URL (?mobil=MBL01)
query_params = st.query_params
id_mobil_terdeteksi = query_params.get("mobil", None)

try:
    # Membaca data status mobil secara real-time dari Google Sheets
    df_mobil = conn.read(worksheet="Status_Mobil", ttl="0s")
    df_mobil['ID_Mobil'] = df_mobil['ID_Mobil'].astype(str).str.strip()
    
    # ==============================================================================
    # 📊 HALAMAN DASBOR UTAMA ADMIN (Jika tidak ada mobil yang di-scan via URL/QR)
    # ==============================================================================
    if id_mobil_terdeteksi is None:
        st.title("📊 Fleet Monitor Dashboard")
        st.subheader("Ringkasan dan Status Real-Time Armada Kendaraan")
        st.divider()

        # --- A. LOGIKA HITUNG RINGKASAN DATA ---
        total_mobil = len(df_mobil)
        mobil_tersedia = len(df_mobil[df_mobil['Status'].str.strip() == 'Tersedia'])
        mobil_dipakai = len(df_mobil[df_mobil['Status'].str.strip() == 'Dipakai'])

        # --- B. TAMPILKAN METRIK RINGKASAN DI BAGIAN ATAS ---
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="🚌 Total Armada", value=total_mobil)
        with col2:
            st.metric(label="✅ Mobil Tersedia di Pool", value=mobil_tersedia)
        with col3:
            st.metric(label="⚠️ Mobil Sedang Digunakan", value=mobil_dipakai)

        st.divider()

        # --- C. FITUR FILTER STATUS ---
        st.write("### 🔍 Daftar Penggunaan & Status Kendaraan")
        filter_status = st.selectbox("Filter Tampilan Berdasarkan Status:", ["Semua Kendaraan", "Tersedia", "Dipakai"])
        
        # Salinan data untuk ditampilkan di tabel dashboard
        df_display = df_mobil.copy()
        
        # Ambil data tujuan dari Log_Aktivitas untuk mobil yang sedang dipakai
        try:
            df_log = conn.read(worksheet="Log_Aktivitas", ttl="0s")
            # Cari log yang KM_Akhir-nya masih kosong (artinya sedang jalan)
            df_active_logs = df_log[df_log['KM_Akhir'].isna() | (df_log['KM_Akhir'] == "") | (df_log['KM_Akhir'] == "-")]
            df_active_logs = df_active_logs.drop_duplicates(subset=['ID_Mobil'], keep='last')
            
            # Hubungkan data tujuan ke tabel display dashboard
            tujuan_map = dict(zip(df_active_logs['ID_Mobil'].astype(str).str.strip(), df_active_logs['Tujuan']))
            df_display['Tujuan_Perjalanan'] = df_display['ID_Mobil'].map(tujuan_map).fillna("-")
        except:
            df_display['Tujuan_Perjalanan'] = "-"

        # Pengaturan kolom yang mau ditampilkan di tabel dashboard agar rapi
        df_display = df_display[['ID_Mobil', 'Nama_Kendaraan', 'Plat_Nomor', 'Status', 'Driver_Sekarang', 'Tujuan_Perjalanan', 'KM_Terakhir']]

        # Jalankan filter berdasarkan pilihan admin
        if filter_status != "Semua Kendaraan":
            df_display = df_display[df_display['Status'].str.strip() == filter_status]

        # --- D. TAMPILKAN TABEL MONITOR UTAMA ---
        st.dataframe(
            df_display, 
            hide_index=True, 
            use_container_width=True,
            column_config={
                "ID_Mobil": "ID",
                "Nama_Kendaraan": "Nama Kendaraan",
                "Plat_Nomor": "Plat Nomor",
                "Status": "Status Terkini",
                "Driver_Sekarang": "Supir Sekarang",
                "Tujuan_Perjalanan": "Tujuan Perjalanan",
                "KM_Terakhir": "KM Terakhir"
            }
        )
        
        if st.button("🔄 Segarkan Data (Refresh)"):
            st.rerun()

    # ==============================================================================
    # 📱 HALAMAN LOG BOOK DRIVER (Jika mendeteksi kode mobil dari QR Code / URL)
    # ==============================================================================
    else:
        df_mobil_form = df_mobil.set_index("ID_Mobil")
        
        if id_mobil_terdeteksi in df_mobil_form.index:
            mobil = df_mobil_form.loc[id_mobil_terdeteksi]
            st.title("🚗 Fleet Log Book Digital")
            st.subheader(f"Kendaraan Terdeteksi: {mobil['Nama_Kendaraan']} ({mobil['Plat_Nomor']})")
            st.divider()

            # --- LOGIKA FORM CHECK-OUT ---
            if str(mobil["Status"]).strip() == "Tersedia":
                st.success("✅ STATUS: KENDARAAN TERSEDIA DI POOL")
                with st.form("form_checkout"):
                    st.write("### 📝 Form Mulai Penggunaan (Check-Out)")
                    nama_driver = st.text_input("Nama Pengendara / Driver")
                    tujuan = st.text_input("Tujuan Perjalanan")
                    km_awal = st.number_input("Kilometer (KM) Awal", min_value=0, value=int(mobil["KM_Terakhir"]), step=1)
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
                            st.success(f"Berhasil! Data Check-Out disimpan.")
                            st.rerun()
                        else:
                            st.error("Semua kolom formulir wajib diisi!")

            # --- LOGIKA FORM CHECK-IN ---
            else:
                st.warning(f"⚠️ STATUS: SEDANG DIPAKAI oleh {mobil['Driver_Sekarang']}")
                with st.form("form_checkin"):
                    st.write("### 🔚 Form Selesai Penggunaan (Check-In)")
                    km_akhir = st.number_input("Kilometer (KM) Akhir", min_value=0, value=int(mobil["KM_Terakhir"])+1, step=1)
                    waktu_selesai = datetime.datetime.now(ZoneInfo("Asia/Riyadh")).strftime("%Y-%m-%d %H:%M:%S")
                    
                    submit_in = st.form_submit_button("Simpan & Selesai Perjalanan")
                    if submit_in:
                        if km_akhir >= mobil["KM_Terakhir"]:
                            jarak_tempuh = km_akhir - mobil["KM_Terakhir"]
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
                            st.success(f"Berhasil! Data Check-In disimpan.")
                            st.rerun()
                        else:
                            st.error(f"KM Akhir tidak boleh lebih kecil dari KM Awal ({mobil['KM_Terakhir']} KM)!")
        else:
            st.error(f"❌ ID Mobil '{id_mobil_terdeteksi}' tidak ditemukan di database.")
            
except Exception as e:
    st.error(f"Terjadi kesalahan sistem: {e}")
