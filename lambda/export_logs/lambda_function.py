import boto3
import gzip
import json
import base64
from datetime import datetime

s3 = boto3.client('s3')
BUCKET_NAME = 'autopatch-logs-archive'

def lambda_handler(event, context):
    data = event['awslogs']['data']
    decoded = base64.b64decode(data)
    decompressed = gzip.decompress(decoded)
    log_json = json.loads(decompressed)
    
    # Extract logGroup name for prefix
    log_group = log_json.get('logGroup', 'unknown-loggroup').replace('/', '-')
    now = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")
    s3_key = f"{log_group}/log_{now}.json"
    
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=s3_key,
        Body=json.dumps(log_json, indent=2),
        ContentType='application/json'
    )
    
    return {
        'statusCode': 200,
        'body': f"Logs saved to {s3_key}"
    }