import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ============================================================
# AZURE CONFIGURATION
# ============================================================
# Keys are loaded from .env file (never commit .env to git!)
# Copy .env.example to .env and fill in your real keys
# ============================================================

AZURE_COMMUNICATION_CONNECTION_STRING = os.getenv("AZURE_COMMUNICATION_CONNECTION_STRING")
AZURE_MAPS_SUBSCRIPTION_KEY = os.getenv("AZURE_MAPS_SUBSCRIPTION_KEY")


def get_communication_client():
    from azure.communication.identity import CommunicationIdentityClient
    if not AZURE_COMMUNICATION_CONNECTION_STRING:
        raise ValueError("AZURE_COMMUNICATION_CONNECTION_STRING not set in .env")
    return CommunicationIdentityClient.from_connection_string(AZURE_COMMUNICATION_CONNECTION_STRING)


def get_maps_client():
    if not AZURE_MAPS_SUBSCRIPTION_KEY:
        raise ValueError("AZURE_MAPS_SUBSCRIPTION_KEY not set in .env")
    return {"subscription_key": AZURE_MAPS_SUBSCRIPTION_KEY}
