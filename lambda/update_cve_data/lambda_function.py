import boto3
import json
import logging
import os
import requests
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])

def get_last_month_date_range():
    """Tính toán khoảng thời gian của tháng trước"""
    today = datetime.now()
    first_day_current_month = today.replace(day=1)
    last_day_previous_month = first_day_current_month - timedelta(days=1)
    first_day_previous_month = last_day_previous_month.replace(day=1)
    
    return first_day_previous_month, last_day_previous_month

def build_msrc_api_url(start_date, end_date, skip=0):
    """Tạo URL cho MSRC API"""
    base_url = "https://api.msrc.microsoft.com/sug/v2.0/sugodata/v2.0/vi-VN/affectedProduct"
    
    # Format dates for API
    start_str = start_date.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    end_str = end_date.strftime("%Y-%m-%dT%H:%M:%S.999Z")
    
    params = {
        '$orderBy': 'releaseDate desc',
        '$filter': f'(releaseDate ge {start_str}) and (releaseDate le {end_str})',
        '$skip': skip
    }
    
    # Build query string
    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
    return f"{base_url}?{query_string}"

def fetch_cve_data(start_date, end_date):
    """Tải dữ liệu CVE từ MSRC API"""
    all_data = []
    skip = 0
    batch_size = 500
    
    logger.info(f"Fetching CVE data from {start_date} to {end_date}")
    
    while True:
        try:
            url = build_msrc_api_url(start_date, end_date, skip)
            logger.info(f"Fetching data from: {url}")
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract the 'value' array which contains the actual CVE data
            if 'value' not in data or not data['value']:
                logger.info("No more data to fetch")
                break
                
            cve_records = data['value']
            all_data.extend(cve_records)
            logger.info(f"Fetched {len(cve_records)} records, total: {len(all_data)}")
            
            # Check if there's a next page
            if '@odata.nextLink' not in data:
                logger.info("No next page available")
                break
                
            skip += batch_size
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching data: {e}")
            break
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            break
    
    return all_data

def process_cve_data(cve_data):
    """Xử lý và chuẩn bị dữ liệu cho DynamoDB"""
    processed_items = {}
    processed_count = 0
    filtered_product_count = 0
    filtered_severity_count = 0
    
    # Define target Windows Server products
    target_products = [
        "Windows Server 2016 (Server Core installation)",
        "Windows Server 2019 (Server Core installation)", 
        "Windows Server 2022 (Server Core installation)",
        "Windows Server 2025 (Server Core installation)"
    ]
    
    # Define target severity levels
    target_severities = ["Critical", "Important"]
    
    logger.info(f"Processing {len(cve_data)} CVE records with filters:")
    logger.info(f"Target products: {target_products}")
    logger.info(f"Target severities: {target_severities}")
    
    for item in cve_data:
        try:
            # Extract relevant fields from the MSRC API response
            cve_number = item.get('cveNumber', '')
            product = item.get('product', '')
            severity = item.get('severity', '')
            impact = item.get('impact', '')
            release_date = item.get('releaseDate', '')
            base_score = item.get('baseScore', '')
            temporal_score = item.get('temporalScore', '')
            vector_string = item.get('vectorString', '')
            
            # Extract KB article information
            kb_articles = item.get('kbArticles', [])
            kb_info = {}
            if kb_articles and len(kb_articles) > 0:
                kb_info = kb_articles[0]  # Take the first KB article
            
            if not cve_number or not product:
                logger.warning(f"Skipping item with missing CVE number or product: {item}")
                continue
            
            # Filter for target products
            if product not in target_products:
                filtered_product_count += 1
                logger.debug(f"Skipping non-target product: {product}")
                continue
            
            # Filter for target severity levels
            if severity not in target_severities:
                filtered_severity_count += 1
                logger.debug(f"Skipping non-target severity: {severity}")
                continue
                
            # Create DynamoDB item
            pk = f"OS#{product}"
            sk = f"CVE#{cve_number}"
            
            # Use composite key to avoid duplicates
            unique_key = f"{pk}#{sk}"
            
            # Parse release date
            try:
                parsed_date = datetime.fromisoformat(release_date.replace('Z', '+00:00'))
                ttl = int((parsed_date + timedelta(days=365)).timestamp())  # TTL 1 năm
            except:
                ttl = int((datetime.now() + timedelta(days=365)).timestamp())
            
            db_item = {
                'PK': pk,
                'SK': sk,
                'GSI1PK': f"DATE#{parsed_date.strftime('%Y-%m')}",
                'GSI1SK': f"CVE#{cve_number}",
                'cveNumber': cve_number,
                'product': product,
                'severity': severity,
                'impact': impact,
                'releaseDate': release_date,
                'baseScore': base_score,
                'temporalScore': temporal_score,
                'vectorString': vector_string,
                'kbArticle': kb_info.get('articleName', ''),
                'kbUrl': kb_info.get('articleUrl', ''),
                'downloadUrl': kb_info.get('downloadUrl', ''),
                'rebootRequired': kb_info.get('rebootRequired', ''),
                'fixedBuildNumber': kb_info.get('fixedBuildNumber', ''),
                'TTL': ttl,
                'lastUpdated': datetime.now().isoformat() + 'Z'
            }
            
            # Use unique key to avoid duplicates
            processed_items[unique_key] = db_item
            processed_count += 1
            
        except Exception as e:
            logger.error(f"Error processing item {item}: {e}")
            continue
    
    logger.info(f"Filtering summary: {len(cve_data)} total records, {filtered_product_count} filtered by product, {filtered_severity_count} filtered by severity, {processed_count} processed")
    
    return list(processed_items.values())

