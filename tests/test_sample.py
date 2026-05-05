from unittest.mock import MagicMock, patch

import boto3
import pandas as pd
import pytest
from moto import mock_aws

from sample_2.libs.storages import AwsS3
from sample_2.libs.utils import BEA_Wrapper, add

# ---------------------------------------------------------------------------
# utils.py
# ---------------------------------------------------------------------------


class TestAdd:
    def test_positive(self):
        assert add(2, 3) == 5

    def test_negative(self):
        assert add(-1, 1) == 0

    def test_zeros(self):
        assert add(0, 0) == 0

    def test_floats(self):
        assert add(1.5, 2.5) == pytest.approx(4.0)


class TestBEAWrapper:
    API_KEY = "test-key-123"

    def _mock_response(self, payload: dict) -> MagicMock:
        mock = MagicMock()
        mock.json.return_value = payload
        mock.raise_for_status.return_value = None
        return mock

    def test_list_datasets_returns_dataframe(self):
        payload = {
            "BEAAPI": {
                "Results": {
                    "Dataset": [
                        {"DatasetName": "NIPA", "DatasetDescription": "National Income"},
                        {"DatasetName": "GDPbyIndustry", "DatasetDescription": "GDP by Industry"},
                    ]
                }
            }
        }
        with patch("sample_2.libs.utils.requests.get", return_value=self._mock_response(payload)):
            bea = BEA_Wrapper(api_key=self.API_KEY)
            df = bea.list_datasets()

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "DatasetName" in df.columns

    def test_list_datasets_request_url(self):
        payload = {"BEAAPI": {"Results": {"Dataset": []}}}
        with patch(
            "sample_2.libs.utils.requests.get", return_value=self._mock_response(payload)
        ) as mock_get:
            BEA_Wrapper(api_key=self.API_KEY).list_datasets()

        called_url = mock_get.call_args[0][0]
        assert self.API_KEY in called_url
        assert "GETDATASETLIST" in called_url
        assert called_url.startswith("https://")

    def test_fetch_gdp_by_industry_returns_dataframe(self):
        payload = {
            "BEAAPI": {
                "Results": [
                    {
                        "Data": [
                            {"Year": "2023", "Industry": "11", "DataValue": "100.0"},
                            {"Year": "2023", "Industry": "21", "DataValue": "200.0"},
                        ]
                    }
                ]
            }
        }
        with patch("sample_2.libs.utils.requests.get", return_value=self._mock_response(payload)):
            df = BEA_Wrapper(api_key=self.API_KEY).fetch_gdp_by_industry(year="2023")

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "DataValue" in df.columns

    def test_fetch_gdp_url_has_no_html_entities(self):
        payload = {"BEAAPI": {"Results": [{"Data": []}]}}
        with patch(
            "sample_2.libs.utils.requests.get", return_value=self._mock_response(payload)
        ) as mock_get:
            BEA_Wrapper(api_key=self.API_KEY).fetch_gdp_by_industry(year="2023")

        called_url = mock_get.call_args[0][0]
        assert "&amp;" not in called_url, "URL must not contain HTML-encoded ampersands"


# ---------------------------------------------------------------------------
# storages.py
# ---------------------------------------------------------------------------


class TestAwsS3:
    BUCKET = "test-bucket-sample2"
    REGION = "us-east-1"

    @pytest.fixture(autouse=True)
    def aws_mock(self):
        with mock_aws():
            self.s3 = boto3.client("s3", region_name=self.REGION)
            yield

    def test_create_bucket(self):
        AwsS3.create_bucket(self.BUCKET)
        buckets = [b["Name"] for b in self.s3.list_buckets()["Buckets"]]
        assert self.BUCKET in buckets

    def test_create_bucket_idempotent(self):
        AwsS3.create_bucket(self.BUCKET)
        AwsS3.create_bucket(self.BUCKET)  # should not raise
        buckets = [b["Name"] for b in self.s3.list_buckets()["Buckets"]]
        assert buckets.count(self.BUCKET) == 1

    def test_list_buckets(self):
        self.s3.create_bucket(Bucket=self.BUCKET)
        result = AwsS3.list_buckets()
        assert self.BUCKET in result

    def test_copy_to_bucket_and_list(self, tmp_path):
        self.s3.create_bucket(Bucket=self.BUCKET)
        (tmp_path / "sample.csv").write_text("col1,col2\n1,2\n")
        AwsS3.copy_to_bucket(bucket=self.BUCKET, prefix="data/", local_dir=str(tmp_path))
        keys = AwsS3.list_bucket_files(bucket=self.BUCKET, prefix="data/")
        assert any("sample.csv" in k for k in keys)

    def test_delete_bucket_and_contents(self):
        self.s3.create_bucket(Bucket=self.BUCKET)
        self.s3.put_object(Bucket=self.BUCKET, Key="data/file.txt", Body=b"hello")
        AwsS3.delete_bucket_and_contents(self.BUCKET)
        buckets = [b["Name"] for b in self.s3.list_buckets()["Buckets"]]
        assert self.BUCKET not in buckets

    def test_delete_nonexistent_bucket_is_safe(self):
        AwsS3.delete_bucket_and_contents("bucket-that-does-not-exist")  # should not raise
