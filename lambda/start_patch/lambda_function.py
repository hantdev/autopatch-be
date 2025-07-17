import json
import boto3
import os

client = boto3.client("stepfunctions")
STATE_MACHINE_ARN = os.environ["PATCH_STATE_MACHINE_ARN"]

def lambda_handler(event, context):
    try:
        # Xử lý cả gọi trực tiếp & qua API Gateway
        if "body" in event:
            body = event["body"]
            if isinstance(body, str):
                body = json.loads(body)
        else:
            body = event

        instance_ids = body.get("instance_ids")
        if not instance_ids:
            return {
                "statusCode": 400,
                "body": json.dumps({ "error": "Missing instance_ids" })
            }

        response = client.start_execution(
            stateMachineArn=STATE_MACHINE_ARN,
            input=json.dumps({ "instance_ids": instance_ids })
        )

        return {
            "statusCode": 200,
            "body": json.dumps({ "executionArn": response["executionArn"] })
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({ "error": str(e) })
        }
