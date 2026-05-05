import logging

import pandas as pd
import requests

logger = logging.getLogger(__name__)


def add(x: float, y: float) -> float:
    return x + y


class BEA_Wrapper:
    api_base = "https://apps.bea.gov/api/data"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def list_datasets(self) -> pd.DataFrame:
        """Return all available BEA datasets as a DataFrame."""
        url = (
            f"{self.api_base}"
            f"?UserID={self.api_key}"
            f"&method=GETDATASETLIST"
            f"&ResultFormat=JSON"
        )
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        return pd.DataFrame(data["BEAAPI"]["Results"]["Dataset"])

    def fetch_gdp_by_industry(self, year: str = "2023") -> pd.DataFrame:
        """Return GDP by Industry data for the given year as a DataFrame."""
        url = (
            f"{self.api_base}"
            f"?UserID={self.api_key}"
            f"&method=GetData"
            f"&DataSetName=GDPbyIndustry"
            f"&Year={year}"
            f"&Industry=ALL"
            f"&tableID=1"
            f"&Frequency=A"
            f"&ResultFormat=JSON"
        )
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        rows = data["BEAAPI"]["Results"][0]["Data"]
        return pd.DataFrame(rows)
