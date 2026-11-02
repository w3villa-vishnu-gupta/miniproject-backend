import os
from pathlib import Path
import boto3
from dotenv import find_dotenv, load_dotenv
from botocore.config import Config

# Ensure .env is properly loaded regardless of current working directory
dotenv_path = find_dotenv(usecwd=True)
if not dotenv_path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / ".env"
        if candidate.exists():
            dotenv_path = str(candidate)
            break

load_dotenv(dotenv_path)

# Storj S3 Gateway Configuration
STORJ_ENDPOINT = os.getenv("STORJ_ENDPOINT", "https://gateway.storjshare.io")
STORJ_ACCESS_KEY = os.getenv("STORJ_ACCESS_KEY")
STORJ_SECRET_KEY = os.getenv("STORJ_SECRET_KEY")
BUCKET = os.getenv("STORJ_BUCKET", "profile-picture")

# Important for Storj:
# 1. signature_version="s3v4"
# 2. s3={"addressing_style": "path"}
# 3. request_checksum_calculation="when_required" and response_checksum_validation="when_required"
#    disables trailing checksum chunked transfer encoding (Transfer-Encoding: chunked),
#    which Storj rejects with MissingContentLength.
storj_config = Config(
    signature_version="s3v4",
    s3={"addressing_style": "path"},
    request_checksum_calculation="when_required",
    response_checksum_validation="when_required",
)

storj = boto3.client(
    "s3",
    endpoint_url=STORJ_ENDPOINT,
    aws_access_key_id=STORJ_ACCESS_KEY,
    aws_secret_access_key=STORJ_SECRET_KEY,
    region_name="us-east-1",
    config=storj_config,
)


def upload_image(file_bytes: bytes, object_key: str, content_type: str = "image/jpeg"):
    """
    Uploads an image to Storj bucket with explicit Content-Length and Content-Type.
    """
    if not BUCKET:
        raise ValueError("STORJ_BUCKET is not configured in environment variables.")

    response = storj.put_object(
        Bucket=BUCKET,
        Key=object_key,
        Body=file_bytes,
        ContentLength=len(file_bytes),
        ContentType=content_type,
    )

    return {
        "object_key": object_key,
        "etag": response.get("ETag"),
    }


def delete_image(object_key: str):
    """
    Deletes an object from Storj bucket.
    """
    if not BUCKET or not object_key:
        return

    storj.delete_object(
        Bucket=BUCKET,
        Key=object_key,
    )


def get_image_url(object_key: str, expires_in: int = 3600):
    """
    Generates a presigned URL to view/download the object from Storj.
    """
    if not BUCKET or not object_key:
        return ""

    return storj.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": BUCKET,
            "Key": object_key,
        },
        ExpiresIn=expires_in,
    )
