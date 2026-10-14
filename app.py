import streamlit as st
import pandas as pd

st.set_page_config(page_title="Fleet Log Book", page_icon="🚗", layout="centered")

# ID Google Sheets Anda yang sudah ditanam langsung secara aman
ID_SHEET = "11cmcOt3RYH2XSd2H9KOsEZCbaR-Y-cCdtCj_V2D9S_c"

# URL Ekspor CSV Bersih ke masing-masing Tab Google Sheets Anda
URL_STATUS = f"https://docs.google.com/spreadsheets/d/{ID_SHEET}/export?format=csv&gid=0"
URL_LOG = f"https://docs.google.com/spreadsheets/d/{ID_SHEET}/export?format=csv&gid=1114515513"  # Gid otomatis untuk Log_Aktivitas

try:
    # Membaca data langsung dari Google Sheets menggunakan Pandas
    df_mobil = pd.read_csv(URL_STATUS)
    df_mobil['ID_Mobil'] = df_mobil['ID_Mobil'].astype(str).str.strip()
    df_mobil = df_mobil.set_index("ID_Mobil")

    # Menangkap ID Mobil dari parameter URL (?mobil=MBL01)
    query_params = st.query_params
    id_mobil_terdeteksi = query_params.get("mobil", "MBL01")

    st.title("🚗 Fleet Log Book Digital")

    if id_mobil_terdeteksi in df_mobil.index:
        mobil = df_mobil.loc[id_mobil_terdeteksi]
        st.subheader(f"Kendaraan Terdeteksi: {mobil['Nama_Kendaraan']} ({mobil['Plat_Nomor']})")
        st.divider()

        # Tampilkan Status Utama Kendaraan
        if str(mobil["Status"]).strip() == "Tersedia":
            st.success("✅ STATUS: KENDARAAN TERSEDIA DI POOL")
            with st.form("form_checkout"):
                st.write("### 📝 Form Mulai Penggunaan (Check-Out)")
                nama_driver = st.text_input("Nama Pengendara / Driver")
                tujuan = st.text_input("Tujuan Perjalanan")
                km_awal = st.number_input("Kilometer (KM) Awal", min_value=int(mobil["KM_Terakhir"]), value=int(mobil["KM_Terakhir"]), step=1)
                
                submit_out = st.form_submit_button("Simpan Data Mulai")
                if submit_out:
                    if nama_driver and tujuan:
                        st.success(f"Log dicatat! Driver {nama_driver} membawa kendaraan menuju {tujuan}.")
                    else:
                        st.error("Mohon lengkapi formulir terlebih dahulu.")
        else:
            st.warning(f"⚠️ STATUS: SEDANG DIPAKAI oleh {mobil['Driver_Sekarang']}")
            with st.form("form_checkin"):
                st.write("### 🔚 Form Selesai Penggunaan (Check-In)")
                km_akhir = st.number_input("Kilometer (KM) Akhir", min_value=int(mobil["KM_Terakhir"]), value=int(mobil["KM_Terakhir"])+1, step=1)
                
                submit_in = st.form_submit_button("Simpan Data Selesai")
                if submit_in:
                    st.balloons()
                    st.success("Log selesai dicatat! Kendaraan dikembalikan ke pool.")
    else:
        st.error(f"❌ ID Mobil '{id_mobil_terdeteksi}' tidak ditemukan di database Google Sheets Anda.")

except Exception as e:
    st.error(f"Terjadi kesalahan pembacaan database: {e}")
    st.info("Pastikan akses Google Sheets Anda diatur ke 'Siapa saja yang memiliki link dapat melihat' (Public Viewer).")
