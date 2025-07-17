import boto3
import os
import json
import logging
from datetime import datetime
from collections import defaultdict

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

sns = boto3.client('sns')
topic_arn = os.environ['SNS_TOPIC_ARN']

def lambda_handler(event, context):
    logger.info("Received event: %s", json.dumps(event))
    
    summary = event
    results = summary.get("results", [])
    overview = summary.get("overview", [])

    message_lines = []
    message_lines.append("📋 Patch Summary Report")
    message_lines.append(f"🕒 Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")

    for idx, instance in enumerate(results):
        instance_id = instance.get("InstanceId", "Unknown")
        installed = instance.get("installedKBs", [])
        available = instance.get("availableKBs", [])
        skipped = instance.get("skippedKBs", [])
        overview_items = overview[idx] if idx < len(overview) else []

        message_lines.append(f"🖥️ Instance: {instance_id}")

        if installed:
            message_lines.append(f"  ✅ Already Installed: {', '.join(installed)}")
        
        if available:
            message_lines.append(f"  📦 Available KBs (before patching): {', '.join(available)}")
        
        if skipped:
            message_lines.append(f"  ⚠️ Skipped KBs:")
            for s in skipped:
                message_lines.append(f"    - KB {s.get('KB')}: {s.get('status')}")
        
        if overview_items:
            message_lines.append(f"  📌 Patch Results:")
            for item in overview_items:
                message_lines.append(f"    - KB {item.get('KB')} → {item.get('newStatus')}")
        
        message_lines.append("")  # blank line between instances

    final_message = "\n".join(message_lines)
    logger.info("Final summary:\n%s", final_message)

    try:
        response = sns.publish(
            TopicArn=topic_arn,
            Subject="✅ Windows Patch Summary",
            Message=final_message
        )
        logger.info("SNS publish response: %s", response)
    except Exception as e:
        logger.error("Failed to publish to SNS: %s", str(e))
        raise

    return {
        "statusCode": 200,
        "body": "Patch summary SNS sent successfully."
    }
