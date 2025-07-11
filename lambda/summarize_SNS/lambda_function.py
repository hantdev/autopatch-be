import boto3
import os
import json
import logging
from datetime import datetime

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

sns = boto3.client('sns')
topic_arn = os.environ['SNS_TOPIC_ARN']

def lambda_handler(event, context):
    logger.info("Received event: %s", json.dumps(event))
    
    summary = {
        'timestamp': datetime.utcnow().isoformat(),
        'summary': event
    }
    
    message = json.dumps(summary, indent=2)
    logger.info(f"Prepared summary message: {message}")
    
    try:
        response = sns.publish(
            TopicArn=topic_arn,
            Subject="Patch Flow Summary",
            Message=message
        )
        logger.info(f"Successfully published summary to SNS. MessageId: {response.get('MessageId')}")
        
        return {
            'statusCode': 200,
            'message': 'Summary sent to SNS',
            'summary': summary
        }
    except Exception as e:
        logger.error(f"Error publishing summary to SNS: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'error': str(e)
        }
