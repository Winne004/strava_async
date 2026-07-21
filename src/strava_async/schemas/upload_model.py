"""Activity file uploads.

Uploads are asynchronous: the POST returns immediately with a status, and the caller
polls ``GET /uploads/{uploadId}`` until ``activity_id`` or ``error`` is set.
"""

from typing import Literal

from strava_async.schemas.base import RequestModel, ResponseModel

__all__ = ["CreateUploadRequestBody", "Upload", "UploadDataType"]

type UploadDataType = Literal["fit", "fit.gz", "tcx", "tcx.gz", "gpx", "gpx.gz"]


class Upload(ResponseModel):
    """The state of an upload.

    ``activity_id`` stays null until processing finishes; ``error`` is set instead if it
    fails. Both null means Strava is still working.
    """

    id: int | None = None
    id_str: str | None = None
    external_id: str | None = None
    error: str | None = None
    status: str | None = None
    activity_id: int | None = None

    @property
    def is_complete(self) -> bool:
        """Whether Strava has finished with this upload, successfully or not."""
        return self.activity_id is not None or self.error is not None


class CreateUploadRequestBody(RequestModel):
    """The non-file parts of ``POST /uploads``. Requires ``activity:write`` scope.

    The file itself is passed separately, since it is a stream rather than a
    serialisable field.
    """

    data_type: UploadDataType
    name: str | None = None
    description: str | None = None
    trainer: bool | None = None
    commute: bool | None = None
    external_id: str | None = None
