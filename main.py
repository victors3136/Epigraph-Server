from fastapi import FastAPI, UploadFile, Form, status
from fastapi.responses import PlainTextResponse
import boto3
import uuid
import httpx
import os
from pydub import AudioSegment
from io import BytesIO

app = FastAPI()

bucket_name = "romanian-asr-data"
region_name = "eu-north"
inference_endpoint = "https://postman-echo.com/post"
allowed_extensions = [".m4a"]
max_duration_s = 30

s3_client = boto3.client("s3", region_name=region_name)

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


@app.post("/upload-audio/")
async def receive_audio(
    file: UploadFile,
    age: str = Form(...),
    gender: str = Form(...),
    consent: str = Form(...)
) -> PlainTextResponse:

    file_ext = extract_file_ext(file)

    if not file_ext_is_valid(file_ext, allowed_extensions):
        return PlainTextResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content="Only .m4a files are allowed.",
        )

    unique_filename = f"{uuid.uuid4()}{file_ext}"
    contents = await file.read()

    try:
        overboard, duration = is_audio_duration_longer_than_allowed(contents)
        if overboard:
            return PlainTextResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=f"Audio too long ({duration:.1f}s). Max is 30s.",
            )
    except Exception as e:
        return PlainTextResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=f"Invalid audio file: {str(e)}"
        )

    if is_consent_given(consent):
        store_audio_to_s3(unique_filename, contents, file.content_type, {
                "age": age.lower(),
                "gender": gender.lower()
            })

    try:
        async with httpx.AsyncClient() as client:
            files = {'file': (unique_filename, contents, file.content_type)}
            response = await client.post(inference_endpoint, files=files)
            response.raise_for_status()
            transcription = response.text
    except httpx.HTTPStatusError as e:
        return PlainTextResponse(
            status_code=e.response.status_code,
            content=f"Transcriber responded with error: {e.response.text}",
        )
    except Exception as e:
        return PlainTextResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=f"Transcription failed: {str(e)}",
        )

    return PlainTextResponse(status_code=status.HTTP_200_OK, content=transcription)
