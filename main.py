from concurrent.futures import ThreadPoolExecutor as PoolExecutor
from bs4 import BeautifulSoup as soup
from urllib.request import urlopen
import bs4 as bs
import urllib.request
import re
import requests
import json
import sys
import configparser


class Scraper:

    def __init__(self, config_path):
        # Config
        config = configparser.ConfigParser()
        config.read(config_path)
        self.USER = config['DEFAULT']['username']
        self.PWD = config['DEFAULT']['password']
        self.INCIDENT_API = "https://" + config['DEFAULT']['instance'] \
                            + ".service-now.com/api/now/table/incident"
        self.HEADERS = {"Content-Type": "application/json",
                        "Accept": "application/json"}
        self.PAYLOAD = {"caller_id": "4d147a386f0331003b3c498f5d3ee437",
                        "short_description": '',
                        "assignment_group": "8a4dde73c6112278017a6a4baf547aa7",
                        "category": "software",
                        "description": "scraped from web0"}
        self.MAX_WORKERS = int(config['DEFAULT']['max_workers'])

    @staticmethod
    def _get_bugs():
        bugs_url = \
            "https://bz.apache.org/bugzilla/buglist.cgi?quicksearch=error"
        source = urllib.request.urlopen(bugs_url).read()
        soup = bs.BeautifulSoup(source, 'lxml')
        bugs = soup.find_all('td', class_='bz_short_desc_column')
        bug_descriptions = []
        for bug in bugs:
            # Gross regex because I don't know how beautifulsoup works
            match_object = re.match(
                r"\[<a href=\"show_bug.cgi\?id=.*\">(.*).*</a>\]",
                str(bug.find_all('a')))
            bug_descriptions.append(match_object.group(1).strip())

        return bug_descriptions

    # Insert the data into the instance
    def insert_into_now(self, instance, payload):
        try:
            response = requests.post(instance,
                                     auth=(self.USER, self.PWD),
                                     headers=self.HEADERS,
                                     data=json.dumps(payload))
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            print(err)
            sys.exit(1)
        data = response.json()
        print(data)

    # Concurrently insert into NOW API
    def execute_concurrently(self, payload, api):
        with PoolExecutor(max_workers=self.MAX_WORKERS) as executor:
            for _ in executor.map(self.insert_into_now(api, payload)):
                pass

    # Build the payload for incident
    def populate_data(self):
        bugs = self._get_bugs()

        for bug in bugs:
            # Modify payload for incident
            self.PAYLOAD['short_description'] = bug
            self.execute_concurrently(self.PAYLOAD, self.INCIDENT_API)


if __name__ == '__main__':
    scraper = Scraper('config.ini')
    scraper.populate_data()
