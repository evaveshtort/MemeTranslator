import boto3
import os
import uuid
from PIL import Image
import io

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = boto3.client(
            "s3",
            endpoint_url="https://storage.yandexcloud.net",
            aws_access_key_id=os.environ["S3_ACCESS_KEY"],
            aws_secret_access_key=os.environ["S3_SECRET_KEY"],
            region_name="ru-central1",
        )
    return _client


def upload_image(img: Image.Image, folder: str = "memes") -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    bucket = os.environ["S3_BUCKET"]
    key = f"{folder}/{uuid.uuid4()}.png"

    _get_client().put_object(
        Bucket=bucket,
        Key=key,
        Body=buf,
        ContentType="image/png",
    )

    return f"https://storage.yandexcloud.net/{bucket}/{key}"
