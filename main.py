import logging
import uuid
import httpx
from fastapi import FastAPI, UploadFile, Form, status
from fastapi.responses import PlainTextResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from constants import allowed_extensions, inference_endpoint, headers
from utils.utils import (
    extract_file_ext, file_ext_is_valid,
    is_audio_duration_longer_than_allowed, is_consent_given,
    store_audio_to_s3, get_wav_bytes_from_m4a, is_gender_valid
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI()

app.mount("/assets", StaticFiles(directory="assets"), name="assets")

@app.get("/", response_class=HTMLResponse)
async def index():
    logger.info("Serving index.html")
    with open('index.html', 'r') as home_page_file:
        return HTMLResponse(content=home_page_file.read())

@app.post("/transcribe/")
async def receive_audio(
    file: UploadFile,
    age: str = Form(...),
    gender: str = Form(...),
    consent: str = Form(...)
) -> PlainTextResponse:

    logger.info(f"Received file: {file.filename}, Content-Type: {file.content_type}")
    file_ext = extract_file_ext(file)
    logger.debug(f"Extracted file extension: {file_ext}")

    if not file_ext_is_valid(file_ext, allowed_extensions):
        logger.warning(f"Invalid file extension: {file_ext}")
        return PlainTextResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content="Only .m4a files are allowed.",
        )

    unique_filename = f"{uuid.uuid4()}{file_ext}"
    contents = await file.read()
    logger.info(f"Generated unique filename: {unique_filename}, size: {len(contents)} bytes")

    try:
        overboard, duration = is_audio_duration_longer_than_allowed(contents)
        logger.info(f"Audio duration: {duration:.2f}s, Over limit: {overboard}")
        if overboard:
            return PlainTextResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=f"Audio too long ({duration:.1f}s). Max is 30s.",
            )
    except Exception as e:
        logger.exception("Failed during duration check")
        return PlainTextResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=f"Invalid audio file: {str(e)}"
        )

    if is_consent_given(consent) and is_gender_valid(gender):
        logger.info(f"Consent given. Storing to S3. Age: {age}, Gender: {gender}")
        store_audio_to_s3(unique_filename, contents, file.content_type, {
            "age": age.lower(),
            "gender": gender
        })
    else:
        logger.info("Consent not given. Skipping S3 storage.")

    wav_bytes = get_wav_bytes_from_m4a(contents)
    logger.info(f"Converted audio to WAV. Size: {len(wav_bytes)} bytes")

    try:
        async with httpx.AsyncClient() as client:
            logger.info(f"Sending audio to inference endpoint: {inference_endpoint}")
            response = await client.post(inference_endpoint, content=wav_bytes, headers=headers)
            logger.info(f"Inference response status: {response.status_code}")
    except httpx.HTTPStatusError as e:
        logger.error(f"Transcriber responded with error: {e.response.status_code} - {e.response.text}")
        return PlainTextResponse(
            status_code=e.response.status_code,
            content=f"Transcriber responded with error: {e.response.text}",
        )
    except Exception as e:
        logger.exception("Unexpected error during transcription request")
        return PlainTextResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=f"Transcription failed: {str(e)}",
        )

    return PlainTextResponse(status_code=status.HTTP_200_OK, content=response.text)
