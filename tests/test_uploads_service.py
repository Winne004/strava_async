"""UploadsService delegates each endpoint correctly."""

import io
from typing import Any
from unittest.mock import AsyncMock

from strava_async.schemas.upload_model import CreateUploadRequestBody, Upload
from strava_async.services.uploads import UploadsService
from tests.conftest import BASE_URL

SENTINEL = object()


def service(make_service: Any, helper: str = "fetch_data") -> tuple[UploadsService, AsyncMock]:
    instance = make_service(UploadsService)
    mock = AsyncMock(return_value=SENTINEL)
    setattr(instance, helper, mock)
    return instance, mock


async def test_create_upload_posts_multipart(make_service: Any) -> None:
    """The file is a stream, so it stays a separate argument from the model."""
    instance, mock = service(make_service, "_post_multipart")
    body = CreateUploadRequestBody(data_type="gpx", name="Morning Ride")
    file = io.BytesIO(b"<gpx/>")

    assert await instance.create_upload(body, file) is SENTINEL
    mock.assert_awaited_once_with(
        endpoint=f"{BASE_URL}/uploads",
        model=Upload,
        payload=body,
        file=file,
        filename="activity.gpx",
    )


async def test_get_upload_by_id(make_service: Any) -> None:
    instance, mock = service(make_service)

    assert await instance.get_upload_by_id(98765) is SENTINEL
    mock.assert_awaited_once_with(endpoint=f"{BASE_URL}/uploads/98765", model=Upload)
