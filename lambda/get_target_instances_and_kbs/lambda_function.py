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
    
    os_versions = event.get('os_versions')
    if not os_versions:
        return {"status": "No os_versions provided"}

    results = []

    for os_name_raw in os_versions:
        os_name = f"OS#{os_name_raw}" if not os_name_raw.startswith("OS#") else os_name_raw

        # Fetch KBs from DynamoDB
        kb_list = get_kbs_from_dynamodb(os_name)
        kb_list = list(set(kb_list))

        if not kb_list:
            logger.warning(f"No KBs found for {os_name}")
            continue

        # Find EC2 instances
        instances = get_target_instances(os_name)

        if not instances:
            logger.warning(f"No instances found for {os_name}")
            continue

        for instance_id in instances:
            results.append({
                "InstanceId": instance_id,
                "OS": os_name.replace("OS#",""),
                "KBs": kb_list
            })

    return {
        "status": "Success",
        "results": results
    }

def get_kbs_from_dynamodb(os_name):
    try:
        response = table.query(
            KeyConditionExpression=Key('PK').eq(os_name)
        )
        items = response.get('Items', [])
        return [item['kb'] for item in items if 'kb' in item]
    except ClientError as e:
        logger.error(f"DynamoDB query error: {e}")
        return []

def get_target_instances(os_name):
    try:
        os_name_clean = os_name.replace("OS#", "").strip()
        response = ec2.describe_instances(
            Filters=[
                {'Name': 'instance-state-name', 'Values': ['running']}
            ]
        )
        instance_ids = []
        for res in response['Reservations']:
            for inst in res['Instances']:
                os_tag = next((tag['Value'] for tag in inst.get('Tags', []) if tag['Key'] == 'OS'), None)
                if os_tag == os_name_clean:
                    instance_ids.append(inst['InstanceId'])
        return instance_ids
    except ClientError as e:
        logger.error(f"EC2 describe_instances error: {e}")
        return []
