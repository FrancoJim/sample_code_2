import logging
from pathlib import Path

import boto3

logger = logging.getLogger(__name__)


class AwsS3:
    @staticmethod
    def create_bucket(bucket: str) -> None:
        """Create an S3 bucket if it does not already exist."""
        s3 = boto3.resource("s3")
        if s3.Bucket(bucket) in s3.buckets.all():
            logger.info(f"Bucket {bucket} already exists")
            return
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
        """Download all objects under prefix from bucket to local_dir."""
        s3 = boto3.resource("s3")
        s3_bucket = s3.Bucket(bucket)
        for obj in s3_bucket.objects.filter(Prefix=prefix):
            local_file = local_dir + obj.key
            s3_bucket.download_file(obj.key, local_file)
            logger.info(f"Downloaded {obj.key} to {local_file}")

    @staticmethod
    def copy_to_bucket(bucket: str, prefix: str, local_dir: str) -> None:
        """Upload all files in local_dir to bucket under prefix."""
        s3 = boto3.resource("s3")
        s3_bucket = s3.Bucket(bucket)
        for path in Path(local_dir).rglob("*"):
            if path.is_file():
                key = prefix + path.name
                s3_bucket.upload_file(str(path), key)
                logger.info(f"Uploaded {path} to s3://{bucket}/{key}")

    @staticmethod
    def delete_bucket_and_contents(bucket: str) -> None:
        """Delete all objects in bucket and then delete the bucket itself."""
        s3 = boto3.resource("s3")
        if s3.Bucket(bucket) not in s3.buckets.all():
            logger.info(f"Bucket {bucket} does not exist")
            return
        s3_bucket = s3.Bucket(bucket)
        s3_bucket.objects.all().delete()
        s3_bucket.delete()
        logger.info(f"Bucket {bucket} deleted")
