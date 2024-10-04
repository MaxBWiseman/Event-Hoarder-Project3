import gspread
import requests
from bs4 import BeautifulSoup
from collections import Counter
from datetime import datetime, timedelta
import itertools
import threading
import sys
import time
import hashlib

class Spinner:
    def __init__(self, message='Loading...'):
        self.message = message
        self.spinner = itertools.cycle(['|', '/', '-', '\\'])
        self.stop_running = threading.Event()
# This sets up the message and spinner, and creates a stop_running event that will be used to stop the spinner.
        
    def start(self):
        threading.Thread(target=self._spin).start()
# This starts a new thread that will run the _spin method.
    
    def _spin(self):
        while not self.stop_running.is_set():
# This method will run as long as the stop_running event is not set.
            sys.stdout.write(f'\r{self.message} {next(self.spinner)}')
# \r is a carriage return, which moves the cursor to the beginning of the line.
# This allows the spinner to overwrite itself on the same line, next(self.spinner) gets the next character in the spinner.
            sys.stdout.flush()
# Immediately flushes to the console to show the spinner.
            time.sleep(0.1)
            sys.stdout.write('\b')
# \b is a backspace, which moves the cursor back one character so a new character can be written.
    
    def stop(self):
        self.stop_running.set()
# Thread is stopped
        sys.stdout.write('\r' + ' ' * (len(self.message) + 2) + '\r')
# Clean up the spinner by overwriting it with spaces and moving the cursor back to the beginning of the line.
        sys.stdout.flush()

gc = gspread.service_account(filename="creds.json")
sheet = gc.open('Project3Python').sheet1

# Hashtable to cache recently searched events
cache = {}

def save_to_sheet(sheet, search_key, events):
    # Check if the sheet has reached 1000 rows
    if len(sheet.get_all_values()) >= 1000:
        sheet.clear()
    
    timestamp = datetime.now().isoformat()
# isoformat() method returns a string representing a date and time in ISO 8601 format example: '2021-09-01T12:00:00'
    data = []
    for event in events:
        unique_id = f'{search_key}_{hashlib.md5(event["url"].encode()).hexdigest()}'
# This gives the unique ID for each event by hashing the URL of the event
        
        cell = sheet.find(unique_id)
        while cell:
            sheet.delete_rows(cell.row)
            cell = sheet.find(unique_id)
# Delete existing rows with the same unique ID

        data.append([
            search_key, unique_id, timestamp,
            event.get('name', 'N/A'),
            event.get('location', 'N/A'),
            event.get('event_date_time', 'N/A'),
            event.get('summary', 'N/A'),
            event.get('event_price', 'N/A'),
            event.get('url', 'N/A')
        ])
    sheet.append_rows(data)
# This data is then appended to the Google Sheet, if none of the data is available, 'N/A' is used.

def load_from_sheet(sheet, search_key):
    cell = sheet.findall(search_key)
    if not cell:
        return []

    events = []
    for cell in cell:
        row_data = sheet.row_values(cell.row)
        timestamp = datetime.fromisoformat(row_data[2])
        if datetime.now() - timestamp > timedelta(hours=12):
            continue

        events.append({
            'name': row_data[3],
            'location': row_data[4],
            'event_date_time': row_data[5],
            'summary': row_data[6],
            'event_price': row_data[7],
            'url': row_data[8]
        })

    return events

def display_events(events, start_index, end_index, search_key, tags_counter):
    collected_events = []
    for data in events[start_index:end_index]:
        event_url = data['url']
        page_detail = requests.get(event_url)
        page_detail_soup = BeautifulSoup(page_detail.content, 'html.parser')

        price_div = page_detail_soup.find('div', class_="conversion-bar__panel-info")
        event_price = price_div.get_text(strip=True) if price_div else 'Free'

        summary = page_detail_soup.find('p', class_='summary')
        event_summary = summary.get_text(strip=True) if summary else 'No summary available'

        date_time = page_detail_soup.find('span', class_='date-info__full-datetime')
        event_date_time = date_time.get_text(strip=True) if date_time else 'No date and time available'

        tags = page_detail_soup.find_all('a', class_='tags-link')
        for tag in tags:
            tags_counter[tag.get_text(strip=True)] += 1

        collected_events.append({
            'name': data['name'],
            'location': data['location'],
            'event_date_time': event_date_time,
            'summary': event_summary,
            'event_price': event_price,
            'url': event_url
        })

        print(f'-------------------------------------\n{data["name"]},\n{data["location"]}\nDate & Time: {event_date_time}\nSummary: {event_summary}\nPrice: {event_price}')

    # Save the collected events to Google Sheets
    save_to_sheet(sheet, search_key, collected_events)

    # Cache the events in the hashtable
    cache[search_key] = collected_events

