from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

# Define the SSH directory
ssh_dir = Path.home() / ".ssh"

# Ensure the directory exists
ssh_dir.mkdir(parents=True, exist_ok=True)

# Generate private key
private_key = ed25519.Ed25519PrivateKey.generate()

# Serialize private key
private_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
)

# Generate public key
public_key = private_key.public_key()

# Serialize public key
public_pem = public_key.public_bytes(
    encoding=serialization.Encoding.OpenSSH, format=serialization.PublicFormat.OpenSSH
)

# Add comment to the public key
email_comment = "mustphajajjage@gmail.com"
public_pem_with_comment = public_pem.decode("utf-8").strip() + f" {email_comment}"

# Save private key to ~/.ssh/id_ed25519
private_key_path = ssh_dir / "id_ed25519"
with private_key_path.open("wb") as private_file:
    private_file.write(private_pem)

# Set correct permissions for the private key
private_key_path.chmod(0o600)

# Save public key to ~/.ssh/id_ed25519.pub
public_key_path = ssh_dir / "id_ed25519.pub"
with public_key_path.open("w") as public_file:
    public_file.write(public_pem_with_comment)

print(f"ED25519 SSH keys generated and saved to {ssh_dir}.")  # noqa: T201
