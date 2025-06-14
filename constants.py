import boto3
import os

allowed_extensions = [".m4a"]
bucket_name = os.getenv('BUCKET_NAME')
inference_endpoint = os.getenv('INFERENCE_ENDPOINT')
max_duration_s = 30
region_name = "eu-north"
s3_client = boto3.client("s3", region_name=region_name)
headers = {
	"Accept" : "application/json",
	"Authorization": f"Bearer {os.getenv('HF_TOKEN')}",
	"Content-Type": "application/json"
}