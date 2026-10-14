import streamlit as st
import pandas as pd

st.set_page_config(page_title="Fleet Log Book", page_icon="🚗", layout="centered")

# 1. PASTE LINK GOOGLE SHEETS ANDA DI SINI
# Ganti teks di bawah ini dengan tautan Google Sheets asli Anda (Biarkan berakhiran /edit?usp=sharing)
LINK_GOOGLE_SHEETS = "https://docs.google.com/spreadsheets/d/11cmcOt3RYH2XSd2H9KOsEZCbaR-Y-cCdtCj_V2D9S_c/edit?gid=0#gid=0"

try:
    # Mengambil ID unik Spreadsheet dari link yang Anda tempel
    sheet_id = LINK_GOOGLE_SHEETS.split("/d/")[1].split("/")[0]
    
    # Membuat link unduhan otomatis untuk Tab Status_Mobil (gid=0 adalah tab pertama)
    url_download_csv = f"https://google.com{sheet_id}/export?format=csv&gid=0"
    
    # Membaca data langsung dari Google Sheets menggunakan Pandas
    df_mobil = pd.read_csv(url_download_csv)
    df_mobil['ID_Mobil'] = df_mobil['ID_Mobil'].astype(str).str.strip()
    df_mobil = df_mobil.set_index("ID_Mobil")

    # 2. Menangkap ID Mobil dari parameter URL (?mobil=MBL01)
    query_params = st.query_params
    id_mobil_terdeteksi = query_params.get("mobil", "MBL01")

    st.title("🚗 Fleet Log Book Digital")

    if id_mobil_terdeteksi in df_mobil.index:
        mobil = df_mobil.loc[id_mobil_terdeteksi]
        st.subheader(f"Kendaraan Terdeteksi: {mobil['Nama_Kendaraan']} ({mobil['Plat_Nomor']})")
        st.divider()

        # Tampilkan Status Utama Kendaraan
        if mobil["Status"] == "Tersedia":
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
    st.info("Pastikan tautan Google Sheets Anda sudah benar dan aksesnya diatur ke 'Siapa saja yang memiliki link dapat melihat' (Public Viewer).")
