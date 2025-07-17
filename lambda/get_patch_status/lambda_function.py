import boto3
import os
import json
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ['PATCH_TABLE'])

def lambda_handler(event, context):
    instance_id = event.get("instance_id")
    
    if not instance_id:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing instance_id"})
        }

    pk = f"PATCH#{instance_id}"

    try:
        response = table.query(
            KeyConditionExpression=Key("PK").eq(pk)
        )

        items = response.get("Items", [])

        total = len(items)
        completed = sum(1 for i in items if i.get("Status") in ["Success", "Already Installed", "Failed", "Not Available"])
        percentage = round((completed / total) * 100) if total else 0

        result = {
            "instance_id": instance_id,
            "total": total,
            "completed": completed,
            "percentage": percentage,
            "details": [
                {
                    "KB": i.get("SK", "").replace("KB#", ""),
                    "Status": i.get("Status", "Unknown"),
                    "LastUpdated": i.get("UpdatedAt", "-"),
                    "RebootRequired": i.get("RebootRequired", False)
                }
                for i in sorted(items, key=lambda x: x.get("UpdatedAt", ""))
            ]
        }

        return {
            "statusCode": 200,
            "body": json.dumps(result)
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }