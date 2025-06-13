import boto3

allowed_extensions = [".m4a"]
bucket_name = "romanian-asr-data"
inference_endpoint = "https://postman-echo.com/post"
max_duration_s = 30
region_name = "eu-north"
s3_client = boto3.client("s3", region_name=region_name)