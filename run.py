import gspread
import requests
from bs4 import BeautifulSoup

gc = gspread.service_account(filename="creds.json")

sheet = gc.open('Project3Python').sheet1

product = input('Enter event type or name: ').replace(' ', '%20')
location = input('Enter location: ').replace(' ', '%20')

url = f'https://www.eventbrite.com/d/united-kingdom--{location}/{product}/?page=1'
url2 = f'https://www.eventbrite.com/d/united-kingdom--{location}/{product}/?page=2'

page = requests.get(url)
page2 = requests.get(url2)

soup = BeautifulSoup(page.content, 'html.parser')
soup2 = BeautifulSoup(page2.content, 'html.parser')

events = soup.find_all('a', class_='event-card-link')
events2 = soup2.find_all('a', class_='event-card-link')

print(events)

event_data = []


