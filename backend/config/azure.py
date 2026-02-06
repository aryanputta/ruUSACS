import os

# ============================================================
# AZURE CONFIGURATION
# ============================================================
# Set these environment variables before running the API:
#
# export AZURE_AD_B2C_TENANT_ID="your-tenant-id"
# export AZURE_AD_B2C_CLIENT_ID="your-client-id"
# export AZURE_AD_B2C_CLIENT_SECRET="your-client-secret"
# export AZURE_COMMUNICATION_CONNECTION_STRING="your-connection-string"
# export AZURE_NOTIFICATION_HUB_CONNECTION_STRING="your-hub-connection-string"
# export AZURE_NOTIFICATION_HUB_NAME="your-hub-name"
# export AZURE_MAPS_SUBSCRIPTION_KEY="your-maps-key"
# export AZURE_APP_INSIGHTS_CONNECTION_STRING="your-insights-connection-string"
# ============================================================

AZURE_AD_B2C_TENANT_ID = os.getenv("AZURE_AD_B2C_TENANT_ID")
AZURE_AD_B2C_CLIENT_ID = os.getenv("AZURE_AD_B2C_CLIENT_ID")
AZURE_AD_B2C_CLIENT_SECRET = os.getenv("AZURE_AD_B2C_CLIENT_SECRET")
AZURE_COMMUNICATION_CONNECTION_STRING = os.getenv("AZURE_COMMUNICATION_CONNECTION_STRING")
AZURE_NOTIFICATION_HUB_CONNECTION_STRING = os.getenv("AZURE_NOTIFICATION_HUB_CONNECTION_STRING")
AZURE_NOTIFICATION_HUB_NAME = os.getenv("AZURE_NOTIFICATION_HUB_NAME")
AZURE_MAPS_SUBSCRIPTION_KEY = os.getenv("AZURE_MAPS_SUBSCRIPTION_KEY")
AZURE_APP_INSIGHTS_CONNECTION_STRING = os.getenv("AZURE_APP_INSIGHTS_CONNECTION_STRING")


def get_communication_client():
    from azure.communication.identity import CommunicationIdentityClient
    if not AZURE_COMMUNICATION_CONNECTION_STRING:
        raise ValueError("AZURE_COMMUNICATION_CONNECTION_STRING not set")
    return CommunicationIdentityClient.from_connection_string(AZURE_COMMUNICATION_CONNECTION_STRING)


def get_maps_client():
    if not AZURE_MAPS_SUBSCRIPTION_KEY:
        raise ValueError("AZURE_MAPS_SUBSCRIPTION_KEY not set")
    return {"subscription_key": AZURE_MAPS_SUBSCRIPTION_KEY}
