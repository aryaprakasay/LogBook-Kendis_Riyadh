import streamlit as st
import datetime
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Fleet Log Book", page_icon="🚗", layout="centered")

# 1. Menghubungkan ke Google Sheets dengan hak akses tulis (Service Account)
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. Menangkap ID Mobil dari parameter URL (?mobil=MBL01)
query_params = st.query_params
id_mobil_terdeteksi = query_params.get("mobil", "MBL01")

st.title("🚗 Fleet Log Book Digital")

try:
    # Membaca data status mobil secara real-time dari Google Sheets
    df_mobil = conn.read(worksheet="Status_Mobil", ttl="0s")
    df_mobil['ID_Mobil'] = df_mobil['ID_Mobil'].astype(str).str.strip()
    df_mobil = df_mobil.set_index("ID_Mobil")

    if id_mobil_terdeteksi in df_mobil.index:
        mobil = df_mobil.loc[id_mobil_terdeteksi]
        st.subheader(f"Kendaraan Terdeteksi: {mobil['Nama_Kendaraan']} ({mobil['Plat_Nomor']})")
        st.divider()

        # 3. LOGIKA FORM CHECK-OUT (MULAI PERJALANAN)
        if str(mobil["Status"]).strip() == "Tersedia":
            st.success("✅ STATUS: KENDARAAN TERSEDIA DI POOL")
            
            with st.form("form_checkout"):
                st.write("### 📝 Form Mulai Penggunaan (Check-Out)")
                nama_driver = st.text_input("Nama Pengendara / Driver")
                tujuan = st.text_input("Tujuan Perjalanan")
                km_awal = st.number_input("Kilometer (KM) Awal", min_value=int(mobil["KM_Terakhir"]), value=int(mobil["KM_Terakhir"]), step=1)
                waktu_mulai = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                submit_out = st.form_submit_button("Simpan & Mulai Perjalanan")
                
                if submit_out:
                    if nama_driver and tujuan:
                        # Tambah baris baru ke Tab Log_Aktivitas
                        df_log = conn.read(worksheet="Log_Aktivitas", ttl="0s")
                        new_log = pd.DataFrame([{
                            "Timestamp": waktu_mulai, "ID_Mobil": id_mobil_terdeteksi, "Nama_Driver": nama_driver,
                            "Tujuan": tujuan, "KM_Awal": int(km_awal), "Waktu_Mulai": waktu_mulai,
                            "KM_Akhir": "", "Waktu_Selesai": "", "Total_Jarak": ""
                        }])
                        
                        # Menyamakan tipe data kolom agar tidak bentrok
                        df_log['KM_Akhir'] = df_log['KM_Akhir'].astype(str)
                        df_log_updated = pd.concat([df_log, new_log], ignore_index=True)
                        conn.update(worksheet="Log_Aktivitas", data=df_log_updated)
                        
                        # Ubah status mobil di Tab Status_Mobil menjadi "Dipakai"
                        df_mobil_reset = df_mobil.reset_index()
                        df_mobil_reset.loc[df_mobil_reset['ID_Mobil'] == id_mobil_terdeteksi, ['Status', 'Driver_Sekarang', 'KM_Terakhir']] = ["Dipakai", nama_driver, int(km_awal)]
                        conn.update(worksheet="Status_Mobil", data=df_mobil_reset)
                        
                        st.success(f"Berhasil! Selamat bertugas {nama_driver}. Data disimpan ke Google Sheets.")
                        st.rerun()
                    else:
                        st.error("Semua kolom formulir wajib diisi!")

        # 4. LOGIKA FORM CHECK-IN (SELESAI PERJALANAN)
        else:
            st.warning(f"⚠️ STATUS: SEDANG DIPAKAI oleh {mobil['Driver_Sekarang']}")
            
            with st.form("form_checkin"):
                st.write("### 🔚 Form Selesai Penggunaan (Check-In)")
                km_akhir = st.number_input("Kilometer (KM) Akhir", min_value=int(mobil["KM_Terakhir"]), value=int(mobil["KM_Terakhir"])+1, step=1)
                waktu_selesai = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                submit_in = st.form_submit_button("Simpan & Selesai Perjalanan")
                
                if submit_in:
                    if km_akhir >= mobil["KM_Terakhir"]:
                        jarak_tempuh = km_akhir - mobil["KM_Terakhir"]
                        
                        # Cari baris aktif di Log_Aktivitas
                        df_log = conn.read(worksheet="Log_Aktivitas", ttl="0s")
                        df_log['KM_Akhir'] = df_log['KM_Akhir'].fillna("").astype(str).str.strip()
                        
                        idx = df_log[(df_log['ID_Mobil'] == id_mobil_terdeteksi) & ((df_log['KM_Akhir'] == "") | (df_log['KM_Akhir'] == "-"))].index
                        
                        if not idx.empty:
                            df_log.loc[idx, ['KM_Akhir', 'Waktu_Selesai', 'Total_Jarak']] = [str(int(km_akhir)), waktu_selesai, str(int(jarak_tempuh))]
                            conn.update(worksheet="Log_Aktivitas", data=df_log)
                        
                        # Kembalikan status mobil di Tab Status_Mobil menjadi "Tersedia"
                        df_mobil_reset = df_mobil.reset_index()
                        df_mobil_reset.loc[df_mobil_reset['ID_Mobil'] == id_mobil_terdeteksi, ['Status', 'Driver_Sekarang', 'KM_Terakhir']] = ["Tersedia", "-", int(km_akhir)]
                        conn.update(worksheet="Status_Mobil", data=df_mobil_reset)
                        
                        st.balloons()
                        st.success(f"Berhasil! Mobil kembali ke pool. Total jarak tempuh: {jarak_tempuh} KM.")
                        st.rerun()
                    else:
                        st.error(f"KM Akhir tidak boleh lebih kecil dari KM Awal ({mobil['KM_Terakhir']} KM)!")
    else:
        st.error(f"❌ ID Mobil '{id_mobil_terdeteksi}' tidak ditemukan di database Google Sheets.")
except Exception as e:
    st.error(f"Terjadi kesalahan otorisasi tulis: {e}")
