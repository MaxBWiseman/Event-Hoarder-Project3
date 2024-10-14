import requests
from bs4 import BeautifulSoup
from collections import Counter
from datetime import datetime
import itertools
import threading
import sys
import time
import re
from datetime import datetime
from dateutil import parser
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

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


# Hashtable to cache recently searched events
cache = {}

uri = "mongodb+srv://GackedShotty:QJBdmnp2HnOH8cPP@project3.zbjlo.mongodb.net/?retryWrites=true&w=majority&appName=Project3"
# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))
# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)
    
db = client['Event_Hoarder']
collection = db['Event_Data']

def save_to_mongodb(collection, search_key, events):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    for event in events:
        unique_id = event.get('url', 'N/A')
        if unique_id == 'N/A':
            continue
        
        saved_date = event.get('timestamp', timestamp)
        start_date = event.get('event_date_time', 'N/A')
        
        try:
            checked_saved_date = datetime.strptime(saved_date, '%Y-%m-%d %H:%M:%S')
            checked_start_date = datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            collection.delete_one({'url': unique_id})
            continue
        
        if checked_saved_date > checked_start_date:
            collection.delete_one({'url': unique_id})
            continue
        
        event_data = {
            'search_key': search_key,
            'url': unique_id,
            'timestamp': timestamp,
            'name': event.get('name', 'N/A'),
            'location': event.get('location', 'N/A'),
            'event_date_time': event.get('event_date_time', 'N/A'),
            'summary': event.get('summary', 'N/A'),
            'event_price': event.get('event_price', 'N/A')
        }
        
        collection.update_one({'url': unique_id}, {'$set': event_data}, upsert=True)

def display_events(events, start_index, end_index, search_key, tags_counter, user_selection):
    collected_events = events[start_index:end_index]
    for data in collected_events:
        if isinstance(data, dict):
            print(f'-------------------------------------\n{data["name"]},\n{data["location"]}\nDate & Time: {data["show_date_time"]}\nPrice: {data["event_price"]}')
        else:
            print(f"Skipping invalid event data: {data}")
    save_to_mongodb(collection, search_key, collected_events)

    # Cache the events in the hashtable
    cache[search_key] = events
    
    
def parsed_scraped_date(date_time):
    if 'No date and time available' in date_time or not date_time.strip():
        return 'N/A'
    # If the date_time is not available, return 'N/A'
    
    replacements = {
        'Monday': '',
        'Mon': '',
        'Tuesday': '',
        'Tue': '',
        'Wednesday': '',
        'Wed': '',
        'Thursday': '',
        'Thu': '',
        'Friday': '',
        'Fri': '',
        'Saturday': '',
        'Sat': '',
        'Sunday': '',
        'Sun': '',
        'Starts on': '',
        'GMT': '',
        'GMT+1': '',
        'January': 'Jan',
        'February': 'Feb',
        'March': 'Mar',
        'April': 'Apr',
        'May': 'May',
        'June': 'Jun',
        'July': 'Jul',
        'August': 'Aug',
        'September': 'Sep',
        'October': 'Oct',
        'November': 'Nov',
        'December': 'Dec',
        'pm': 'PM',
        'am': 'AM',
        '·': '',
        ' - ': ' ',
        '+1': '',
    }

    for key, value in replacements.items():
        date_time = date_time.replace(key, value)
    # Replace the long names of the days and months with their abbreviations
    # Also replace other unwanted strings

    # Remove any extra spaces and commas
    date_time = ' '.join(date_time.split()).replace(',', '')
    
    # For cases where users enter date ranges, only take the first date
    date_time_parts = date_time.split(' ')
    # Only take the first 5 parts of the date_time
    if len(date_time_parts) > 3:
        date_time = ' '.join(date_time_parts[:3])
    # If the length of the date_time is less than 3, return the date_time as is
    # If the length of the date_time is greater than 3, only take the first 5 parts of the date_time
    # parts example: ['2024-10-19', '16:30:00']

    try:
        # Use dateutil.parser to parse the date
        dt = parser.parse(date_time, fuzzy=True)
    except ValueError:
        raise ValueError(f"Date format not recognized: {date_time}")
    # parser.parse will try to parse the date and time from the string
    # fuzzy=True allows for more flexibility in the date format

    # Format the datetime object into the desired format
    formatted_date = dt.strftime('%Y-%m-%d %H:%M:%S')

    return formatted_date
    
    

