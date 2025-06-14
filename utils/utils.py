
from fastapi import UploadFile
from io import BytesIO
from constants import bucket_name, max_duration_s, s3_client
import os
from pydub import AudioSegment


def extract_file_ext(file: UploadFile) -> str:
 return os.path.splitext(file.filename or "audio.m4a")[-1].lower()


def file_ext_is_valid(file_ext: str, allowed_extensions: list[str]) -> bool:
    return file_ext.lower() in allowed_extensions


def get_audio_duration(contents: bytes, format: str = "m4a") -> float:
    audio = AudioSegment.from_file(BytesIO(contents), format=format)
    return len(audio) / 1000.0


def is_audio_duration_longer_than_allowed(contents: bytes) -> tuple[bool, float]:
    duration = get_audio_duration(contents)
    return duration > max_duration_s, duration


def is_consent_given(consent: str) -> bool:
    return consent.strip().lower() == "true"


def is_gender_valid(gender: str) -> bool:
    return gender.strip().lower() in valid_genders

def store_audio_to_s3(
    filename: str,
    contents: bytes,
    content_type: str | None,
    metadata: dict
) -> None:
    s3_client.put_object(
        Bucket=bucket_name,
        Key=filename,
        Body=contents,
        ContentType=content_type,
        Metadata={key.lower(): str(value).lower() for key, value in metadata.items()}
    )

def get_wav_bytes_from_m4a(contents: bytes) -> bytes:
    audio = AudioSegment.from_file(BytesIO(contents), format="m4a")
    buf = BytesIO()
    audio.export(buf, format="wav")
    return buf.getvalue()