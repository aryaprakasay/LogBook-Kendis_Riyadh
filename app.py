import streamlit as st
import datetime
import pandas as pd

st.set_page_config(page_title="Fleet Log Book", page_icon="🚗", layout="centered")

# 1. Menangkap ID Mobil dari parameter URL (?mobil=MBL01)
query_params = st.query_params
id_mobil_terdeteksi = query_params.get("mobil", "MBL01")

# 2. Simulasi Data Internal (Nanti langkah berikutnya kita sambungkan ke Google Sheets asli)
if 'db_mobil' not in st.session_state:
    st.session_state.db_mobil = pd.DataFrame([
        {"ID_Mobil": "MBL01", "Nama": "Avanza Hitam (B 1234 ABC)", "Status": "Tersedia", "KM": 15200, "Driver": "-"},
        {"ID_Mobil": "MBL02", "Nama": "Innova Putih (B 5678 DEF)", "Status": "Tersedia", "KM": 42150, "Driver": "-"},
        {"ID_Mobil": "MBL03", "Nama": "Hilux PickUp (B 9999 XYZ)", "Status": "Tersedia", "KM": 85300, "Driver": "-"}
    ]).set_index("ID_Mobil")

if id_mobil_terdeteksi in st.session_state.db_mobil.index:
    mobil = st.session_state.db_mobil.loc[id_mobil_terdeteksi]
    
    st.title("🚗 Fleet Log Book Digital")
    st.subheader(f"Kendaraan Terdeteksi: {mobil['Nama']}")
    st.divider()

    # 3. Logika Form Check-Out & Check-In
    if mobil["Status"] == "Tersedia":
        st.success("✅ STATUS: KENDARAAN TERSEDIA DI POOL")
        
        with st.form("form_checkout"):
            st.write("### 📝 Form Mulai Penggunaan (Check-Out)")
            nama_driver = st.text_input("Nama Pengendara / Driver")
            tujuan = st.text_input("Tujuan Perjalanan")
            km_awal = st.number_input("Kilometer (KM) Awal", min_value=int(mobil["KM"]), value=int(mobil["KM"]), step=1)
            
            submit_out = st.form_submit_button("Mulai Perjalanan")
            
            if submit_out:
                if nama_driver and tujuan:
                    st.session_state.db_mobil.at[id_mobil_terdeteksi, "Status"] = "Dipakai"
                    st.session_state.db_mobil.at[id_mobil_terdeteksi, "Driver"] = nama_driver
                    st.session_state.db_mobil.at[id_mobil_terdeteksi, "KM"] = km_awal
                    st.success(f"Selamat bertugas {nama_driver}! Data Check-Out berhasil disimpan.")
                    st.rerun()
                else:
                    st.error("Semua kolom formulir wajib diisi!")

    elif mobil["Status"] == "Dipakai":
        st.warning(f"⚠️ STATUS: SEDANG DIPAKAI oleh {mobil['Driver']}")
        
        with st.form("form_checkin"):
            st.write("### 🔚 Form Selesai Penggunaan (Check-In)")
            km_akhir = st.number_input("Kilometer (KM) Akhir", min_value=int(mobil["KM"]), value=int(mobil["KM"])+1, step=1)
            
            submit_in = st.form_submit_button("Selesai Perjalanan")
            
            if submit_in:
                if km_akhir > mobil["KM"]:
                    jarak_tempuh = km_akhir - mobil["KM"]
                    st.session_state.db_mobil.at[id_mobil_terdeteksi, "Status"] = "Tersedia"
                    st.session_state.db_mobil.at[id_mobil_terdeteksi, "Driver"] = "-"
                    st.session_state.db_mobil.at[id_mobil_terdeteksi, "KM"] = km_akhir
                    st.balloons()
                    st.success(f"Mobil kembali ke pool! Total jarak tempuh: {jarak_tempuh} KM.")
                    st.rerun()
                else:
                    st.error(f"KM Akhir harus lebih besar dari KM Awal ({mobil['KM']} KM)!")
else:
    st.error("❌ ID Mobil tidak terdaftar di sistem armada. Periksa kembali QR Code Anda.")
