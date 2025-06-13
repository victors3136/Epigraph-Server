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


@app.post("/upload-audio/")
async def receive_audio(
    file: UploadFile,
    age: str = Form(...),
    gender: str = Form(...),
    consent: str = Form(...)
) -> PlainTextResponse:

    file_ext = os.path.splitext(file.filename or "audio.m4a")[-1].lower()
    if file_ext not in allowed_extensions:
        return PlainTextResponse(
            "Only .m4a files are allowed.",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    unique_filename = f"{uuid.uuid4()}{file_ext}"
    contents = await file.read()

    try:
        audio = AudioSegment.from_file(BytesIO(contents), format="m4a")
        audio_duration_s = len(audio) / 1000.0
        if audio_duration_s > max_duration_s:
            return PlainTextResponse(
                f"Audio too long ({audio_duration_s:.1f}s). Max is 30s.",
                status_code=status.HTTP_400_BAD_REQUEST
            )
    except Exception as e:
        return PlainTextResponse(
            f"Invalid audio file: {str(e)}",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    if consent.lower() == "true":
        s3_client.put_object(
            Bucket=bucket_name,
            Key=unique_filename,
            Body=contents,
            ContentType=file.content_type,
            Metadata={
                "age": age.lower(),
                "gender": gender.lower()
            }
        )

    try:
        async with httpx.AsyncClient() as client:
            files = {'file': (unique_filename, contents, file.content_type)}
            response = await client.post(inference_endpoint, files=files)
            response.raise_for_status()
            transcription = response.text
    except httpx.HTTPStatusError as e:
        return PlainTextResponse(
            f"Transcriber responded with error: {e.response.text}",
            status_code=e.response.status_code
        )
    except Exception as e:
        return PlainTextResponse(
            f"Transcription failed: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return PlainTextResponse(transcription, status_code=status.HTTP_200_OK)
