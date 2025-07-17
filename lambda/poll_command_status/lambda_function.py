import boto3
import logging
import json

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ssm = boto3.client('ssm')

def lambda_handler(event, context):
    logger.info(f"Received event: {event}")

    instance_id = event.get("InstanceId")
    command_id = event.get("CommandId")

    if not instance_id or not command_id:
        return {
            "Status": "Failed",
            "ErrorMessage": "Missing InstanceId or CommandId"
        }

    try:
        response = ssm.get_command_invocation(
            CommandId=command_id,
            InstanceId=instance_id,
            PluginName='aws:runPowerShellScript'
        )

        status = response.get("Status")
        stdout = response.get("StandardOutputContent", "")
        stderr = response.get("StandardErrorContent", "")
        response_code = response.get("ResponseCode")

        logger.info(f"SSM Status: {status}, ExitCode: {response_code}")
        logger.info(f"Output: {stdout}")
        logger.info(f"Error: {stderr}")

        if status in ["InProgress", "Pending", "Delayed"]:
            return {
                "Status": "InProgress",
                "RebootRequired": False,
                "Output": stdout.strip(),
                "ErrorOutput": stderr.strip()
            }

        # Parse output on success or general failure
        patch_success = "PATCH_SUCCESS" in stdout
        reboot_required = "REBOOT_REQUIRED" in stdout

        if patch_success:
            return {
                "Status": "Success",
                "RebootRequired": reboot_required,
                "Output": stdout.strip(),
                "ErrorOutput": stderr.strip()
            }
        else:
            return {
                "Status": "Failed",
                "ExitCode": response_code,
                "Output": stdout.strip(),
                "ErrorOutput": stderr.strip()
            }

    except Exception as e:
        logger.error(f"Exception: {str(e)}")
        return {
            "Status": "Failed",
            "RebootRequired": False,
            "ErrorMessage": str(e)
        }
