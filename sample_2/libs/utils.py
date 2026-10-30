import logging
from typing import Any

import pandas as pd
import requests

logger = logging.getLogger(__name__)


class BEAError(RuntimeError):
    """The BEA API answered, but with an error instead of data (bad key, bad parameter, ...)."""


def add(x: float, y: float) -> float:
    return x + y


class BEA_Wrapper:
    api_base = "https://apps.bea.gov/api/data"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def _get(self, method: str, **params: str) -> dict[str, Any]:
        """Call the BEA API and return the BEAAPI payload, raising BEAError on API-level errors.

        Parameters go through `params=` so requests URL-encodes them; a value like
        "2023&UserID=x" can't inject extra query parameters.
        """
        query = {"UserID": self.api_key, "method": method, "ResultFormat": "JSON", **params}
        response = requests.get(self.api_base, params=query, timeout=30)
        response.raise_for_status()
        payload: dict[str, Any] = response.json()["BEAAPI"]

        # BEA reports errors with HTTP 200 and an Error object, either at the top
        # level or under Results, instead of using HTTP status codes.
        results = payload.get("Results")
        error = payload.get("Error") or (
            results.get("Error") if isinstance(results, dict) else None
        )
        if error:
            detail = error.get("APIErrorDescription") or error.get("ErrorDetail") or error
            raise BEAError(f"BEA API error: {detail}")
        return payload

    def list_datasets(self) -> pd.DataFrame:
        """Return all available BEA datasets as a DataFrame."""
        payload = self._get("GETDATASETLIST")
        return pd.DataFrame(payload["Results"]["Dataset"])

    def fetch_gdp_by_industry(self, year: str = "2023") -> pd.DataFrame:
        """Return GDP by Industry data for the given year as a DataFrame."""
        payload = self._get(
            "GetData",
            DataSetName="GDPbyIndustry",
            Year=year,
            Industry="ALL",
            tableID="1",
            Frequency="A",
        )
        results = payload["Results"]
        # GDPbyIndustry returns a list of result tables; other datasets return a dict.
        table = results[0] if isinstance(results, list) else results
        return pd.DataFrame(table["Data"])
