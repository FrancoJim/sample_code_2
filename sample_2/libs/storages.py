import logging
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class AwsS3:
    @staticmethod
    def bucket_exists(bucket: str) -> bool:
        """True if the bucket exists and is reachable (HeadBucket; no account-wide ListBuckets)."""
        try:
            boto3.client("s3").head_bucket(Bucket=bucket)
            return True
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") in ("404", "NoSuchBucket"):
                return False
            raise

    @staticmethod
    def create_bucket(bucket: str) -> None:
        """Create an S3 bucket if it does not already exist."""
        if AwsS3.bucket_exists(bucket):
            logger.info(f"Bucket {bucket} already exists")
            return
        s3 = boto3.client("s3")
        region = s3.meta.region_name
        if region and region != "us-east-1":
            # Every region except us-east-1 requires an explicit LocationConstraint.
            config: Any = {"LocationConstraint": region}  # runtime str vs. the stubs' Literal
            s3.create_bucket(Bucket=bucket, CreateBucketConfiguration=config)
        else:
            s3.create_bucket(Bucket=bucket)
        logger.info(f"Bucket {bucket} created")

    @staticmethod
    def list_buckets() -> list[str]:
        """Return names of all S3 buckets in the account."""
        s3 = boto3.client("s3")
        response = s3.list_buckets()
        return [bucket["Name"] for bucket in response["Buckets"]]

    @staticmethod
    def list_bucket_files(bucket: str, prefix: str) -> list[str]:
        """Return keys of all objects in bucket under prefix."""
        s3 = boto3.client("s3")
        response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
        return [content["Key"] for content in response.get("Contents", [])]

    @staticmethod
    def copy_from_bucket(bucket: str, prefix: str, local_dir: str) -> None:
        """Download all objects under prefix from bucket into local_dir, keeping their key paths."""
        s3 = boto3.resource("s3")
        s3_bucket = s3.Bucket(bucket)
        root = Path(local_dir).resolve()
        for obj in s3_bucket.objects.filter(Prefix=prefix):
            if obj.key.endswith("/"):  # "folder" placeholder objects
                continue
            local_file = (root / obj.key).resolve()
            if not local_file.is_relative_to(root):  # don't let "../" keys escape local_dir
                logger.warning(f"Skipping {obj.key}: resolves outside {root}")
                continue
            local_file.parent.mkdir(parents=True, exist_ok=True)
            s3_bucket.download_file(obj.key, str(local_file))
            logger.info(f"Downloaded {obj.key} to {local_file}")

    @staticmethod
    def copy_to_bucket(bucket: str, prefix: str, local_dir: str) -> None:
        """Upload all files in local_dir to bucket under prefix, keeping subdirectory paths."""
        s3 = boto3.resource("s3")
        s3_bucket = s3.Bucket(bucket)
        root = Path(local_dir)
        for path in root.rglob("*"):
            if path.is_file():
                key = prefix + path.relative_to(root).as_posix()
                s3_bucket.upload_file(str(path), key)
                logger.info(f"Uploaded {path} to s3://{bucket}/{key}")

    @staticmethod
    def delete_bucket_and_contents(bucket: str) -> None:
        """Delete all objects in bucket and then delete the bucket itself."""
        if not AwsS3.bucket_exists(bucket):
            logger.info(f"Bucket {bucket} does not exist")
            return
        s3_bucket = boto3.resource("s3").Bucket(bucket)
        s3_bucket.objects.all().delete()
        s3_bucket.delete()
        logger.info(f"Bucket {bucket} deleted")
