from typing import Dict, Union, List, Optional
import requests
import configparser

config = configparser.ConfigParser()
config.read('config.cfg')

API_KEY = config['RAPIDAPI']['API_KEY']
API_HOST = config['RAPIDAPI']['API_HOST']
BASE_API_URL = config['RAPIDAPI']['BASE_API_URL']


def date_to_dict(date_str: str) -> Dict[str, int]:
    year, month, day = map(int, date_str.split('-'))
    return {
        'day': day,
        'month': month,
        'year': year
    }


class HotelsAPI:
    def __init__(self):
        self.base_url = BASE_API_URL
        self.headers = {
            "X-RapidAPI-Key": API_KEY,
            "X-RapidAPI-Host": API_HOST
        }

    def _create_payload(self, city_id: int,
                        check_in_date: str,
                        check_out_date: str,
                        sort: str,
                        additional_filters: Optional[Dict[str, str]] = None) -> Dict:
        payload = {
            'currency': 'USD',
            'eapid': 1,
            'locale': 'ru_RU',
            'siteId': 300000001,
            'destination': {
                'regionId': city_id
            },
            'checkInDate': date_to_dict(check_in_date),
            'checkOutDate': date_to_dict(check_out_date),
            'rooms': [{'adults': 1}],
            'resultsStartingIndex': 0,
            'resultsSize': 10,
            'sort': sort,
            'filters': {'availableFilter': 'SHOW_AVAILABLE_ONLY'}
        }
        if additional_filters:
            payload['filters'].update(additional_filters)
        return payload

    async def search_by_guest_rating(self, city_id: int, check_in_date: str, check_out_date: str) -> Dict:
        url = f"{self.base_url}/properties/v2/list"
        payload = self._create_payload(
            city_id, check_in_date, check_out_date, 'REVIEW')
        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()

    async def search_by_bestdeal(self, city_id: int, check_in_date: str, check_out_date: str = None) -> Dict:
        url = f"{self.base_url}/properties/v2/list"
        additional_filters = {"guestRating": "40"}
        payload = self._create_payload(
            city_id, check_in_date, check_out_date, 'DISTANCE', additional_filters)
        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()

    async def search_by_lowprice(self, city_id: int, check_in_date: str, check_out_date: str) -> Dict:
        url = f"{self.base_url}/properties/v2/list"
        payload = self._create_payload(
            city_id, check_in_date, check_out_date, 'PRICE_LOW_TO_HIGH')
        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()

    async def get_city_id(self, city_name: str) -> Union[List[Dict[str, Union[int, str]]], None]:
        url = f"{self.base_url}/locations/v3/search"
        params = {
            'q': city_name,
            'locale': 'ru_RU'
        }
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        try:
            cities = []
            for city in response.json().get('sr', [])[:10]:
                if city.get('@type') == 'gaiaRegionResult':
                    cities.append({
                        'id': city['gaiaId'],
                        'name': city['regionNames']['fullName']
                    })
            return cities
        except (IndexError, KeyError):
            return None
