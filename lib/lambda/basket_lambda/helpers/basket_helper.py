import boto3
import uuid
from datetime import datetime
from boto3.dynamodb.conditions import Key

def create_basket(table_name, item):
    try:
        ddb = boto3.resource('dynamodb')
        basket_table = ddb.Table(table_name)
        response = basket_table.put_item(Item=
            {
                'id': f"{uuid.uuid4()}",
                'creation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'last_modified_date':datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'created_by_user_id':item['created_by_user_id'],
                'last_modified_by_user_id':item['last_modified_by_user_id'],
                'active':item['active'],
                'uuid': item['user_uuid'],
                'unicornUuid':item['unicornUuid']
            }
            )
        return response
    except Exception as e:
        print(f"Error inside create_basket_helper_function  :  {e}")
        raise e


def delete_basket(table_name,basket_id):
    try:
        ddb = boto3.resource('dynamodb')
        basket_table = ddb.Table(table_name)
        response = basket_table.delete_item(
            Key={
                'id': str(basket_id)
            }
        )
        return response
    except Exception as e:
        print(f"Error Message in the delete_basket_handler_function : {e}")
        raise e

def get_basket(table_name,user_uuid,index_name):
    try:
        ddb = boto3.resource('dynamodb')
        basket_table = ddb.Table(table_name)
        response = basket_table.query(
            IndexName=index_name,
            KeyConditionExpression=Key('user_uuid').eq(str(user_uuid))
        )
        return response
    except Exception as e:
        print(f"Error Message in the get_basket_handler_function : {e}")
        raise e