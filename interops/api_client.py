"""Compatibility exports for callers using the former API client location."""

from frontend.api_client import HireReadyApiClient, api_client

__all__ = ["HireReadyApiClient", "api_client"]
