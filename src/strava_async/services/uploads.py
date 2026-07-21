"""The ``/uploads`` surface."""

from typing import BinaryIO

from strava_async.schemas.upload_model import CreateUploadRequestBody, Upload
from strava_async.services.base import Base

__all__ = ["UploadsService"]


class UploadsService(Base):
    """Activity file uploads."""

    async def create_upload(
        self, upload: CreateUploadRequestBody, file: BinaryIO | bytes
    ) -> Upload:
        """Upload an activity file. Requires ``activity:write`` scope.

        Processing is asynchronous: this returns as soon as Strava accepts the file, with
        neither ``activity_id`` nor ``error`` set. Poll :meth:`get_upload_by_id` until
        ``Upload.is_complete``.

        Args:
            upload: The file's format and the resulting activity's metadata.
            file: The file itself, as a binary stream or bytes.

        Returns:
            The upload's initial state.
        """
        return await self._post_multipart(
            endpoint=f"{self.base_url}/uploads",
            model=Upload,
            payload=upload,
            file=file,
            filename=f"activity.{upload.data_type}",
        )

    async def get_upload_by_id(self, upload_id: int) -> Upload:
        """Check on an upload. Requires ``activity:write`` scope.

        Args:
            upload_id: The identifier of the upload, from :meth:`create_upload`.

        Returns:
            The upload's current state.
        """
        return await self.fetch_data(
            endpoint=f"{self.base_url}/uploads/{upload_id}",
            model=Upload,
        )
