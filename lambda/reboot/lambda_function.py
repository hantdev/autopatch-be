import boto3
import json
import logging

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

ec2 = boto3.client('ec2')

def lambda_handler(event, context):
    logger.info("Received event: %s", json.dumps(event))
    
    instance_ids = event.get('instance_ids', [])
    
    if not instance_ids:
        logger.warning("No instance_ids provided in event.")
        return {
            'statusCode': 400,
            'message': 'No instance_ids provided'
        }
    
    try:
        logger.info(f"Sending reboot command to instances: {instance_ids}")
        response = ec2.reboot_instances(InstanceIds=instance_ids)
        logger.info(f"Reboot response: {response}")
        
        return {
            'statusCode': 200,
            'message': f"Reboot command sent to instances: {instance_ids}",
            'response': response
        }
    except Exception as e:
        logger.error(f"Error rebooting instances {instance_ids}: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'error': str(e)
        }
