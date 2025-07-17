import boto3
import logging
import json

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ssm = boto3.client('ssm')

POWERSHELL_SCRIPT = '''
$kb = "{kb}"

try {{
    Install-WindowsUpdate -KBArticleID $kb -AcceptAll -IgnoreReboot -ErrorAction Stop -Verbose -Confirm:$false
    Write-Output "PATCH_SUCCESS"

    if (Test-Path "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\WindowsUpdate\\Auto Update\\RebootRequired") {{
        Write-Output "REBOOT_REQUIRED"
    }}
}} catch {{
    Write-Error "PATCH_FAILED: $_"
    exit 1
}}
'''

def lambda_handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")

    instance_id = event.get("InstanceId")
    kb = event.get("KB")

    if not instance_id or not kb:
        return {
            "status": "error",
            "message": "Missing InstanceId or KB"
        }

    try:
        script = POWERSHELL_SCRIPT.format(kb=kb)

        logger.info(f"Sending patch command to {instance_id} for {kb}")

        response = ssm.send_command(
            InstanceIds=[instance_id],
            DocumentName="AWS-RunPowerShellScript",
            Parameters={'commands': [script]},
            TimeoutSeconds=900,
        )

        command_id = response['Command']['CommandId']
        logger.info(f"Command sent: {command_id}")

        return {
            "status": "ok",
            "InstanceId": instance_id,
            "KB": kb,
            "CommandId": command_id
        }

    except Exception as e:
        logger.error(f"Error sending patch command: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }
