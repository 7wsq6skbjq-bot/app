"""Client-chosen attachments for quotes (soumissions).

Files are stored in GridFS (bucket `quote_attachments`) so they survive
container redeploys, and appended to the quote PDF on download/email.
PDFs are merged page-by-page; images are wrapped into a full-page PDF.
"""
import io

from PIL import Image
from pypdf import PdfReader, PdfWriter
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorGridFSBucket
from gridfs.errors import NoFile

BUCKET = "quote_attachments"


def _bucket(db: AsyncIOMotorDatabase) -> AsyncIOMotorGridFSBucket:
    return AsyncIOMotorGridFSBucket(db, bucket_name=BUCKET)


async def store_attachment(db, *, att_id: str, quote_id: str,
                            filename: str, content_type: str, raw: bytes) -> None:
    await _bucket(db).upload_from_stream(
        filename, raw,
        metadata={"att_id": att_id, "quote_id": quote_id,
                  "content_type": content_type, "filename": filename},
    )


async def fetch_attachment(db, att_id: str):
    bucket = _bucket(db)
    docs = await bucket.find({"metadata.att_id": att_id}).to_list(1)
    if not docs:
        return None, None
    stream = await bucket.open_download_stream(docs[0]._id)
    data = await stream.read()
    return data, (docs[0].metadata or {}).get("content_type")


async def delete_attachment(db, att_id: str) -> None:
    bucket = _bucket(db)
    async for gf in bucket.find({"metadata.att_id": att_id}):
        try:
            await bucket.delete(gf._id)
        except NoFile:
            pass


def _image_to_pdf_bytes(raw: bytes) -> bytes:
    """Wrap a raster image into a single-page PDF (fits Letter, keeps ratio)."""
    img = Image.open(io.BytesIO(raw))
    if img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PDF", resolution=150.0)
    buf.seek(0)
    return buf.read()


def append_files_to_pdf(base_pdf: bytes, files: list) -> bytes:
    """files = list of (raw_bytes, content_type, filename). Returns merged PDF."""
    writer = PdfWriter()
    writer.append(PdfReader(io.BytesIO(base_pdf)))
    for raw, content_type, _fname in files:
        try:
            ct = (content_type or "").lower()
            if "pdf" in ct:
                writer.append(PdfReader(io.BytesIO(raw)))
            else:
                writer.append(PdfReader(io.BytesIO(_image_to_pdf_bytes(raw))))
        except Exception:
            continue  # skip a bad file rather than break the whole PDF
    out = io.BytesIO()
    writer.write(out)
    out.seek(0)
    return out.read()
