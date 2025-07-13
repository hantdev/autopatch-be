import boto3
import os
import json
from boto3.dynamodb.conditions import Key, Attr

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])

def lambda_handler(event, context):
    os_versions = event.get("os_versions", [])
    if not os_versions:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing os_versions in input"})
        }

    results = []

    for os_version in os_versions:
        pk_value = f"OS#{os_version.split(' (')[0]}"  # Loại bỏ phần '(Server Core installation)'
        response = table.query(
            KeyConditionExpression=Key('PK').eq(pk_value)
        )
        
        for item in response.get('Items', []):
            result_item = {
                "PK": item.get("PK", ""),
                "SK": item.get("SK", ""),
                "baseScore": item.get("baseScore", ""),
                "cveNumber": item.get("cveNumber", ""),
                "severity": item.get("severity", ""),
                "impact": item.get("impact", ""),
                "kbArticle": item.get("kbArticle", ""),
                "releaseDate": item.get("releaseDate", "")
            }
            results.append(result_item)

    return {
        "statusCode": 200,
        "body": json.dumps(results)
    }
