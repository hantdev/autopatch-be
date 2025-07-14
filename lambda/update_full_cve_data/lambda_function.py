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

def get_monthly_periods():
    """Tạo danh sách các tháng từ 2025-01 đến 2025-06"""
    periods = []
    start_date = datetime(2025, 1, 1)
    end_date = datetime(2025, 6, 30, 23, 59, 59)
    
    current_date = start_date
    while current_date <= end_date:
        # Tính ngày cuối tháng
        if current_date.month == 12:
            next_month = current_date.replace(year=current_date.year + 1, month=1, day=1)
        else:
            next_month = current_date.replace(month=current_date.month + 1, day=1)
        
        period_end = next_month - timedelta(days=1)
        period_end = period_end.replace(hour=23, minute=59, second=59)
        
        # Đảm bảo không vượt quá tháng 6/2025
        if period_end > end_date:
            period_end = end_date
        
        periods.append((current_date, period_end))
        
        # Chuyển sang tháng tiếp theo
        current_date = next_month
    
    return periods

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

def fetch_cve_data_for_month(start_date, end_date, max_records=500):
    """Tải dữ liệu CVE từ MSRC API cho một tháng cụ thể"""
    all_data = []
    skip = 0
    batch_size = 500
    
    logger.info(f"Fetching CVE data for {start_date.strftime('%Y-%m')}: {start_date} to {end_date}")
    
    while len(all_data) < max_records:
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
            
            # Add a small delay to avoid overwhelming the API
            import time
            time.sleep(0.1)
            
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
            cwe_list = item.get('cweList', [])
            architecture = item.get('architecture', '')
            product_family = item.get('productFamily', '')
            
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
                'cweList': cwe_list,
                'architecture': architecture,
                'productFamily': product_family,
                'kbArticle': kb_info.get('articleName', ''),
                'kbUrl': kb_info.get('articleUrl', ''),
                'downloadUrl': kb_info.get('downloadUrl', ''),
                'rebootRequired': kb_info.get('rebootRequired', ''),
                'fixedBuildNumber': kb_info.get('fixedBuildNumber', ''),
                'supercedence': kb_info.get('supercedence', ''),
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
    """Lưu dữ liệu vào DynamoDB với xử lý duplicate"""
    saved_count = 0
    error_count = 0
    
    # Process in batches of 25 (DynamoDB batch write limit)
    batch_size = 25
    total_batches = len(items) // batch_size + (1 if len(items) % batch_size else 0)
    
    logger.info(f"Starting to save {len(items)} items in {total_batches} batches...")
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        batch_num = i // batch_size + 1
        
        try:
            # Use individual put_item to handle duplicates gracefully
            for item in batch:
                try:
                    table.put_item(Item=item)
                    saved_count += 1
                except Exception as e:
                    if 'ConditionalCheckFailedException' in str(e) or 'ValidationException' in str(e):
                        # Item already exists or duplicate, skip
                        logger.warning(f"Skipping duplicate item: {item.get('PK', '')}#{item.get('SK', '')}")
                        continue
                    else:
                        logger.error(f"Error saving item: {e}")
                        error_count += 1
                        
        except Exception as e:
            logger.error(f"Error saving batch {batch_num}: {e}")
            error_count += len(batch)
    
    return saved_count, error_count

def lambda_handler(event, context):
    """Main Lambda handler for CVE data update (2025-01 to 2025-06, Windows Server Core only, Critical/Important severity)"""
    logger.info("=== START update_full_cve_data Lambda ===")
    logger.info("Filtering for Windows Server Core installations (2016, 2019, 2022, 2025) with Critical/Important severity")
    logger.info("Time range: 2025-01 to 2025-06 (ALL MONTHS)")
    
    try:
        # Get the month to process from event or use current month
        target_month = event.get('month', None)
        
        if target_month:
            # Process specific month from event
            start_date = datetime.fromisoformat(target_month['start'])
            end_date = datetime.fromisoformat(target_month['end'])
            periods = [(start_date, end_date)]
            logger.info(f"Processing specific month: {start_date.strftime('%Y-%m')}")
        else:
            # Get all monthly periods
            all_periods = get_monthly_periods()
            logger.info(f"Total periods available: {len(all_periods)}")
            
            # Process all periods (all 6 months from 1/2025 to 6/2025)
            periods = all_periods
            logger.info(f"Processing all {len(periods)} periods from 1/2025 to 6/2025")
        
        total_fetched = 0
        total_processed = 0
        total_saved = 0
        total_errors = 0
        
        for i, (start_date, end_date) in enumerate(periods):
            logger.info(f"Processing period {i+1}/{len(periods)}: {start_date.strftime('%Y-%m')} to {end_date.strftime('%Y-%m')}")
            
            # Fetch CVE data for this month (increased to 1000 records for better coverage)
            cve_data = fetch_cve_data_for_month(start_date, end_date, max_records=1000)
            
            if not cve_data:
                logger.info(f"No data found for period {start_date.strftime('%Y-%m')} to {end_date.strftime('%Y-%m')}")
                continue
            
            total_fetched += len(cve_data)
            logger.info(f"Fetched {len(cve_data)} records for this period")
            
            # Process data for DynamoDB
            processed_items = process_cve_data(cve_data)
            total_processed += len(processed_items)
            logger.info(f"Processed {len(processed_items)} items for DynamoDB")
            
            # Save to DynamoDB
            saved_count, error_count = save_to_dynamodb(processed_items)
            total_saved += saved_count
            total_errors += error_count
            
            logger.info(f"Saved {saved_count} items to DynamoDB, {error_count} errors for this period")
            
            # Check if we're running out of time (leave 30 seconds buffer)
            if context and hasattr(context, 'get_remaining_time_in_millis'):
                remaining_time = context.get_remaining_time_in_millis()
                if remaining_time < 30000:  # 30 seconds
                    logger.warning(f"Running out of time. Remaining: {remaining_time}ms. Stopping processing.")
                    break
        
        # Calculate completion status
        all_periods = get_monthly_periods()
        completed_periods = len(periods)  # All periods were processed
        
        logger.info(f"Final summary - Total fetched: {total_fetched}, Total processed (filtered): {total_processed}, Total saved: {total_saved}, Total errors: {total_errors}")
        logger.info(f"All {completed_periods} periods from 1/2025 to 6/2025 have been processed")
        
        # Return summary with completion info
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'All CVE data update completed for 1/2025 to 6/2025',
                'summary': {
                    'totalFetched': total_fetched,
                    'totalProcessed': total_processed,
                    'savedToDynamoDB': total_saved,
                    'errors': total_errors,
                    'periodsProcessed': len(periods),
                    'totalPeriods': len(all_periods),
                    'completedPeriods': completed_periods,
                    'timeRange': {
                        'start': '2025-01-01T00:00:00',
                        'end': '2025-06-30T23:59:59'
                    },
                    'status': 'COMPLETED' if completed_periods == len(all_periods) else 'PARTIAL'
                }
            })
        }
        
    except Exception as e:
        logger.error(f"ERROR in update_full_cve_data Lambda: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }