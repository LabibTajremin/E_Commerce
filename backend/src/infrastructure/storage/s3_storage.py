import aioboto3

from src.core.config import settings


class S3ObjectStorage:
    def __init__(self) -> None:
        self._session = aioboto3.Session()

    async def upload(self, *, key: str, content: bytes, content_type: str) -> str:
        async with self._session.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
        ) as client:
            await client.put_object(
                Bucket=settings.s3_bucket, Key=key, Body=content, ContentType=content_type
            )

        if settings.s3_public_base_url is not None:
            # Already bucket-scoped (an R2.dev subdomain or a custom domain
            # mapped to one bucket) — no bucket segment in the path.
            return f"{settings.s3_public_base_url.rstrip('/')}/{key}"

        base = settings.s3_endpoint_url or f"https://{settings.s3_bucket}.s3.amazonaws.com"
        return f"{base.rstrip('/')}/{settings.s3_bucket}/{key}"
