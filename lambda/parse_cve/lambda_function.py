import boto3
import csv
import io
import os
import logging

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])

def lambda_handler(event, context):
    logger.info("=== START fetchCVELambda ===")
    
    try:
        # Lấy OS versions từ event
        os_versions = event['os_versions']
        logger.info(f"OS versions to filter: {os_versions}")

        # Thông tin S3 file
        bucket = os.environ['BUCKET_NAME']
        key = os.environ['CSV_KEY']
        logger.info(f"Reading CSV from s3://{bucket}/{key}")

        # Tải file CSV từ S3
        obj = s3.get_object(Bucket=bucket, Key=key)
        csv_content = obj['Body'].read().decode('utf-8')

        reader = csv.DictReader(io.StringIO(csv_content))
        saved = []
        total_rows = 0

        # Duyệt từng row trong CSV
        for row in reader:
            total_rows += 1

            product = row.get('Product', '')
            cve_id = row.get('Details', '')
            kb = row.get('Article', '')
            severity = row.get('Max Severity', '')
            description = row.get('Impact', '')
            published_date = row.get('Release date', '')

            logger.debug(f"Row {total_rows}: product={product}, cve_id={cve_id}, kb={kb}")

            if product in os_versions and kb:
                pk = f"OS#{product}"
                sk = f"CVE#{cve_id}"

                item = {
                    'PK': pk,
                    'SK': sk,
                    'kb': kb,
                    'severity': severity,
                    'description': description,
                    'publishedDate': published_date
                }

                table.put_item(Item=item)
                saved.append(f"{cve_id} ({product})")
                logger.info(f"Saved to DynamoDB: {pk} | {sk}")

        logger.info(f"Total rows parsed: {total_rows}")
        logger.info(f"Total items saved: {len(saved)}")
        logger.info("=== END fetchCVELambda ===")

        return {
            'statusCode': 200,
            'saved': saved
        }
    
    except Exception as e:
        logger.error(f"ERROR in fetchCVELambda: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'error': str(e)
        }