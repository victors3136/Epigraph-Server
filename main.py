from constants import allowed_extensions, inference_endpoint
from fastapi import FastAPI, UploadFile, Form, status
from fastapi.responses import PlainTextResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import uuid
import httpx
from utils.utils import extract_file_ext, file_ext_is_valid, is_audio_duration_longer_than_allowed, is_consent_given, store_audio_to_s3
app = FastAPI()

app.mount("/assets", StaticFiles(directory="assets"), name="assets")
@app.get("/", response_class=HTMLResponse)
async def index():
    html_content = """
                   <!DOCTYPE html>
                   <html lang="en">
                   <head>
                       <meta charset="UTF-8">
                       <title>Welcome to Epigraph Server</title>
                       <style>
                           body {
                               font-family: Arial, sans-serif;
                               background-color: #3a3e40;
                               margin: 0;
                               padding: 0;
                               display: flex;
                               justify-content: center;
                               align-items: center;
                               width: auto;
                           }

                           .container {
                               text-align: center;
                               background: #232933;
                               margin-top: 10px;
                               border-radius: 12px;
                               box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
                           }

                           img {
                               max-width: 60%;
                               height: auto;
                               border-radius: 8px;
                               margin-top: 20px;
                           }

                           h1 {
                               color: #d6d6d6;
                               font-size: 2em;
                           }
                       </style>
                   </head>
                   <body>
                   <div class="container">
                       <img src="/assets/index-photo.png" alt="Welcome Image">
                       <h1>Welcome to Epigraph Server!</h1>
                   </div>
                   </body>
                   </html> \
                   """
    return HTMLResponse(content=html_content)

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
