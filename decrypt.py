# decrypt.py
from cryptography.fernet import Fernet
import os

# Load the key
with open("simulation_key.key", "rb") as f:
    key = f.read()
cipher = Fernet(key)

# Ask for the folder containing .encrypted files
folder = input("Enter the full folder path (e.g., C:\\Users\\amaan\\Desktop\\my_precious_files): ")

# Walk through all files
for root, dirs, files in os.walk(folder):
    for file in files:
        if file.endswith(".encrypted"):
            enc_path = os.path.join(root, file)
            # Read encrypted data
            with open(enc_path, "rb") as f:
                encrypted_data = f.read()
            # Decrypt
            decrypted_data = cipher.decrypt(encrypted_data)
            # Original path = remove .encrypted
            original_path = enc_path[:-10]  # removes the last 10 characters (.encrypted)
            # Write decrypted content
            with open(original_path, "wb") as f:
                f.write(decrypted_data)
            # Optional: delete the .encrypted file
            # os.remove(enc_path)
            print(f"✅ Unlocked: {file} -> {os.path.basename(original_path)}")

print("Done! Your files are now decrypted.")