import boto3
import json
import logging
import time
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ssm = boto3.client('ssm')

POWERSHELL_PATCH_SCRIPT = """
$kb = '{kb}'
Write-Host "Installing patch: $kb"
Install-WindowsUpdate -KBArticleID $kb -AcceptAll -AutoReboot

# Check if reboot required
$pendingReboot = (Get-ItemProperty "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Component Based Servicing\\RebootPending" -ErrorAction SilentlyContinue) -ne $null

# Output structured JSON
$result = @{
    KB = $kb
    RebootRequired = $pendingReboot
}
$result | ConvertTo-Json
"""

def lambda_handler(event, context):
    logger.info("Started runPatchCommandLambda with event: %s", json.dumps(event))
    
    instance_id = event.get('InstanceId')
    kb = event.get('KB')

    if not instance_id or not kb:
        return {"status": "Missing InstanceId or KB in input"}

    script = POWERSHELL_PATCH_SCRIPT.format(kb=kb)
    
    try:
        response = ssm.send_command(
            InstanceIds=[instance_id],
            DocumentName='AWS-RunPowerShellScript',
            Parameters={'commands': [script]},
            TimeoutSeconds=600
        )
        command_id = response['Command']['CommandId']
        logger.info(f"Command {command_id} sent to {instance_id}")

        # Optional: Wait briefly before returning (polling should be in Step Functions)
        time.sleep(2)

        return {
            "InstanceId": instance_id,
            "KB": kb,
            "CommandId": command_id,
            "Status": "Sent"
        }

    except ClientError as e:
        logger.error(f"SSM send_command error: {e}")
        return {
            "InstanceId": instance_id,
            "KB": kb,
            "Error": str(e)
        }
