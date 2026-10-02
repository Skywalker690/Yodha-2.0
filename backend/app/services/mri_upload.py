"""Validate MRI upload selections and store one managed volume and preview."""

from pathlib import Path

from fastapi import HTTPException, UploadFile

from backend.app.core.config import get_settings
from backend.app.services.storage import new_key, resolve_key
from ml.preprocessing import convert_paired_volume, render_preview

VOLUME_MIME_TYPES = {
    "application/octet-stream", "application/gzip", "application/x-gzip",
    "application/x-nifti", "application/nifti", "", None,
}
PAIR_MIME_TYPES = {
    "application/octet-stream", "application/x-nifti", "application/nifti",
    "image/vnd.radiance", "application/x-raw-disk-image", "application/x-disk-image",
    "", None,
}


def _filename(upload: UploadFile) -> str:
    # Names identify matching partners only and are never used as storage paths.
    return (upload.filename or "").replace("\\", "/").rsplit("/", 1)[-1].lower()


def _copy_upload(upload: UploadFile, destination: Path, used_bytes: int, limit: int) -> int:
    with destination.open("wb") as output:
        while chunk := upload.file.read(1024 * 1024):
            used_bytes += len(chunk)
            if used_bytes > limit:
                raise HTTPException(413, "Selected MRI files exceed the combined 100 MiB upload limit.")
            output.write(chunk)
    return used_bytes


def store_mri_upload(
    file: UploadFile | None, header: UploadFile | None, image: UploadFile | None,
) -> tuple[str, str, dict]:
    """Accept a single NIfTI or one matched pair, with bounded staging and cleanup."""
    if file is not None and (header is not None or image is not None):
        raise HTTPException(422, "Choose one NIfTI volume or a matching .hdr/.img pair, not both.")
    if file is None and (header is None or image is None):
        raise HTTPException(422, "Select a .nii/.nii.gz volume or both matching .hdr and .img files.")
    if file is not None:
        name = _filename(file)
        suffix = ".nii.gz" if name.endswith(".nii.gz") else ".nii" if name.endswith(".nii") else None
        if suffix is None:
            raise HTTPException(415, "Select a .nii/.nii.gz volume, or upload .hdr and .img together.")
        if file.content_type not in VOLUME_MIME_TYPES:
            raise HTTPException(415, "Unsupported MRI content type.")
    else:
        assert header is not None and image is not None
        header_name, image_name = _filename(header), _filename(image)
        if not header_name.endswith(".hdr") or not image_name.endswith(".img"):
            raise HTTPException(415, "The header must end in .hdr and the image must end in .img.")
        if not header_name[:-4] or header_name[:-4] != image_name[:-4]:
            raise HTTPException(422, "The .hdr and .img filenames must have the same name before the extension.")
        if header.content_type not in PAIR_MIME_TYPES or image.content_type not in PAIR_MIME_TYPES:
            raise HTTPException(415, "Unsupported header/image content type.")
        suffix = ".nii.gz"

    key, preview = new_key("raw", suffix), new_key("derived", ".png")
    path, thumbnail = resolve_key(key), resolve_key(preview)
    staging: list[Path] = []
    limit = get_settings().max_upload_bytes
    try:
        if file is not None:
            _copy_upload(file, path, 0, limit)
        else:
            assert header is not None and image is not None
            staged_header = resolve_key(new_key("staging", ".hdr"))
            staged_image = staged_header.with_suffix(".img")
            staging.extend((staged_header, staged_image))
            used = _copy_upload(header, staged_header, 0, limit)
            _copy_upload(image, staged_image, used, limit)
            convert_paired_volume(staged_header, path)
        if path.stat().st_size > limit:
            raise HTTPException(413, "Converted MRI exceeds the 100 MiB managed volume limit.")
        metadata = render_preview(path, thumbnail)
        metadata["mri_upload_format"] = "nifti_single" if file is not None else "hdr_img_pair"
        return key, preview, metadata
    except Exception:
        path.unlink(missing_ok=True)
        thumbnail.unlink(missing_ok=True)
        raise
    finally:
        for staged in staging:
            staged.unlink(missing_ok=True)
