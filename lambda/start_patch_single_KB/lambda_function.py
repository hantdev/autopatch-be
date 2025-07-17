import json
import boto3
import os

client = boto3.client("stepfunctions")
STATE_MACHINE_ARN = os.environ["RETRY_SINGLE_KB_STATE_MACHINE_ARN"]

def lambda_handler(event, context):
    try:
        # Hỗ trợ gọi từ API Gateway (string body) hoặc trực tiếp
        if "body" in event:
            body = event["body"]
            if isinstance(body, str):
                body = json.loads(body)
        else:
            body = event

        instance_id = body.get("instance_id")
        kb = body.get("kb")

        if not instance_id or not kb:
            return {
                "statusCode": 400,
                "body": json.dumps({ "error": "Missing instance_id or kb" })
            }

        input_payload = {
            "InstanceId": instance_id,
            "KB": kb
        }

        response = client.start_execution(
            stateMachineArn=STATE_MACHINE_ARN,
            input=json.dumps(input_payload)
        )

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Retry patch started",
                "executionArn": response["executionArn"]
            })
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({ "error": str(e) })
        }
