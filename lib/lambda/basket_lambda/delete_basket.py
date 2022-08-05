import json 
import os
from helpers.basket_helper import delete_basket

def handler(event,context):
    print(f'Event Request: {json.dumps(event)}')
    try:
        table_name = os.getenv('BASKET_TABLE_NAME')
        id = event['queryStringParameters']['id']
        delete_the_basket = delete_basket(table_name=table_name,basket_id=id)
        return {
            'statusCode': 200,
            'body': json.dumps(delete_the_basket)
        }
    except Exception as e:
        print(f"Error Message in delete_basket_lambda  : {e}")
        return {
            'statusCode': 502,
            'body': json.dumps(e)
        }