from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest

from src.infrastructure.storage.s3_storage import S3ObjectStorage


@asynccontextmanager
async def _fake_client_cm(client: AsyncMock):
    yield client


@pytest.fixture(autouse=True)
def _reset_settings():
    import src.core.config as config_module

    original_endpoint = config_module.settings.s3_endpoint_url
    original_public_base = config_module.settings.s3_public_base_url
    original_bucket = config_module.settings.s3_bucket
    yield
    config_module.settings.s3_endpoint_url = original_endpoint
    config_module.settings.s3_public_base_url = original_public_base
    config_module.settings.s3_bucket = original_bucket


async def test_upload_builds_path_style_url_from_endpoint_when_no_public_base_url_set() -> None:
    import src.core.config as config_module

    config_module.settings.s3_endpoint_url = "https://minio.internal:9000"
    config_module.settings.s3_public_base_url = None
    config_module.settings.s3_bucket = "media"

    fake_client = AsyncMock()
    with patch("aioboto3.Session.client", return_value=_fake_client_cm(fake_client)):
        url = await S3ObjectStorage().upload(
            key="tenants/t1/logo.png", content=b"x", content_type="image/png"
        )

    fake_client.put_object.assert_awaited_once()
    assert url == "https://minio.internal:9000/media/tenants/t1/logo.png"


async def test_upload_uses_bucket_scoped_public_base_url_when_set() -> None:
    """The R2 case: the API endpoint used for the PUT isn't the same host
    that serves public reads, so the returned URL must come from
    s3_public_base_url instead — and without a bucket path segment, since
    that URL is already scoped to one bucket."""
    import src.core.config as config_module

    config_module.settings.s3_endpoint_url = "https://acct123.r2.cloudflarestorage.com"
    config_module.settings.s3_public_base_url = "https://pub-abc123.r2.dev"
    config_module.settings.s3_bucket = "media"

    fake_client = AsyncMock()
    with patch("aioboto3.Session.client", return_value=_fake_client_cm(fake_client)):
        url = await S3ObjectStorage().upload(
            key="tenants/t1/logo.png", content=b"x", content_type="image/png"
        )

    assert url == "https://pub-abc123.r2.dev/tenants/t1/logo.png"


async def test_upload_falls_back_to_aws_s3_bucket_subdomain_with_no_endpoint_configured() -> None:
    import src.core.config as config_module

    config_module.settings.s3_endpoint_url = None
    config_module.settings.s3_public_base_url = None
    config_module.settings.s3_bucket = "media"

    fake_client = AsyncMock()
    with patch("aioboto3.Session.client", return_value=_fake_client_cm(fake_client)):
        url = await S3ObjectStorage().upload(
            key="tenants/t1/logo.png", content=b"x", content_type="image/png"
        )

    assert url == "https://media.s3.amazonaws.com/media/tenants/t1/logo.png"
