import boto3
import json
import uuid
from datetime import datetime
from dotenv import load_dotenv
import os
load_dotenv()

REGION = os.getenv('AWS_REGION', 'ap-south-1')

def save_report(user_id, file_name, analysis):
    """Save full analysis to DynamoDB."""
    try:
        dynamodb = boto3.resource('dynamodb', region_name=REGION)
        table = dynamodb.Table('LabReports')

        report_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()

        table.put_item(Item={
            'report_id': report_id,
            'timestamp': timestamp,
            'user_id': user_id,
            'file_name': file_name,
            'patient_name': analysis.get('patient_name', 'Unknown'),
            'total_tests': analysis.get('total_tests', 0),
            'abnormal_count': analysis.get('abnormal_count', 0),
            'specialist': json.dumps(analysis.get('specialist', {})),
            'questions': json.dumps(analysis.get('questions', {})),
            'full_analysis': json.dumps(analysis)
        })

        print(f"[DB] Report saved: {report_id}")
        return report_id

    except Exception as e:
        print(f"[DB] Save failed: {e}")
        return None

def get_user_reports(user_id):
    """Fetch all reports for a user."""
    try:
        dynamodb = boto3.resource('dynamodb', region_name=REGION)
        table = dynamodb.Table('LabReports')

        response = table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('user_id').eq(user_id)
        )
        reports = sorted(
            response.get('Items', []),
            key=lambda x: x['timestamp'],
            reverse=True
        )
        return reports

    except Exception as e:
        print(f"[DB] Fetch failed: {e}")
        return []