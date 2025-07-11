import boto3
import os
import json
import logging
from datetime import datetime
from collections import defaultdict

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# DynamoDB client
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])

def lambda_handler(event, context):
    logger.info("Received event: %s", json.dumps(event))
    
    # Handle input type: list or wrapped object
    if isinstance(event, list):
        results = event
    else:
        results = event.get('results', [])

    if not results:
        logger.warning("No results provided in event.")
        return {
            'statusCode': 400,
            'message': 'No results to save'
        }
    
    saved_items = []

    for r in results:
        instance_id = r.get('InstanceId')
        timestamp = datetime.utcnow().isoformat()
        output_text = r.get('Output', '')

        # Prefer direct RebootRequired field if exists
        reboot_required = r.get('RebootRequired')

        # Fallback parse from output string
        if reboot_required is None:
            try:
                # Try parse structured JSON output
                parsed = json.loads(output_text)
                reboot_required = parsed.get('RebootRequired')
            except json.JSONDecodeError:
                # Fallback parse text lines
                if "RebootRequired: True" in output_text:
                    reboot_required = True
                elif "RebootRequired: False" in output_text:
                    reboot_required = False

        item = {
            'InstanceId': instance_id,  # Partition key
            'Patch timestamp': timestamp,  # Sort key
            'CommandId': r.get('CommandId'),
            'Status': r.get('Status'),
            'RebootRequired': reboot_required,
            'Output': output_text
        }
        
        logger.info(f"Saving item to DynamoDB: {json.dumps(item)}")
        table.put_item(Item=item)
        saved_items.append(item)
    
    logger.info(f"Successfully saved {len(saved_items)} items to DynamoDB.")

    # Group output by InstanceId for clarity
    grouped_items = defaultdict(list)
    for item in saved_items:
        grouped_items[item['InstanceId']].append(item)

    # Convert defaultdict to dict for JSON serialization
    grouped_items = dict(grouped_items)
    
    return {
        'statusCode': 200,
        'message': f"Saved {len(saved_items)} patch results",
        'items_grouped_by_instance': grouped_items
    }
