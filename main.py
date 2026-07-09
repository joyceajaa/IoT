import os
import webbrowser

def main_menu():
    while True:
        print("\n=== Sistem Deteksi Wajah & Gerakan ===")
        print("1. Daftarkan wajah baru")
        print("2. Jalankan deteksi")
        print("3. Buka tampilan web")
        print("4. Keluar")
        choice = input("Pilih menu (1/2/3/4): ").strip()

        if choice == "1":
            os.system("python register_face.py")
        elif choice == "2":
            os.system("python detection.py")
        elif choice == "3":
            print("[INFO] Membuka dashboard web...")
            os.system("python app.py")
            webbrowser.open("http://127.0.0.1:5000")
        elif choice == "4":
            print("Keluar dari program.")
            break
        else:
            print("Pilihan tidak valid. Coba lagi.")

if __name__ == "__main__":
    main_menu()
