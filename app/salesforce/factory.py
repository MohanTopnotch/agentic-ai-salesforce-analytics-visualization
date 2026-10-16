"""Construct the configured Salesforce client."""

import os

from app.mock_salesforce_client import MockSalesforceClient
from app.salesforce.client import SalesforceClient
from app.salesforce.rest_client import SalesforceRESTClient


def create_salesforce_client() -> SalesforceClient:
    """Select a mock or live client from backend environment configuration."""
    mode = os.getenv("SALESFORCE_MODE", "mock").strip().lower()
    if mode == "mock":
        return MockSalesforceClient()
    if mode != "live":
        raise ValueError("SALESFORCE_MODE must be either 'mock' or 'live'.")

    client_id = os.getenv("SALESFORCE_CLIENT_ID", "").strip()
    client_secret = os.getenv("SALESFORCE_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        raise RuntimeError(
            "Live Salesforce mode requires SALESFORCE_CLIENT_ID and "
            "SALESFORCE_CLIENT_SECRET."
        )

    return SalesforceRESTClient(
        client_id=client_id,
        client_secret=client_secret,
        login_url=os.getenv(
            "SALESFORCE_LOGIN_URL",
            "https://login.salesforce.com",
        ).strip(),
        api_version=os.getenv("SALESFORCE_API_VERSION", "v66.0").strip(),
    )