def scrape_eventbrite_events(location, product, page_number):
    url = f'https://www.eventbrite.com/d/united-kingdom--{location}/{product}/?page={page_number}'
    
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
            'url': event_url
        }
        
        page_detail = requests.get(event_url)
        page_detail_soup = BeautifulSoup(page_detail.content, 'html.parser')

        price_div = page_detail_soup.find('div', class_="conversion-bar__panel-info")
        event_price = price_div.get_text(strip=True) if price_div else 'Free'
        
        location_div = page_detail_soup.find('div', class_='location-info__address')
        event_location = location_div.get_text(strip=True) if location_div else 'No location available'

        summary = page_detail_soup.find('p', class_='summary')
        event_summary = summary.get_text(strip=True) if summary else 'No summary available'

        date_time = page_detail_soup.find('span', class_='date-info__full-datetime')
        event_date_time = date_time.get_text(strip=True) if date_time else 'No date and time available'

        date_parsed = parsed_scraped_date(event_date_time)
        
        tags = page_detail_soup.find_all('a', class_='tags-link')
        for tag in tags:
            tags_counter[tag.get_text(strip=True)] += 1

        event_info.update({
            'location': event_location,
            'show_date_time': event_date_time, # More clearer user version of the date
            'event_date_time': date_parsed,
            'summary': event_summary,
            'event_price': event_price
        })

        event_data.append(event_info)
    
    return event_data, tags_counter

def scrape_eventbrite_top_events(country, location, category_slug, page_number=1):
    url = f'https://www.eventbrite.co.uk/d/{country}--{location}/{category_slug}--events/?page={page_number}'
    
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
            'url': event_url
        }
        
        page_detail = requests.get(event_url)
        page_detail_soup = BeautifulSoup(page_detail.content, 'html.parser')

        price_div = page_detail_soup.find('span', class_="eds-text-bm eds-text-weight--heavy")
        event_price = price_div.get_text(strip=True) if price_div else 'Free'

        location_div = page_detail_soup.find('div', class_='location-info__address')
        event_location = location_div.get_text(strip=True) if location_div else 'No location available'
        
        summary_div = page_detail_soup.find('div', class_='eds-text--left')
        event_summary = 'No summary available'
        if summary_div:
            p_element = summary_div.find('p')
            if p_element:
                event_summary = p_element.get_text(strip=True)

        date_time = page_detail_soup.find('span', class_='date-info__full-datetime')
        event_date_time = date_time.get_text(strip=True) if date_time else 'No date and time available'

        date_parsed = parsed_scraped_date(event_date_time)
        
        tags = page_detail_soup.find_all('a', class_='tags-link')
        for tag in tags:
            tags_counter[tag.get_text(strip=True)] += 1

        event_info.update({
            'location': event_location,
            'event_date_time': date_parsed,
            'summary': event_summary,
            'event_price': event_price
        })

        event_data.append(event_info)
    
    return event_data, tags_counter, len(event_data)


def scrape_eventbrite_top_events_no_category(location, country):
    url = f'https://www.eventbrite.co.uk/d/{country}--{location}/events/'
    
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
            'url': event_url
        }
        
        page_detail = requests.get(event_url)
        page_detail_soup = BeautifulSoup(page_detail.content, 'html.parser')
        
        location_div = page_detail_soup.find('div', class_='location-info__address')
        event_location = location_div.get_text(strip=True) if location_div else 'No location available'
        
        price_div = page_detail_soup.find('span', class_="eds-text-bm eds-text-weight--heavy")
        event_price = price_div.get_text(strip=True) if price_div else 'Free'

        summary_div = page_detail_soup.find('div', class_='event-details__main-inner')
        event_summary = summary_div.get_text(strip=True) if summary_div else 'No summary available'
        
        if summary_div:
            p_element = summary_div.find('p')
            if p_element:
                event_summary = p_element.get_text(strip=True)

        date_time = page_detail_soup.find('span', class_='date-info__full-datetime')
        event_date_time = date_time.get_text(strip=True) if date_time else 'No date and time available'

        date_parsed = parsed_scraped_date(event_date_time)
        
        event_info.update({
            'location': event_location,
            'event_date_time': date_parsed,
            'summary': event_summary,
            'event_price': event_price
        })

        event_data.append(event_info)
    print(f"events scraped{len(event_data)}")
    print(url)
    return event_data

def main():
    while True:
        print("Choose an option:")
        print("1. Search for quick events")
        print("2. Search for popular categories")
        print("3. Exit")
        print("#. Clear Database")
        choice = input("Enter your choice: ").strip()

        if choice == '1':
            search_events()
        elif choice == '2':
            search_top_categories()
        elif choice == '3':
            print("Exiting the program.")
            sys.exit()
        elif choice == '#':
            collection.delete_many({})
            print('Database cleared.')
            main()
        else:
            print("Invalid choice. Please try again.")

