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

def scrape_eventbrite_events(location, product):
    url = f'https://www.eventbrite.com/d/united-kingdom--{location}/{product}/?page=1'
    
    page = requests.get(url)
    
    soup = BeautifulSoup(page.content, 'html.parser')
    
    events = soup.find_all('a', class_='event-card-link')
    
    event_data = []
    tags_counter = Counter()
    seen_urls = set()
    
    for event in events:
        event_url = event['href']
        if event_url in seen_urls:
            continue
        seen_urls.add(event_url)
        
        event_info = {
            'name': event.get('aria-label', '').replace('View', '').strip(),
            'location': event['data-event-location'],
            'url': event_url
        }
        
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

        event_info.update({
            'event_date_time': event_date_time,
            'summary': event_summary,
            'event_price': event_price
        })

        event_data.append(event_info)
    
    return event_data, tags_counter

def scrape_ticketweb_spotlight_venues(location):
    url = f'https://www.ticketweb.uk/search?q={location}'
    page = requests.get(url)
    soup = BeautifulSoup(page.content, 'html.parser')
    
    ticket_web_events = soup.find_all(lambda tag: tag.name == 'li' and tag.find('a'))
    ticket_web_events_dates = soup.find_all('div', class_='card-media responsive-ratios ratio16_9 theme-separator-strokes')
    
    event_data = []
    for event in ticket_web_events:
        name_span = event.find('span', class_='list-group-item-text')
        date_span = event.find('span', class_='small-l')
        url_anchor = event.find('a')
        
        spotlight_venues = {
            'name': name_span.get_text(strip=True) if name_span else 'N/A',
            'date': date_span.get_text(strip=True) if date_span else 'N/A',
            'url': url_anchor['href'] if url_anchor else 'N/A',
        }
        event_data.append(spotlight_venues)
    
    for event in ticket_web_events_dates:
        provider_h3 = event.find('h3', class_="card-title")
        location_title = event.find('title')
        
        spotlight_venues_locations = {
            'spotlight_provider': provider_h3.get_text(strip=True) if provider_h3 else 'N/A',
            'spotlight_location': location_title.get_text(strip=True) if location_title else 'N/A',
        }
        event_data.append(spotlight_venues_locations)
    
    return event_data

def main():
    while True:
        print("Choose an option:")
        print("1. Search for events")
        print("2. Search for spotlight venues")
        print("3. Exit")
        choice = input("Enter your choice: ").strip()

        if choice == '1':
            search_events()
        elif choice == '2':
            search_spotlight_venues()
        elif choice == '3':
            print("Exiting the program.")
            break
        else:
            print("Invalid choice. Please try again.")

def search_events():
    product = input('Enter event type or name: ').replace(' ', '%20')
    location = input('Enter location: ').replace(' ', '%20')

    search_key = f'{product}_{location}'

    spinner = Spinner("Fetching events...")
    spinner.start()

    unique_events = []

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
            events_data, tags_counter = scrape_eventbrite_events(location, product)
            unique_events.extend(events_data)
    finally:
        spinner.stop()

    display_paginated_events(unique_events, search_key)

def search_spotlight_venues():
    location = input('Enter location: ').replace(' ', '%20')

    search_key = f'spotlight_{location}'

    spinner = Spinner("Fetching spotlight venues...")
    spinner.start()

    unique_events = []

    try:
        if search_key in cache:
            spinner.stop()
            print("Using cached spotlight venues from hashtable.")
            unique_events = cache[search_key]
        else:
            spinner.stop()
            print("Scraping new spotlight venues.")
            spinner.start()
            spotlight_data = scrape_ticketweb_spotlight_venues(location)
            unique_events.extend(spotlight_data)
    finally:
        spinner.stop()

    display_paginated_events(unique_events, search_key)

def display_paginated_events(unique_events, search_key):
    page_size = 5
    total_events = len(unique_events)
    current_page = 0
    tags_counter = Counter()

    while current_page * page_size < total_events:
        start_index = current_page * page_size
        end_index = min(start_index + page_size, total_events)
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

    spinner = Spinner("Loading most common tags...")
    spinner.start()
    most_common_tags = tags_counter.most_common(6)
    spinner.stop()

    print(f'\nThe most common tags are:')
    for tag, count in most_common_tags:
        print(f'{tag}: {count}')
        
if __name__ == "__main__":
    main()