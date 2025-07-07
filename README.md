# AutoPatch Backend

Repository for Lambda functions (Python), Step Functions, API Gateway, DynamoDB schema, Systems Manager setup, CloudWatch Logs, and S3 log storage for AutoPatch system.

## Folder structure

- lambda/                             # AWS Lambda functions
  - fetch_os_info/                    # fetchOSInfoLambda: lấy OS version từ SSM
  - fetch_cve/                        # fetchCVELambda: gọi Microsoft API tìm CVE theo OS
  - save_db/                          # saveDBLambda: lưu OS-CVE-KB mapping vào DynamoDB
  - run_patch/                        # runPatchLambda: gọi SSM RunCommand để patch
  - summarize_report/                 # summarizeReportLambda: tổng hợp kết quả từ CloudWatch
  - trigger_reboot/                   # triggerRebootLambda: reboot máy chủ ngay lập tức
- stepfunctions/                      # Step Functions state machine definitions (JSON/YAML)
- dynamodb/                           # DynamoDB table schema & design docs
- ssm/                                # Systems Manager setup
  - inventory/                        # Inventory collection setup scripts
  - run_command/                      # RunCommand documents/scripts
  - maintenance_window/               # Maintenance Window configuration
- cloudwatch/                         # CloudWatch setup
  - log_groups/                       # Log group & retention policy setup
  - metrics_alarms/                   # Metrics, alarms, and dashboards (if any)
- ec2/                                # EC2 Windows Server setup scripts, AMI notes
- s3/                                 # S3 bucket policies for log archive