def search_events():
    product = input('Enter event type or name: ').replace(' ', '%20')
    location = input('Enter location: ').replace(' ', '%20')

    search_key = f'{product}_{location}'

    spinner = Spinner("Fetching events...")
    spinner.start()

    unique_events = []
    page_number = 1

    try:
        # Check if the search term is in the cache
        if search_key in cache:
            spinner.stop()
            print("Using cached events from hashtable.")
            unique_events = cache[search_key]
        else:
            spinner.stop()
            spinner = Spinner("Scraping new events...")
            spinner.start()
            events_data, tags_counter = scrape_eventbrite_events(location, product, page_number)
            unique_events.extend(events_data)
            cache[search_key] = unique_events
    finally:
        spinner.stop()

    result = display_paginated_events(unique_events, search_key, 'eventbrite', location, None, None, product, page_number)
    if result == 'new_search':
        main()
        return
    
def search_top_categories():
    categories = [
        "Home & Lifestyle", "Business", "Health", "Performing & Visual Arts",
        "Family & Education", "Holidays", "Music", "Community",
        "Hobbies", "Charity & Causes", "Food & Drink", "Science & Tech",
        "Sports & Fitness", "Travel & Outdoor", "Spirituality", "Nightlife",
        "Dating", "Film & Media", "Fashion", "Government", "Auto, Boat & Air",
        "School Activities"
    ]

    def display_categories():
        print("Please choose a category:")
        for i, category in enumerate(categories, 1):
            print(f"{i}. {category}")

    def get_user_choice():
        while True:
            user_input = input("Enter the number of your choice, or nothing to search all top events: ")
            if user_input == "":
                return None
            try:
                choice = int(user_input)
                if 1 <= choice <= len(categories):
                    return categories[choice - 1]
                else:
                    print(f"Please enter a number between 1 and {len(categories)}.\nOr enter nothing to search for all top categories in your location.")
            except ValueError:
                print("Invalid input. Please enter a number or press Enter to search for all top categories.")

    def generate_slug(category):
        category = category.replace('&', 'and')
        return re.sub(r'\s+', '-', category.strip().lower())

    country = 'united-kingdom'
    location = input('Enter location: ').replace(' ', '')

    display_categories()
    category = get_user_choice()

    if category is None:
        search_key = f'all_top_categories_for_{location}_{country}'
        spinner = Spinner("Fetching events...")
        spinner.start()

        unique_events = []
        page_number = 1

        try:
            if search_key in cache:
                spinner.stop()
                print("Using cached events from hashtable.")
                unique_events = cache[search_key]
            else:
                spinner.stop()
                spinner = Spinner("Scraping new events...")
                spinner.start()
                events_data, tags_counter, event_count = scrape_eventbrite_top_events_no_category(location, country, page_number)
                unique_events.extend(events_data)
                cache[search_key] = unique_events
        finally:
            spinner.stop()

        result = display_paginated_events(unique_events, search_key, 'eventbrite_top', location, None, country, None, page_number)
        if result == 'new_search':
            main()
            return
    else:
        search_key = f'{generate_slug(category)}_{location}_{country}'
        spinner = Spinner("Fetching events...")
        spinner.start()

        unique_events = []
        page_number = 1

        try:
            # Check if the search term is in the cache
            if search_key in cache:
                spinner.stop()
                print("Using cached events from hashtable.")
                unique_events = cache[search_key]
            else:
                spinner.stop()
                spinner = Spinner("Scraping new events...")
                spinner.start()
                events_data, tags_counter, event_count = scrape_eventbrite_top_events(country, location, generate_slug(category), page_number)
                unique_events.extend(events_data)
                cache[search_key] = unique_events
        finally:
            spinner.stop()

        result = display_paginated_events(unique_events, search_key, 'eventbrite_top', location, generate_slug(category), country, None, page_number)
        if result == 'new_search':
            main()
            return



def display_paginated_events(unique_events, search_key, user_selection, location=None, category_slug=None, country=None, product=None, page_number=1):
    page_size = 5
    total_events = len(unique_events)
    current_page = 0
    tags_counter = Counter()

    while current_page * page_size < total_events:
        start_index = current_page * page_size
        end_index = min(start_index + page_size, total_events)
        display_events(unique_events, start_index, end_index, search_key, tags_counter, user_selection)
        
        if end_index >= total_events:
            # Fetch more events if available
            page_number += 1
            spinner = Spinner("Fetching more events...")
            spinner.start()
            try:
                if user_selection == 'eventbrite':
                    events_data, new_tags_counter = scrape_eventbrite_events(location, product, page_number)
                elif user_selection == 'eventbrite_top':
                    events_data, new_tags_counter, event_count = scrape_eventbrite_top_events(country, location, category_slug, page_number)
                else:
                    break  # No more events to fetch

                if not events_data:
                    break  # No more events to fetch

                unique_events.extend(events_data)
                tags_counter.update(new_tags_counter)
                total_events = len(unique_events)
            finally:
                spinner.stop()

        user_input = input("Press 'Y' to see more events, 'S' to start a new search, or any other key to exit: ").strip().lower()
        if user_input == 's':
            return 'new_search'
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
        
    return 'done'
        
if __name__ == "__main__":
    main()