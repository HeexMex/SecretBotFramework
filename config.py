import os
from dotenv import load_dotenv

load_dotenv()

HOMESERVER_URL = os.getenv("HOMESERVER_URL", "")
HOMESERVER_DOMAIN = os.getenv("HOMESERVER_DOMAIN", "")

BOT_USERNAME = os.getenv("BOT_USERNAME", "mybot")
BOT_PASSWORD = os.getenv("BOT_PASSWORD", "CHANGE_ME_STRONG_PASSWORD")
BOT_DISPLAY_NAME = os.getenv("BOT_DISPLAY_NAME", "Matrix Bot")
BOT_USER_ID = f"@{BOT_USERNAME}:{HOMESERVER_DOMAIN}"

# SSH config for remote registration
SSH_HOST = os.getenv("SSH_HOST", "")
SSH_USER = os.getenv("SSH_USER", "root")
SSH_PORT = int(os.getenv("SSH_PORT", "22"))
SSH_PASSWORD = os.getenv("SSH_PASSWORD", "")
SSH_KEY = os.getenv("SSH_KEY", "")

SYNAPSE_CONTAINER = os.getenv("SYNAPSE_CONTAINER", "synapse")
MATRIX_REMOTE_DIR = os.getenv("MATRIX_REMOTE_DIR", "/root/matrix")

REGISTRATION_SHARED_SECRET = os.getenv("REGISTRATION_SHARED_SECRET", "")

CREDENTIALS_FILE = "credentials.json"
STORE_PATH = "./nio_store/"
