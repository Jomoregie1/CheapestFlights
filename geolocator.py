import random
import requests
from geopy.geocoders import Nominatim
from geopy.distance import great_circle


class GeoLocator:

    def __init__(self, ip_file_path="ip_address_file_txt", sample_size=100,
                 proxy_list_url="https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt",
                 BATCH_GEO_QUERY_URL="http://ip-api.com/batch"):
        self.ip_file_path = ip_file_path
        self.sample_size = sample_size
        self.proxy_list_url = proxy_list_url
        self.ip_to_port = None
        self.location_data = None
        self.BATCH_GEO_QUERY_URL = BATCH_GEO_QUERY_URL

    def retrieve_ip_addresses(self):
        is_download_successful = False
        try:
            response = requests.get(self.proxy_list_url)
            response.raise_for_status()

            with open(self.ip_file_path, "w") as file:
                file.write(response.text)
                is_download_successful = True
        except requests.exceptions.RequestException as e:
            print(f"Failed to download IP addresses: {e}")

        return is_download_successful

    def read_ip_addresses_from_file(self):
        with open(self.ip_file_path, "r") as file:
            addresses_and_ports = [tuple(line.strip().split(":")) for line in file.readlines()]

        return addresses_and_ports

    def get_random_sample_of_addresses(self):
        addresses_and_ports = self.read_ip_addresses_from_file()
        sample_addresses_ports = random.sample(addresses_and_ports, self.sample_size)

        return sample_addresses_ports

    def load_ip_port_combinations(self):
        sample_addresses_ports = self.get_random_sample_of_addresses()
        self.ip_to_port = {item[0]: item[1] for item in sample_addresses_ports}
        self.location_data = []

    # Consider how to handle errors - possibly retry request if there is a failure.
    def retrieve_location_data(self):
        payload = [{"query": ip, "fields": "query,country,city,countryCode,lat,lon"} for ip in
                   self.ip_to_port.keys()]
        try:
            response = requests.post(self.BATCH_GEO_QUERY_URL, json=payload)
            response.raise_for_status()
            self.location_data = response.json()
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            self.location_data = []

    def get_country_coordinates(self, country_name):
        geolocator = Nominatim(user_agent="geolocator")
        location = geolocator.geocode(country_name)
        if location:
            return location.latitude, location.longitude
        else:
            return None

    def find_closest_countries(self, target_coords):

        closest_countries = []

        if not self.location_data:
            print("No data retrieved from request!")
            return closest_countries

        for location in self.location_data:
            distance = great_circle(target_coords, (location['lat'], location['lon']))
            if location['query'] in self.ip_to_port:
                closest_countries.append(
                    {"Country": location['country'], "ip": location['query'], "port": self.ip_to_port[location['query']]
                        , "Distance": distance}
                )

        closest_countries.sort(key=lambda x: x["Distance"])

        return closest_countries
