import boto3
import os
import json
import logging
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
ec2 = boto3.client('ec2')

DDB_TABLE_NAME = os.environ['TABLE_NAME']
table = dynamodb.Table(DDB_TABLE_NAME)

def lambda_handler(event, context):
    logger.info("Started getTargetInstancesAndKBsLambda with event: %s", json.dumps(event))

    instance_ids = event.get('instance_ids', [])
    if not instance_ids or not isinstance(instance_ids, list):
        return {
            "status": "Failed",
            "message": "Missing or invalid 'instance_ids' input"
        }

    results = []

    for instance_id in instance_ids:
        os_name = get_os_from_instance(instance_id)
        if not os_name:
            logger.warning(f"Could not determine OS for instance {instance_id}")
            continue

        os_key = f"OS#{os_name}"
        kb_list = get_kbs_from_dynamodb(os_key)
        kb_list = list(set(kb_list))  # Remove duplicates

        results.append({
            "InstanceId": instance_id,
            "OS": os_name,
            "KBs": kb_list
        })

    return {
        "status": "Success",
        "results": results
    }

def get_os_from_instance(instance_id):
    try:
        response = ec2.describe_instances(InstanceIds=[instance_id])
        for res in response['Reservations']:
            for inst in res['Instances']:
                os_tag = next((tag['Value'] for tag in inst.get('Tags', []) if tag['Key'] == 'OS'), None)
                return os_tag
        return None
    except ClientError as e:
        logger.error(f"EC2 describe_instances error: {e}")
        return None

def get_kbs_from_dynamodb(os_key):
    try:
        response = table.query(
            KeyConditionExpression=Key('PK').eq(os_key)
        )
        items = response.get('Items', [])
        return [item['kbArticle'] for item in items if 'kbArticle' in item]
    except ClientError as e:
        logger.error(f"DynamoDB query error: {e}")
        return []
