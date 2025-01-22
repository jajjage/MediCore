# scripts/generate_keys.py

import base64
import os
from pathlib import Path


def generate_env_file():
    # Generate encryption key
    encryption_key = base64.urlsafe_b64encode(os.urandom(32)).decode()

    # Generate Django secret key
    django_secret = base64.b64encode(os.urandom(50)).decode()

    # Create .env file
    env_content = f"""
ENCRYPTION_KEY={encryption_key}
DJANGO_SECRET_KEY={django_secret}
DEBUG=1
ALLOWED_HOSTS=localhost,127.0.0.1,[::1]
"""

    # Write to .env file
    env_path = Path(__file__).parents[1] / ".env"
    with open(env_path, "w") as f:
        f.write(env_content.strip())

    print("Generated .env file with encryption keys and Django settings")


if __name__ == "__main__":
    generate_env_file()
