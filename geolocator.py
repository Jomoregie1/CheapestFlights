import random
import time
import requests
from typing import Tuple, Optional, Dict, List, NoReturn
from geopy.geocoders import Nominatim
from geopy.distance import great_circle


class GeoLocator:

    def __init__(self, ip_file_path="ip_address_file.txt", sample_size=100,
                 proxy_list_url="https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt",
                 BATCH_GEO_QUERY_URL="http://ip-api.com/batch"):
        self.ip_file_path = ip_file_path
        self.sample_size = sample_size
        self.proxy_list_url = proxy_list_url
        self.ip_to_port = None
        self.location_data = None
        self.BATCH_GEO_QUERY_URL = BATCH_GEO_QUERY_URL
        self.is_download_successful = False

    def setup(self) -> NoReturn:
        """Initializes the geolocator by downloading IP addresses, loading IP-port combinations, and retrieving
        location data. """
        self.retrieve_ip_addresses()
        if self.is_download_successful:
            self.load_ip_port_combinations()
            self.retrieve_location_data()
            self.is_download_successful = False
        else:
            print("Failed to download IP addresses. Please check your internet connection and try again.")

    def reset(self) -> NoReturn:

        """
            Resets the GeoLocator instance's state, clearing the IP-to-port mappings,
            location data, and download success status. This method is useful for
            reinitialising the instance's state before a new setup or operation cycle,
            ensuring that old data does not affect new operations.
            """

        self.ip_to_port = None
        self.location_data = None
        self.is_download_successful = False

    def retrieve_ip_addresses(self) -> NoReturn:

        """
            Attempts to download a list of IP addresses from the configured proxy list URL
            and save it to the specified file path. The method updates the
            `is_download_successful` attribute based on the outcome of the download attempt.

            If the download is successful, the IP addresses are written to the file defined
            by `ip_file_path`, and `is_download_successful` is set to True. If the download
            fails due to a request exception, the method prints an error message and
            `is_download_successful` remains False.
            """

        try:
            response = requests.get(self.proxy_list_url)
            response.raise_for_status()

            with open(self.ip_file_path, "w") as file:
                file.write(response.text)
                self.is_download_successful = True
        except requests.exceptions.RequestException as e:
            print(f"Failed to download IP addresses: {e}")

    def read_ip_addresses_from_file(self) -> List[Tuple[str, str]]:

        """
            Reads IP addresses and their associated port numbers from a file specified by
            `ip_file_path`. Each line in the file is expected to contain an IP address and
            a port number, separated by a colon.

            The method attempts to open and read the file, parsing each line into a tuple
            of (IP address, port number). If an error occurs during file opening or reading,
            it catches the exception, prints an error message, and prompts the user to try again.

            Returns:
                addresses_and_ports (list of tuples): A list containing tuples, each consisting
                of an IP address and a port number as strings, extracted from the file.
                Returns an empty list if an exception is caught.

            Notes:
                This method prints an error message and suggests retrying in case of exceptions
                such as `FileNotFoundError` or any other `IOError`. The exact exception is printed
                to aid in troubleshooting.
            """

        addresses_and_ports = []

        try:
            with open(self.ip_file_path, "r") as file:
                addresses_and_ports = [tuple(line.strip().split(":")) for line in file.readlines()]

        except Exception as e:
            print(f"Exception: {e}")
            print("Please try again.")

        return addresses_and_ports

    def get_random_sample_of_addresses(self) -> List[Tuple[str, str]]:

        """
        Retrieves a random sample of IP addresses and their associated port numbers from the list of addresses
        read from the file specified by `ip_file_path`, with the sample size not exceeding the total number
        of available addresses and ports. If the initially specified `sample_size` is larger than the
        total number of addresses, it is automatically adjusted to fit the maximum possible size.

        Returns:
            sample_addresses_ports (list of tuples): A randomly selected subset of the addresses and ports,
            where each element is a tuple containing an IP address and a port number as strings. The final
            sample size is the lesser of the initially specified `sample_size` or the total number of available
            addresses and ports.
         """

        addresses_and_ports = self.read_ip_addresses_from_file()

        self.sample_size = min(self.sample_size, len(addresses_and_ports))

        sample_addresses_ports = random.sample(addresses_and_ports, self.sample_size)

        return sample_addresses_ports

    def load_ip_port_combinations(self) -> NoReturn:

        """
            Populates the `ip_to_port` dictionary with IP address and port number pairs
            retrieved from a random sample of addresses read from the specified file.
            This method ensures that `ip_to_port` reflects a current subset of available
            IP addresses and their associated ports, based on the `sample_size` attribute.
            It also resets `location_data` to an empty list in preparation for new location
            data retrieval, ensuring any previous location data does not affect subsequent operations.

            The `get_random_sample_of_addresses` method is used to obtain a random sample
            of addresses, which is then mapped to a dictionary where each key-value pair
            corresponds to an IP address and its associated port number.

            Post-Conditions:
                - `ip_to_port` is updated with the new IP address and port number pairs.
                - `location_data` is reset to an empty list to prevent stale data.
            """

        sample_addresses_ports = self.get_random_sample_of_addresses()
        self.ip_to_port = {item[0]: item[1] for item in sample_addresses_ports}
        self.location_data = []

    def retrieve_location_data(self, attempts: int = 3) -> NoReturn:

        """
            Attempts to retrieve geolocation data for a set of IP addresses by making a POST request
            to a batch geolocation query URL. The method tries up to a specified number of attempts
            to obtain the data, with a pause between failed attempts.

            The payload for the POST request is constructed from the IP addresses stored in `ip_to_port`,
            requesting specific fields (`query`, `country`, `city`, `countryCode`, `lat`, `lon`) for each IP.

            If the request is successful, the method updates `self.location_data` with the response data.
            In case of request failures, it retries the request, waiting for 60 seconds between attempts.
            If all attempts fail, it logs a failure message and sets `self.location_data` to an empty list.

            Parameters:
                attempts (int): The number of attempts to make in case of request failures. Defaults to 3.

            Post-Conditions:
                - `self.location_data` is updated with the geolocation data on success.
                - `self.location_data` is set to an empty list on failure after exhausting all attempts.

            Note:
                The method uses a fixed delay of 60 seconds between retries and logs the remaining attempts.
                Adjust the `attempts` parameter and delay as necessary based on application requirements and
                API rate limiting.
        """

        payload = [{"query": ip, "fields": "query,country,city,countryCode,lat,lon"} for ip in
                   self.ip_to_port.keys()]

        while attempts > 0:
            try:
                response = requests.post(self.BATCH_GEO_QUERY_URL, json=payload)
                response.raise_for_status()
                self.location_data = response.json()
                return
            except requests.exceptions.RequestException as e:
                print(f"Request failed: {e}, attempts left: {attempts - 1}")
                time.sleep(60)
                attempts -= 1

        print("Failed to retrieve location data after multiple attempts.")
        self.location_data = []

    def get_country_coordinates(self, country_name: str) -> Optional[Tuple[float, float]]:

        """
            Retrieves the geographical coordinates (latitude and longitude) of a given country
            by its name using the Nominatim geocoding service.

            Parameters:
                country_name (str): The name of the country for which to retrieve the coordinates.

            Returns:
                tuple: A tuple containing the latitude and longitude of the country if found,
                       otherwise, None is returned. The tuple format is (latitude, longitude).

            Note:
                This method relies on the Nominatim geocoding service, which requires a user agent
                to be specified. The method uses "geolocator" as the user agent. Make sure that the
                usage complies with Nominatim's Terms of Service. The accuracy and availability of
                coordinates depend on the service's data.

            Example:
                >>> geo_locator = GeoLocator()
                >>> geo_locator.get_country_coordinates("France")
                (46.603354, 1.888334)
            """

        geolocator = Nominatim(user_agent="geolocator")
        location = geolocator.geocode(country_name)
        if location:
            return location.latitude, location.longitude
        else:
            return None

    def find_closest_countries(self, target_coords: Tuple[float, float]) -> List[Dict[str, any]]:

        """
            Identifies and returns a list of the closest countries to a given set of geographical coordinates,
            based on the geolocation data previously retrieved and stored in `self.location_data`. The distances
            are calculated using the great-circle distance between the target coordinates and each location in
            `self.location_data`.

            Parameters:
                target_coords (Tuple[float, float]): A tuple containing the latitude and longitude of the target
                                                     location for which to find the closest countries.

            Returns:
                List[Dict[str, Union[str, float]]]: A sorted list of dictionaries, each representing a country
                                                    closest to the target coordinates. Each dictionary contains
                                                    the country name ('Country'), the IP address ('ip'), the
                                                    port number ('port'), and the calculated distance ('Distance')
                                                    from the target coordinates. The list is sorted by 'Distance',
                                                    ascending.

            Note:
                This method relies on `self.location_data` being populated with valid geolocation data for the
                IP addresses of interest. If `self.location_data` is empty, indicating that no data was retrieved
                or that an error occurred during data retrieval, the method prints a warning message and returns
                an empty list.

                The method assumes that `self.ip_to_port` has been previously populated with IP-to-port mappings
                corresponding to the entries in `self.location_data`.

            Example:
                >>> geo_locator = GeoLocator()
                >>> geo_locator.setup()
                >>> closest_countries = geo_locator.find_closest_countries((48.8566, 2.3522))
                >>> print(closest_countries)
                [{'Country': 'France', 'ip': '123.123.123.123', 'port': '8080', 'Distance': 0.0}, ...]
            """

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
