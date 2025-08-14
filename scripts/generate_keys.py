"""
Generates RSA private and public keys for JWT signing.
"""
import os
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

# Define paths
storage_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'storage')
keys_path = os.path.join(storage_path, 'keys')
private_key_path = os.path.join(keys_path, 'private_key.pem')
public_key_path = os.path.join(keys_path, 'public_key.pem')

# Create directories if they don't exist
os.makedirs(keys_path, exist_ok=True)

# Generate private key
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
    backend=default_backend()
)

# Serialize and save private key
with open(private_key_path, 'wb') as f:
    f.write(private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ))
print(f"Private key saved to: {private_key_path}")

# Generate and save public key
public_key = private_key.public_key()
with open(public_key_path, 'wb') as f:
    f.write(public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ))
print(f"Public key saved to: {public_key_path}")