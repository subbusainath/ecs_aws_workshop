import json 
import os
from helpers.basket_helper import create_basket

def handler(event,context):
    print(f'Event Request: {json.dumps(event)}')
    try:
        table_name = os.getenv('BASKET_TABLE_NAME')
        basket_item = event['body']['item'] 
        unicorn_basket = create_basket(table_name=table_name, item=basket_item)
        return {
            'statusCode': 200,
            'body': json.dumps(unicorn_basket)
        }
    except Exception as e:
        print(f"Error Message in the basket_lambda :  {e}")
        return {
            'statusCode': 502,
            'body': json.dumps(e)
        }