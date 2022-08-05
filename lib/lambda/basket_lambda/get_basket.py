import json 
import os
from helpers.basket_helper import get_basket

def handler(event,context):
    print(f'Event Request: {json.dumps(event)}')
    try:
        table_name = os.getenv('BASKET_TABLE_NAME')
        indexName = os.getenv('BASKET_INDEX_NAME')
        user_id = event['pathParameters']['user_uuid']
        unicorn_in_the_basket = get_basket(table_name=table_name,user_uuid=user_id, index_name=indexName)
        return {
            'statusCode': 200,
            'body': json.dumps(unicorn_in_the_basket)
        }
    except Exception as e:
        print(f"Error Message inside the get_basket_lambda :  {e}")
        return {
            'statusCode': 502,
            'body': json.dumps(e)
        }