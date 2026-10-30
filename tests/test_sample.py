from unittest.mock import MagicMock, patch

import boto3
import pandas as pd
import pytest
import requests
from botocore.exceptions import ClientError, NoCredentialsError
from moto import mock_aws

from sample_2.libs.storages import AwsS3
from sample_2.libs.utils import BEA_Wrapper, BEAError, add
from sample_2.main import main

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

    def test_list_datasets_request(self):
        payload = {"BEAAPI": {"Results": {"Dataset": []}}}
        with patch(
            "sample_2.libs.utils.requests.get", return_value=self._mock_response(payload)
        ) as mock_get:
            BEA_Wrapper(api_key=self.API_KEY).list_datasets()

        called_url = mock_get.call_args[0][0]
        params = mock_get.call_args.kwargs["params"]
        assert called_url.startswith("https://")
        assert params["UserID"] == self.API_KEY
        assert params["method"] == "GETDATASETLIST"

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

    def test_year_cannot_inject_query_params(self):
        """Values are URL-encoded by requests, so '&' in --year stays inside the Year value."""
        req = requests.Request(
            "GET", BEA_Wrapper.api_base, params={"Year": "2023&UserID=attacker"}
        ).prepare()
        assert req.url is not None
        assert "UserID=attacker" not in req.url
        assert "Year=2023%26UserID%3Dattacker" in req.url

    def test_fetch_gdp_accepts_dict_results(self):
        payload = {"BEAAPI": {"Results": {"Data": [{"DataValue": "1"}]}}}
        with patch("sample_2.libs.utils.requests.get", return_value=self._mock_response(payload)):
            df = BEA_Wrapper(api_key=self.API_KEY).fetch_gdp_by_industry()
        assert len(df) == 1

    @pytest.mark.parametrize(
        "payload",
        [
            # Real shape returned for an invalid key (HTTP 200, error under Results)
            {"BEAAPI": {"Results": {"Error": {"APIErrorDescription": "Invalid API UserId."}}}},
            {"BEAAPI": {"Error": {"ErrorDetail": "Bad parameter"}}},
        ],
    )
    def test_api_error_raises_bea_error(self, payload):
        response = self._mock_response(payload)
        with (
            patch("sample_2.libs.utils.requests.get", return_value=response),
            pytest.raises(BEAError, match="BEA API error"),
        ):
            BEA_Wrapper(api_key=self.API_KEY).fetch_gdp_by_industry()


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

    def test_copy_to_bucket_keeps_subdirectories(self, tmp_path):
        self.s3.create_bucket(Bucket=self.BUCKET)
        for sub in ("a", "b"):
            (tmp_path / sub).mkdir()
            (tmp_path / sub / "f.csv").write_text(sub)
        AwsS3.copy_to_bucket(bucket=self.BUCKET, prefix="up/", local_dir=str(tmp_path))
        keys = AwsS3.list_bucket_files(bucket=self.BUCKET, prefix="up/")
        assert sorted(keys) == ["up/a/f.csv", "up/b/f.csv"]  # no silent overwrite

    def test_copy_from_bucket(self, tmp_path):
        self.s3.create_bucket(Bucket=self.BUCKET)
        self.s3.put_object(Bucket=self.BUCKET, Key="data/x.csv", Body=b"1,2")
        self.s3.put_object(Bucket=self.BUCKET, Key="data/sub/", Body=b"")
        self.s3.put_object(Bucket=self.BUCKET, Key="data/../../escape.txt", Body=b"no")
        AwsS3.copy_from_bucket(bucket=self.BUCKET, prefix="data/", local_dir=str(tmp_path / "out"))
        assert (tmp_path / "out" / "data" / "x.csv").read_bytes() == b"1,2"
        assert not (tmp_path / "escape.txt").exists()

    def test_create_bucket_outside_us_east_1(self, monkeypatch):
        monkeypatch.setenv("AWS_DEFAULT_REGION", "us-west-2")
        AwsS3.create_bucket(self.BUCKET)
        location = self.s3.get_bucket_location(Bucket=self.BUCKET)["LocationConstraint"]
        assert location == "us-west-2"

    def test_bucket_exists_reraises_other_errors(self):
        error = ClientError({"Error": {"Code": "403"}}, "HeadBucket")
        with patch("sample_2.libs.storages.boto3.client") as client:
            client.return_value.head_bucket.side_effect = error
            with pytest.raises(ClientError):
                AwsS3.bucket_exists(self.BUCKET)


# ---------------------------------------------------------------------------
# main.py (CLI)
# ---------------------------------------------------------------------------


class TestMain:
    BUCKET = "test-bucket-cli"

    @pytest.fixture(autouse=True)
    def env(self, monkeypatch, tmp_path):
        monkeypatch.setenv("BEA_API_KEY", "test-key")
        monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
        self.dest = str(tmp_path / "data")
        with mock_aws():
            yield

    def _df(self):
        return pd.DataFrame([{"Industry": "11", "DataValue": "100.0"}])

    def test_gdp_saves_and_uploads(self):
        with patch.object(BEA_Wrapper, "fetch_gdp_by_industry", return_value=self._df()):
            code = main(["--bucket", self.BUCKET, "--dest", self.dest, "--year", "2022"])
        assert code == 0
        keys = AwsS3.list_bucket_files(self.BUCKET, "data/")
        assert len(keys) == 2
        assert all("gdp_by_industry_2022" in k for k in keys)

    def test_datasets_option(self):
        with patch.object(BEA_Wrapper, "list_datasets", return_value=self._df()):
            assert (
                main(["--bucket", self.BUCKET, "--dest", self.dest, "--dataset", "datasets"]) == 0
            )
        assert any("bea_datasets" in k for k in AwsS3.list_bucket_files(self.BUCKET, "data/"))

    def test_delete_bucket(self):
        AwsS3.create_bucket(self.BUCKET)
        assert main(["--bucket", self.BUCKET, "--delete-bucket"]) == 0
        assert not AwsS3.bucket_exists(self.BUCKET)

    def test_missing_api_key_exits_2(self, monkeypatch):
        monkeypatch.delenv("BEA_API_KEY")
        assert main(["--bucket", self.BUCKET, "--dest", self.dest]) == 2

    @pytest.mark.parametrize(
        "error",
        [
            BEAError("BEA API error: Invalid API UserId."),
            requests.ConnectionError("down"),
            NoCredentialsError(),
            ClientError({"Error": {"Code": "AccessDenied"}}, "CreateBucket"),
        ],
    )
    def test_failures_exit_nonzero(self, error):
        with patch.object(BEA_Wrapper, "fetch_gdp_by_industry", side_effect=error):
            assert main(["--bucket", self.BUCKET, "--dest", self.dest]) == 1
