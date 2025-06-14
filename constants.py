import boto3
import os

allowed_extensions = [".m4a"]
valid_genders = ["woman", "man", "other"]
bucket_name = os.getenv('BUCKET_NAME')
inference_endpoint = os.getenv('INFERENCE_ENDPOINT')
max_duration_s = 30
region_name = "eu-north-1"
s3_client = boto3.client("s3",
						 aws_access_key_id=os.getenv('AWS_ACC_KEY'),
						 aws_secret_access_key=os.getenv('AWS_SEC_ACC_KEY'),
						 region_name=region_name)
headers = {
	"Accept" : "application/json",
	"Authorization": f"Bearer {os.getenv('HF_TOKEN')}",
	"Content-Type" : "audio/wav"
}