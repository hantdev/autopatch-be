# CVE Data Update System Setup

Hệ thống tự động cập nhật dữ liệu CVE từ Microsoft Security Response Center (MSRC) vào DynamoDB mỗi đầu tháng.

## Kiến trúc hệ thống

```
EventBridge (Cron) → Lambda Function → MSRC API → DynamoDB
```

### Components:
1. **EventBridge Rule**: Chạy mỗi đầu tháng lúc 6 AM UTC
2. **Lambda Function**: Tải và xử lý dữ liệu CVE
3. **DynamoDB Table**: Lưu trữ dữ liệu CVE
4. **IAM Role**: Permissions cho Lambda

## Deployment Steps

### 1. Deploy DynamoDB Table

```bash
# Deploy DynamoDB table
aws cloudformation deploy \
  --template-file dynamodb/cve-table.json \
  --stack-name vpbank-cve-table \
  --capabilities CAPABILITY_IAM
```

### 2. Deploy Lambda Function

#### 2.1. Package Lambda code
```bash
cd lambda/update_cve_data
pip install -r requirements.txt -t .
zip -r lambda_function.zip .
```

#### 2.2. Create Lambda function
```bash
aws lambda create-function \
  --function-name updateCVEDataLambda \
  --runtime python3.9 \
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/cve-update-lambda-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://lambda_function.zip \
  --timeout 300 \
  --memory-size 512 \
  --environment Variables='{TABLE_NAME=vpbank-cve-data}'
```

### 3. Deploy EventBridge Rule

```bash
aws events put-rule \
  --name cve-monthly-update \
  --schedule-expression "cron(0 6 1 * ? *)" \
  --description "Trigger CVE data update on the first day of each month"
```

```bash
aws events put-targets \
  --rule cve-monthly-update \
  --targets "Id"="update-cve-data-lambda","Arn"="arn:aws:lambda:us-east-1:YOUR_ACCOUNT_ID:function:updateCVEDataLambda"
```

### 4. Deploy toàn bộ bằng CloudFormation

```bash
aws cloudformation deploy \
  --template-file cloudformation/cve-update-system.yaml \
  --stack-name vpbank-cve-update-system \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides Environment=prod
```

## Cấu hình

### Environment Variables
- `TABLE_NAME`: Tên DynamoDB table (tự động set)

### Cron Expression
- `cron(0 6 1 * ? *)`: Chạy lúc 6 AM UTC ngày đầu tháng

### DynamoDB Schema
```json
{
  "PK": "OS#Windows Server 2016",
  "SK": "CVE#CVE-2023-1234",
  "GSI1PK": "DATE#2023-06",
  "GSI1SK": "CVE#CVE-2023-1234",
  "cveId": "CVE-2023-1234",
  "product": "Windows Server 2016",
  "severity": "High",
  "impact": "Remote code execution",
  "releaseDate": "2023-06-15T00:00:00Z",
  "kbArticle": "KB123456",
  "TTL": 1704067200,
  "lastUpdated": "2023-12-01T06:00:00Z"
}
```

## Monitoring

### CloudWatch Logs
- Log Group: `/aws/lambda/updateCVEDataLambda`
- Retention: 30 days

### Metrics to monitor:
- Lambda execution time
- DynamoDB write capacity
- API call success rate
- Error rates

## Testing

### 1. Test Lambda manually
```bash
aws lambda invoke \
  --function-name updateCVEDataLambda \
  --payload '{}' \
  response.json
```

### 2. Check DynamoDB data
```bash
aws dynamodb scan \
  --table-name vpbank-cve-data \
  --max-items 10
```

### 3. Test EventBridge rule
```bash
aws events test-event-pattern \
  --event-pattern '{"source":["aws.events"],"detail-type":["Scheduled Event"]}' \
  --event '{"source":"aws.events","detail-type":"Scheduled Event","detail":{"region":"us-east-1"}}'
```

## Troubleshooting

### Common Issues:

#### 1. Lambda timeout
- Tăng timeout lên 300 seconds
- Tăng memory size lên 1024 MB

#### 2. DynamoDB throttling
- Kiểm tra write capacity
- Implement exponential backoff

#### 3. API rate limiting
- Implement retry logic
- Add delays between requests

#### 4. Network issues
- Kiểm tra VPC configuration
- Ensure Lambda has internet access

### Debug Commands:
```bash
# Check Lambda logs
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/updateCVEDataLambda"

# Get recent logs
aws logs filter-log-events \
  --log-group-name "/aws/lambda/updateCVEDataLambda" \
  --start-time $(date -d '1 hour ago' +%s)000

# Check DynamoDB table
aws dynamodb describe-table --table-name vpbank-cve-data
```

## Cost Optimization

### DynamoDB
- Use PAY_PER_REQUEST billing
- Set TTL to auto-delete old data
- Use GSI sparingly

### Lambda
- Optimize memory allocation
- Use appropriate timeout
- Monitor execution time

### EventBridge
- Free tier: 1 million events/month
- Minimal cost for monthly cron jobs

## Security

### IAM Permissions
- Least privilege principle
- Only necessary DynamoDB permissions
- No admin access

### Data Protection
- Encrypt data at rest
- Use HTTPS for API calls
- Implement proper error handling

## Maintenance

### Monthly Tasks:
1. Review CloudWatch logs
2. Check DynamoDB table size
3. Monitor Lambda performance
4. Update dependencies if needed

### Quarterly Tasks:
1. Review IAM permissions
2. Update Lambda runtime
3. Optimize performance
4. Review cost optimization 