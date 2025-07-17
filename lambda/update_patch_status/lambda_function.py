import boto3
import os
import logging
from datetime import datetime, timedelta

# Setup logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Init DynamoDB
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['PATCH_TABLE'])

def lambda_handler(event, context):
    logger.info(f"Received event: {event}")

    instance_id = event.get("InstanceId")
    kb = event.get("KB")
    status = event.get("Status")
    reboot_required = event.get("RebootRequired", False)

    if not instance_id or not kb or not status:
        logger.error("Missing InstanceId, KB, or Status")
        return {"status": "error", "message": "Missing required fields"}

    ttl = int((datetime.utcnow() + timedelta(minutes=5)).timestamp())

    try:
        logger.info(f"Updating patch status: InstanceId={instance_id}, KB={kb}, Status={status}, TTL={ttl}")
        table.update_item(
            Key={
                "PK": f"PATCH#{instance_id}",
                "SK": f"KB#{kb}"
            },
            UpdateExpression="SET #s = :s, UpdatedAt = :u, #ttl = :ttl, RebootRequired = :r",
            ExpressionAttributeNames={
                "#s": "Status",
                "#ttl": "TTL"
            },
            ExpressionAttributeValues={
                ":s": status,
                ":u": datetime.utcnow().isoformat(),
                ":ttl": ttl,
                ":r": reboot_required
            }
        )

        logger.info(f"Patch status updated successfully: {instance_id} | {kb} -> {status}")
        return {
            "status": "ok",
            "InstanceId": instance_id,
            "KB": kb,
            "newStatus": status
        }

    except Exception as e:
        logger.error(f"Error updating patch status for {instance_id} | {kb}: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }
