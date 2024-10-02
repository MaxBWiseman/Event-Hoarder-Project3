import gspread
import requests
from bs4 import BeautifulSoup

gc = gspread.service_account(filename="creds.json")
# This is the file that contains the credentials for the Google Sheets API
sheet = gc.open('Project3Python').sheet1
# Opens the Google Sheet called Project3Python and selects the first sheet

product = input('Enter event type or name: ').replace(' ', '%20')
location = input('Enter location: ').replace(' ', '%20')
# The replace method replaces spaces with %20, which is the URL encoding for a space

url = f'https://www.eventbrite.com/d/united-kingdom--{location}/{product}/?page=1'
url2 = f'https://www.eventbrite.com/d/united-kingdom--{location}/{product}/?page=2'
# product and location are inserted into the URL with f-strings, 2 pages are used to get more events

page = requests.get(url)
page2 = requests.get(url2)
# The requests.get method is used to get the HTML content of the URL

soup = BeautifulSoup(page.content, 'html.parser')
soup2 = BeautifulSoup(page2.content, 'html.parser')
# You must specify the parser to use, in this case 'html.parser' for beautifulsoup to work

events = soup.find_all('a', class_='event-card-link')
events2 = soup2.find_all('a', class_='event-card-link')
# Fine all the elements with the tag 'a' and the class 'event-card-link' in the returned HTML

event_data = []
# Create an empty list to store the event data, to manipulate it later

for event in events + events2:
# Combines the two lists of events
    event_info = {
        'name': event['aria-label'].replace('View', '').strip(),
# Without this the word "View" will be included in the name of the event
        'location': event['data-event-location'],
        'url': event['href']
    }
# The event name, location and URL are stored in a dictionary
    event_data.append(event_info)
# event_info is appended to the event_data list
    
unique_events = []
# Create an empty list to store the unique events, checked by seen_urls
seen_urls = set()
# A set is a collection of unique elements, which makes removing duplicates easier when passed through.

for data in event_data:
    if data['url'] not in seen_urls:
        unique_events.append(data)
        seen_urls.add(data['url'])
# If the iterated URL is not in seen_urls which is a unique set, it is appended to unique_events and added to seen_urls.
# seen_urls acts as a filter to remove duplicates

for data in unique_events:
    event_url = data['url']
    page_detail = requests.get(event_url)
    page_detail_soup = BeautifulSoup(page_detail.content, 'html.parser')
    
    price_div = page_detail_soup.find('div', class_="conversion-bar__panel-info")
    event_price = price_div.get_text(strip=True) if price_div else 'Free'
# The price of the event is scraped from the searched events, if it is not found it is set to 'Free'

    summary = page_detail_soup.find('p', class_='summary')
    event_summary = summary.get_text(strip=True) if summary else 'No summary available'
# The summary of the event is scraped from the searched events, if it is not found it is set to 'No summary available'
    
    print(f'{data["name"]},\n{data["location"]}\nSummary: {event_summary}\nPrice: {event_price}\n---------------------------------')

