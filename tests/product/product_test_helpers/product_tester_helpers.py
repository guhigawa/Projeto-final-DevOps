import requests, json, time, random
from random import uniform, randrange
from datetime import datetime

class TestProductHelpers:
    __test__ = False

    def __init__(self,base_url):
        self.base_url = base_url


    def generate_unique_object(self):
        timestamp = int(time.time())
        formated_date = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H-%M-%S")
        raw_price = uniform(100.00, 3000.00)
        price = round(raw_price,2)
        name = f"test {formated_date}"
        description = f"Descritivo teste {formated_date}" 
        quantity = randrange(1,10)
        item = {"name":name,"price":price,"description":description,"quantity":quantity}
        return item


    