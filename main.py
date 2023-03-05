import json
import requests
from bs4 import BeautifulSoup as bs
import lxml
from TikTokApi import TikTokApi
import proxy_config


class WiqApiInterface:
    headers = {'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/69.0'}
    NORMAL_STATUS_CODE = 200

    def __init__(self, proxy):
        self.__api_key = None
        self.parser = TikTokParser()

        self.proxy = {
            'https': f"http://{proxy['login']}:{proxy['password']}@{proxy['address']}"
        }

    @staticmethod
    def _if_api_key_exist(request_method):
        def wrapper(*args, **kwargs):
            self = args[0]
            if self.api_key is not None:
                return request_method(self)
            else:
                print('You did not install the API-key, or the file with it was corrupted')
        return wrapper

    @property
    def api_key(self):

        if self.__api_key is not None:
            return self.__api_key

        try:
            with open('config.json') as file:
                config = json.load(file)
        except FileNotFoundError:
            return None

        if 'wiq_api_key' not in set(config.keys()):
            return None

        self.__api_key = config['wiq_api_key']
        return self.__api_key

    def set_api_key(self):
        api_key = input('Enter your api key(write 0 to exit):')

        if api_key == '0':
            return None

        if not api_key.isalnum():
            print('API key must contain only letters and numbers, not symbols!')
            self.set_api_key()
            return
        response = requests.get(f'https://wiq.ru/api/?key={api_key}&action=balance', proxies=self.proxy)
        response = json.loads(response.text)

        if 'Error' not in set(response.keys()):
            try:
                with open('config.json') as file:
                    config = json.load(file)
            except Exception:
                config = {"wiq_api_key": None, 'orders_id': []}
            config['wiq_api_key'] = api_key

            with open("config.json", "w", encoding='utf-8') as json_file:
                json.dump(config, json_file, ensure_ascii=False, indent=2)

                self.__api_key = None
                print('New API key installed successfully')
        else:
            print('Error:' + response['Error'])
            self.set_api_key()


    @_if_api_key_exist
    def get_orders_status(self) -> dict:
        print('Here is the list of orders')

        try:
            with open('config.json') as file:
                config = json.load(file)
        except FileNotFoundError:
            print("Error: File (config.json) not found.\nUse the 'Set API key' function in the main menu to automatically create it")
            return None

        if len(config['orders_id']) == 0:
            print("Looks like you haven't ordered yet. . .")
            return {}

        list_of_orders = requests.get(f"https://wiq.ru/api/?key={self.api_key}&action=status&order={','.join(config['orders_id'])}", proxies=self.proxy)
        list_of_orders = json.loads(list_of_orders.text)
        if len(config['orders_id']) == 1:
            return {config['orders_id'][0]: list_of_orders}

        return list_of_orders

    @_if_api_key_exist
    def print_orders_status(self):
        orders_status = self.get_orders_status()

        for order_id, info in orders_status.items():
            print(f'Order ID-{order_id}, status-{info["status"]}\n'
                          f'Link-{info["link"]}\n'
                          f'Start count-{info["start_count"]}, remains-{info["remains"]}\n')
        return None

    @_if_api_key_exist
    def get_balance(self):
        response = requests.get(f'https://wiq.ru/api/?key={self.api_key}&action=balance', proxies=self.proxy)
        response = json.loads(response.text)
        balance = f"Balance - {response['balance']} {response['currency']}"
        return balance

    @_if_api_key_exist
    def get_servicer(self):
        response = requests.get(f'https://wiq.ru/api/?key={self.api_key}&action=services', proxies=self.proxy)
        response = json.loads(response.text)
        tik_tok_services = [service for service in response if service['category'] == '31']
        print('Type of wrapping (The price is indicated for 1000 pieces)')
        for service in tik_tok_services:
            print(f"ID-{service['ID']}: {service['name']}\n"
                  f"Price-{service['rate']}, min pieces-{service['min']} max-{service['max']}\n")

        return None

    @_if_api_key_exist
    def make_order(self,):
        print('Enter the service ID to create an order.\n'
              'Service IDs can be viewed in the function in the main menu((write 0 to exit)')

        service_id = input('ID:')
        quantity = input('Quantity:')
        link = input('Link:')

        if quantity == '0' or service_id == '0':
            return None

        response = requests.get(f'https://wiq.ru/api/?key={self.api_key}&action=create&service={service_id}&quantity={quantity}&link={link}', proxies=self.proxy)
        response = json.loads(response.text)

        if 'Error' not in set(response.keys()):
            with open('config.json') as file:
                config = json.load(file)

            config['orders_id'].append(response['order'])

            with open("config.json", "w", encoding='utf-8') as json_file:
                json.dump(config, json_file, ensure_ascii=False, indent=2)
            print('The process started successfully. You can view the order status in the main menu.')
        else:
            print(response['Error'])

    @_if_api_key_exist
    def get_order_statistic(self):
        order_id = input("Enter Order ID:")

        if order_id == "0":
            return None

        response = requests.get(f'https://wiq.ru/api/?key={self.api_key}&action=status&order={order_id}', proxies=self.proxy)
        response = json.loads(response.text)

        if 'Error' not in set(response.keys()) and response['status'] == 'Completed':
            self.parser.print_video_statistic(response['link'], self.proxy)
            return None
        elif response['status'] != 'Completed':
            print(f"Order has not yet been completed\nOrder status - {response['status']}")
            return None
        else:
            print(response['Error'])
            return None


class TikTokParser:
    NORMAL_STATUS_CODE = 200

    def __int__(self):
        pass

    def get_video_statistic(self, url, proxies):
        api = TikTokApi(proxy=proxies['https'])
        video_id = self.get_video_id(url)
        info = api.video(id=video_id).info()
        return info

    def print_video_statistic(self, url, proxies):
        video_statistic = self.get_video_statistic(url, proxies)
        video_statistic = video_statistic['stats']
        print(f"Viewed - {video_statistic['playCount']} | Likes - {video_statistic['diggCount']}\n"
              f"Comments - {video_statistic['commentCount']} | Share - {video_statistic['shareCount']}")

    def get_video_id(self, url):
        start_id = url.find('video/')+6
        finish_id = url.find('?', start_id+6)

        if finish_id == -1:
            video_id = url[start_id:]
        else:
            video_id = url[start_id: finish_id]
        return video_id


def main():

    proxy = {
        'login': proxy_config.login,
        'password': proxy_config.password,
        'address': proxy_config.address
    }

    interface = WiqApiInterface(proxy)

    funk_dict = {
        '2': interface.get_balance,
        '1': interface.set_api_key,
        '3': interface.get_servicer,
        '4': interface.make_order,
        '5': interface.print_orders_status,
        '6': interface.get_order_statistic,
    }

    while True:
        print('1 Set a API key\n2 Balance\n3 List services\n4 Make order\n5 My orders\n6 Get order statistic')

        command = input()

        output = funk_dict[command]()

        if output is not None:
            print(output)


if __name__ == '__main__':
    main()