while True:
    product = input('Enter event type or name: ').replace(' ', '%20')
    location = input('Enter location: ').replace(' ', '%20')

    search_key = f'{product}_{location}'

    spinner = Spinner("Fetching events...")
    spinner.start()

    unique_events = []  # Ensure unique_events is defined

    try:
        # Check if the search term is in the cache
        if search_key in cache:
            spinner.stop()
            print("Using cached events from hashtable.")
            spinner = Spinner("Using cached events from hashtable...")
            spinner.start()
            unique_events = cache[search_key]
        else:
            spinner.stop()
            print("Scraping new events.")
            spinner = Spinner("Scraping new events...")
            spinner.start()
            url = f'https://www.eventbrite.com/d/united-kingdom--{location}/{product}/?page=1'
            url2 = f'https://www.eventbrite.com/d/united-kingdom--{location}/{product}/?page=2'
            url3 = f'https://www.ticketmaster.co.uk/search?q={product}'
            url4 = f'https://www.ticketweb.uk/'

            page = requests.get(url)
            page2 = requests.get(url2)
            page3 = requests.get(url3)
            page4 = requests.get(url4)
            
            soup = BeautifulSoup(page.content, 'html.parser')
            soup2 = BeautifulSoup(page2.content, 'html.parser')
            soup3 = BeautifulSoup(page3.content, 'html.parser')
            soup4 = BeautifulSoup(page4.content, 'html.parser')

            events = soup.find_all('a', class_='event-card-link')
            events2 = soup2.find_all('a', class_='event-card-link')
# events 2 is the second page of events
            
            ticket_web_events = soup4.find_all(lambda tag: tag.name == 'li' and tag.find('a'))
            ticket_web_events_dates = soup4.find('div', class_='card-media responsive-ratios ratio16_9 theme-separator-strokes')
# This finds all the 'li' tags that have an 'a' tag inside them, using a lambda to scrape spotlight venue data
# ticket_web_event_dates is used to scrape the dates off the homepage cards.4 c
            
            event_data = []
            tags_counter = Counter()
            
            for event in ticket_web_events:
                spotlight_venues = {
                    'name': event.find('span', class_='list-group-item-text').get_text(strip=True)
                    'date': event.find('span', class_='small-l').get_text(strip=True)
                    'url': event.find('a')['href']
                }
                event_data.append(spotlight_venues)
                
            for event in ticket_web_events_dates:
                spotlight_venues_locations = {
                    'spotlight_provider': event.find('h3', class_="card-title").get_text(strip=True)
                    'spotlight_location': event.find('title').get_text(strip=True)
                }
                
            for event in events + events2:
                event_info = {
                    'name': event.get('aria-label', '').replace('View', '').strip(),
                    'location': event['data-event-location'],
                    'url': event['href']
                }
                event_data.append(event_info)

            unique_events = []
            seen_urls = set()

            for data in event_data:
                if data['url'] not in seen_urls:
                    unique_events.append(data)
                    seen_urls.add(data['url'])
    finally:
        spinner.stop()

    page_size = 5
    total_events = len(unique_events)
    current_page = 0

    while current_page * page_size < total_events:
        start_index = current_page * page_size
        end_index = start_index + page_size
        display_events(unique_events, start_index, end_index, search_key, tags_counter)
        
        if end_index >= total_events:
            break
        
        user_input = input("Press 'Y' to see more events, 'S' to start a new search, or any other key to exit: ").strip().lower()
        if user_input == 's':
            break
        elif user_input == 'y':
            current_page += 1
        else:
            print("Exiting the program.")
            sys.exit()

    if user_input != 's':
        break

spinner = Spinner("Loading most common tags...")
spinner.start()
most_common_tags = tags_counter.most_common(6)
spinner.stop()

print(f'\nThe most common tags are:')
for tag, count in most_common_tags:
    print(f'{tag}: {count}')