def save_to_dynamodb(items):
    """Lưu dữ liệu vào DynamoDB"""
    saved_count = 0
    error_count = 0
    
    # Process in batches of 25 (DynamoDB batch write limit)
    batch_size = 25
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        
        try:
            with table.batch_writer() as batch_writer:
                for item in batch:
                    batch_writer.put_item(Item=item)
                    saved_count += 1
                    
        except Exception as e:
            logger.error(f"Error saving batch {i//batch_size + 1}: {e}")
            error_count += len(batch)
    
    return saved_count, error_count

def lambda_handler(event, context):
    """Main Lambda handler for previous month CVE data update (Windows Server Core only, Critical/Important severity)"""
    logger.info("=== START update_cve_data Lambda ===")
    logger.info("Filtering for Windows Server Core installations (2016, 2019, 2022, 2025) with Critical/Important severity")
    logger.info("Processing previous month data")
    
    try:
        # Get date range for last month
        start_date, end_date = get_last_month_date_range()
        
        logger.info(f"Processing data for period: {start_date} to {end_date}")
        
        # Fetch CVE data from MSRC API
        cve_data = fetch_cve_data(start_date, end_date)
        
        if not cve_data:
            logger.warning("No CVE data found for the specified period")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'No CVE data found for the specified period',
                    'period': {
                        'start': start_date.isoformat(),
                        'end': end_date.isoformat()
                    }
                })
            }
        
        logger.info(f"Fetched {len(cve_data)} CVE records")
        
        # Process data for DynamoDB
        processed_items = process_cve_data(cve_data)
        
        logger.info(f"Processed {len(processed_items)} items for DynamoDB (after filtering)")
        
        # Save to DynamoDB
        saved_count, error_count = save_to_dynamodb(processed_items)
        
        logger.info(f"Saved {saved_count} items to DynamoDB, {error_count} errors")
        
        # Return summary
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Previous month CVE data updated successfully (filtered for Windows Server Core)',
                'period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'summary': {
                    'totalFetched': len(cve_data),
                    'totalProcessed': len(processed_items),
                    'savedToDynamoDB': saved_count,
                    'errors': error_count,
                    'filters': {
                        'products': ['Windows Server 2016/2019/2022/2025 (Server Core installation)'],
                        'severities': ['Critical', 'Important']
                    }
                }
            })
        }
        
    except Exception as e:
        logger.error(f"ERROR in update_cve_data Lambda: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        } 