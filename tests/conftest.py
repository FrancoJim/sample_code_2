import pytest


@pytest.fixture(autouse=True)
def isolated_aws_env(monkeypatch):
    """Keep tests hermetic: fake credentials, default region, and no custom endpoint.

    The devcontainer sets AWS_ENDPOINT_URL to LocalStack; moto does not intercept
    custom endpoints, so without this the "mocked" tests would talk to LocalStack.
    """
    monkeypatch.delenv("AWS_ENDPOINT_URL", raising=False)
    monkeypatch.delenv("AWS_ENDPOINT_URL_S3", raising=False)
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
