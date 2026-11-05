"""Compatibility exports for callers using the former API client location."""

import requests

from frontend.api_client import BackendApiError, HireReadyApiClient, api_client

__all__ = ["BackendApiError", "HireReadyApiClient", "api_client"]
