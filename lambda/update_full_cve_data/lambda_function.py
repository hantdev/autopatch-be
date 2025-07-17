import boto3
import json
import logging
import os
import requests
from datetime import datetime, timedelta
from botocore.exceptions import ClientError

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])

def get_os_name_from_instance(instance_id):
    ec2 = boto3.client('ec2')
    try:
        response = ec2.describe_instances(InstanceIds=[instance_id])
        tags = response['Reservations'][0]['Instances'][0].get('Tags', [])
        for tag in tags:
            if tag['Key'] == 'OS':
                return tag['Value']
    except ClientError as e:
        logger.error(f"Error fetching EC2 instance tags for {instance_id}: {e}")
    return None

def build_msrc_api_url(start_date, end_date, skip=0):
    base_url = "https://api.msrc.microsoft.com/sug/v2.0/sugodata/v2.0/vi-VN/affectedProduct"
    start_str = start_date.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    end_str = end_date.strftime("%Y-%m-%dT%H:%M:%S.999Z")

    params = {
        '$orderBy': 'releaseDate desc',
        '$filter': f'(releaseDate ge {start_str}) and (releaseDate le {end_str})',
        '$skip': skip
    }

    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
    return f"{base_url}?{query_string}"

def fetch_cve_data_for_month(start_date, end_date):
    all_data = []
    skip = 0
    batch_size = 500

    while True:
        try:
            url = build_msrc_api_url(start_date, end_date, skip)
            logger.info(f"Fetching data from: {url}")
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()

            value = data.get('value', [])
            if not value:
                logger.info("No more CVE records from API.")
                break

            all_data.extend(value)
            logger.info(f"Fetched {len(value)} records, total so far: {len(all_data)}")

            # Nếu không còn trang tiếp theo → dừng
            if '@odata.nextLink' not in data:
                break

            # Nếu còn, skip sang trang sau
            skip += batch_size
            import time
            time.sleep(0.1)

        except Exception as e:
            logger.error(f"Error fetching CVE data: {e}")
            break

    return all_data

def process_cve_data(cve_data, os_name_filter=None):
    processed_items = {}
    target_severities = ["Critical", "Important"]

    for item in cve_data:
        product = item.get('product', '')
        severity = item.get('severity', '')

        if os_name_filter and product != os_name_filter:
            continue
        if severity not in target_severities:
            continue

        try:
            cve_number = item.get('cveNumber', '')
            if not cve_number or not product:
                continue

            pk = f"OS#{product}"
            sk = f"CVE#{cve_number}"
            unique_key = f"{pk}#{sk}"

            release_date = item.get('releaseDate', '')
            try:
                parsed_date = datetime.fromisoformat(release_date.replace('Z', '+00:00'))
                ttl = int((parsed_date + timedelta(days=365)).timestamp())
            except:
                ttl = int((datetime.utcnow() + timedelta(days=365)).timestamp())

            kb = item.get('kbArticles', [{}])[0]
            db_item = {
                'PK': pk,
                'SK': sk,
                'GSI1PK': f"DATE#{parsed_date.strftime('%Y-%m')}",
                'GSI1SK': f"CVE#{cve_number}",
                'cveNumber': cve_number,
                'product': product,
                'severity': severity,
                'impact': item.get('impact', ''),
                'releaseDate': release_date,
                'baseScore': item.get('baseScore', ''),
                'temporalScore': item.get('temporalScore', ''),
                'vectorString': item.get('vectorString', ''),
                'cweList': item.get('cweList', []),
                'architecture': item.get('architecture', ''),
                'productFamily': item.get('productFamily', ''),
                'kbArticle': kb.get('articleName', ''),
                'kbUrl': kb.get('articleUrl', ''),
                'downloadUrl': kb.get('downloadUrl', ''),
                'rebootRequired': kb.get('rebootRequired', ''),
                'fixedBuildNumber': kb.get('fixedBuildNumber', ''),
                'supercedence': kb.get('supercedence', ''),
                'TTL': ttl,
                'lastUpdated': datetime.utcnow().isoformat() + 'Z'
            }

            processed_items[unique_key] = db_item

        except Exception as e:
            logger.warning(f"Error processing CVE: {e}")
            continue

    return list(processed_items.values())

def save_to_dynamodb(items):
    saved_count = 0
    error_count = 0
    batch_size = 25

    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        for item in batch:
            try:
                table.put_item(Item=item)
                saved_count += 1
            except Exception as e:
                logger.error(f"Error saving item: {e}")
                error_count += 1
                continue

    return saved_count, error_count

def lambda_handler(event, context):
    logger.info("=== START Lambda: update_cve_for_instances ===")
    instance_ids = event.get('instanceIds', [])

    if not instance_ids:
        return {'statusCode': 400, 'body': json.dumps({'error': 'Missing instanceIds array in input'})}

    now = datetime.utcnow()
    start_date = datetime(now.year, now.month, 1)
    end_date = now

    summary_list = []

    for instance_id in instance_ids:
        logger.info(f"Processing instance: {instance_id}")
        try:
            os_name = get_os_name_from_instance(instance_id)
            if not os_name:
                summary_list.append({
                    'instanceId': instance_id,
                    'status': 'FAILED',
                    'reason': 'OS tag not found'
                })
                continue

            cve_data = fetch_cve_data_for_month(start_date, end_date)
            processed_items = process_cve_data(cve_data, os_name_filter=os_name)
            saved_count, error_count = save_to_dynamodb(processed_items)

            summary_list.append({
                'instanceId': instance_id,
                'osName': os_name,
                'totalFetched': len(cve_data),
                'filteredProcessed': len(processed_items),
                'savedToDynamoDB': saved_count,
                'errors': error_count,
                'status': 'COMPLETED'
            })

        except Exception as e:
            logger.error(f"Error processing instance {instance_id}: {e}")
            summary_list.append({
                'instanceId': instance_id,
                'status': 'FAILED',
                'reason': str(e)
            })

    return {
        'statusCode': 200,
        'body': json.dumps({
            'summary': summary_list,
            'timeRange': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            }
        })
    }
