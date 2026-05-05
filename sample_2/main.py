import argparse
import logging
import os
from datetime import datetime as dt

from botocore.exceptions import NoCredentialsError

from sample_2.libs.storages import AwsS3
from sample_2.libs.utils import BEA_Wrapper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
)
logger = logging.getLogger(__name__)


def run(
    s3_bucket: str,
    dest_path: str,
    dataset: str,
    year: str,
    delete_bucket: bool,
) -> None:
    if delete_bucket:
        AwsS3.delete_bucket_and_contents(bucket=s3_bucket)
        logger.info(f"Deleted bucket {s3_bucket}")
        return

    bea = BEA_Wrapper(api_key=os.environ["BEA_API_KEY"])

    if dataset == "datasets":
        df = bea.list_datasets()
        file_name = "bea_datasets"
    else:
        df = bea.fetch_gdp_by_industry(year=year)
        file_name = f"gdp_by_industry_{year}"

    os.makedirs(dest_path, exist_ok=True)
    timestamp = dt.now().strftime("%Y%m%d%H%M%S")
    base = f"{dest_path}/{timestamp}.{file_name}"
    df.to_pickle(f"{base}.pkl")
    df.to_csv(f"{base}.csv", index=False)
    logger.info(f"Saved {len(df)} rows to {base}.{{pkl,csv}}")

    try:
        AwsS3.create_bucket(bucket=s3_bucket)
        logger.info(f"Buckets: {AwsS3.list_buckets()}")
        AwsS3.copy_to_bucket(bucket=s3_bucket, prefix="data/", local_dir=dest_path)
        logger.info(
            f"Upload complete. Objects in {s3_bucket}: {AwsS3.list_bucket_files(bucket=s3_bucket, prefix='data/')}"
        )
    except NoCredentialsError:
        logger.error("AWS credentials not found — skipping S3 upload")
    except Exception as e:
        logger.error(f"S3 error: {e}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch BEA economic data and store it in AWS S3.")
    parser.add_argument("--bucket", required=True, help="S3 bucket name")
    parser.add_argument("--dest", default="./data", help="Local output directory (default: ./data)")
    parser.add_argument(
        "--dataset",
        choices=["datasets", "gdp"],
        default="gdp",
        help="Which BEA dataset to fetch (default: gdp)",
    )
    parser.add_argument("--year", default="2023", help="Year for GDP data (default: 2023)")
    parser.add_argument(
        "--delete-bucket",
        action="store_true",
        help="Delete the S3 bucket and all its contents, then exit",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = parse_args()
    run(
        s3_bucket=args.bucket,
        dest_path=args.dest,
        dataset=args.dataset,
        year=args.year,
        delete_bucket=args.delete_bucket,
    )
