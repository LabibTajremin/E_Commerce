import aioboto3
import pytest

from src.infrastructure.storage.s3_storage import S3ObjectStorage


@pytest.fixture
async def s3_storage(minio_endpoint_url: str):
    import src.core.config as config_module

    config_module.settings.s3_endpoint_url = minio_endpoint_url
    config_module.settings.s3_access_key = "minioadmin"
    config_module.settings.s3_secret_key = "minioadmin"
    config_module.settings.s3_bucket = "test-store-media"

    session = aioboto3.Session()
    async with session.client(
        "s3",
        endpoint_url=minio_endpoint_url,
        aws_access_key_id="minioadmin",
        aws_secret_access_key="minioadmin",
        region_name="us-east-1",
    ) as client:
        await client.create_bucket(Bucket="test-store-media")

    return S3ObjectStorage()


async def test_upload_stores_object_and_returns_retrievable_url(
    s3_storage: S3ObjectStorage,
) -> None:
    url = await s3_storage.upload(
        key="tenants/t1/logo/logo.png", content=b"fake-png-bytes", content_type="image/png"
    )

    assert "test-store-media" in url
    assert url.endswith("tenants/t1/logo/logo.png")

    session = aioboto3.Session()
    import src.core.config as config_module

    async with session.client(
        "s3",
        endpoint_url=config_module.settings.s3_endpoint_url,
        aws_access_key_id="minioadmin",
        aws_secret_access_key="minioadmin",
        region_name="us-east-1",
    ) as client:
        obj = await client.get_object(Bucket="test-store-media", Key="tenants/t1/logo/logo.png")
        body = await obj["Body"].read()

    assert body == b"fake-png-bytes"
