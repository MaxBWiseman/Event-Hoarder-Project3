import csv
import os
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
            'show_date_time': event.get('show_date_time', 'N/A'),
            'summary': event.get('summary', 'N/A'),
            'event_price': event.get('event_price', 'N/A')
        }
        
        collection.update_one({'url': unique_id}, {'$set': event_data}, upsert=True)


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
    
    

def scrape_eventbrite_events(location, day, product, page_number, start_date, end_date):
    url = f'https://www.eventbrite.com/d/united-kingdom--{location}/events--{day}/{product}/?page={page_number}&start_date={start_date}&end_date={end_date}'
    
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
        # Code with help from Co-Pilot
        if location_div:
            event_location = location_div.get_text(strip=True)
            event_location= re.sub(r'Show map$', '', event_location)
        else:
            event_location = 'No location available'
        # End of Co-Pilot code, this code removes the 'Show map' text from the location
        # even if its preceeded by another word, the issue was "United KingdomShow map"

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

def scrape_eventbrite_top_events(country, day, location, category_slug, page_number, start_date, end_date):
    url = f'https://www.eventbrite.co.uk/d/{country}--{location}/{category_slug}--events--{day}/?page={page_number}&start_date={start_date}&end_date={end_date}'
    
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
         # Code with help from Co-Pilot
        if location_div:
            event_location = location_div.get_text(strip=True)
            event_location= re.sub(r'Show map$', '', event_location)
        else:
            event_location = 'No location available'
        # End of Co-Pilot code, this code removes the 'Show map' text from the location
        # even if its preceeded by another word, the issue was "United KingdomShow map"
        
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
            'show_date_time': event_date_time,
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
         # Code with help from Co-Pilot
        if location_div:
            event_location = location_div.get_text(strip=True)
            event_location= re.sub(r'Show map$', '', event_location)
        else:
            event_location = 'No location available'
        # End of Co-Pilot code, this code removes the 'Show map' text from the location
        # even if its preceeded by another word, the issue was "United KingdomShow map"
        
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
            'show_date_time': event_date_time,
            'event_date_time': date_parsed,
            'summary': event_summary,
            'event_price': event_price
        })

        event_data.append(event_info)
    return event_data

def save_to_csv(events):
    directory = 'static'
    if not os.path.exists(directory):
        os.makedirs(directory)
    
    file_name = os.path.join(directory, 'collected_events.csv')
    file_exists = os.path.exists(file_name)
    
    fields = ['name', 'location', 'show_date_time', 'event_price', 'summary', 'url']

    with open(file_name, 'a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fields)

        if not file_exists:
            writer.writeheader()

        for event in events:
            filtered_event = {field: event[field] for field in fields if field in event}
            # this will only include the fields that are in the fields list above, so that
            # fields that only have a programmatic purpose are not included in the CSV
            # it works by creating a new dictionary with only the fields that are in the fields list
            writer.writerow(filtered_event)

    print(f"Events saved to {file_name}")
    return

def collection_menu():
    while True:
        print("\nChoose an option to manipulate events or print to CSV:")
        print("1. View all searched events")
        print("2. View recent searches")
        print("3. something")
        print("4. Main Menu")
        print("#. Clear Database")
        choice = input("Enter your choice: ").strip()

        if choice == '1':
            view_all_events()
        elif choice == '2':
            search_events_in_collection()
        elif choice == '3':
            something()
        elif choice == '4':
            print("Going back to the main menu.")
            main()
        elif choice == '#':
            collection.delete_many({})
            print('-------------------------------------\nDatabase cleared\n-------------------------------------.')
            main()
        else:
            print("Invalid choice. Please try again.")

def get_unique_search_keys():
    pipeline = [
        {'$group': {'_id': '$search_key'}},
    ]
    unique_search_keys = list(collection.aggregate(pipeline))
    return [key['_id'] for key in unique_search_keys]
# This function will return a list of unique search keys from the mongodb collection
# The pipeline will group the documents by the search_key field and return only unique values

def compare_events(events):
    if len(events) < 2:
        print('Not enough events to compare.')
        return
    
    print('What would you like to compare?')
    print('1. Cheapest/Free events')
    print('2. Most expensive events')
    print('3. Closest distance events')
    print('4. Events happening soon')
    print('5. Compare organizers')
    print('5. Main Menu')
    choice = input('Enter your choice: ').strip()
    
    

def event_manipulation_menu(events):
    while True:
        print('\nChoose an option to manipulate the events data:')
        print('1. Compare events')
        print('2. Sort events')
        print('3. Filter events')
        print('4. Main Menu')
        choice = input('Enter your choice: ').strip()
        
        if choice == '1':
            compare_events(events)
        elif choice == '2':
            sort_events(events)
        elif choice == '3':
            filter_events(events)
        elif choice == '4':
            print('Returning to the main menu.')
            main()

def search_events_in_collection():
    unique_search_keys = get_unique_search_keys()
    user_selection = 'data-manipulation'
    
    if len(unique_search_keys) == 0:
        print("No events found in the collection.")
        return
    
    print("-------------------------------------\nChoose a search key:")
    for i, key in enumerate(unique_search_keys, 1):
        print(f"{i}. {key}")
        
    choice = input("\nEnter the number of your choice: ").strip()
    all_events = list(collection.find({'search_key': unique_search_keys[int(choice) - 1]}))
    
    if not all_events:
        print("No events found for the selected search key.")
        return
    
    display_events(all_events, 0, len(all_events), user_selection, search_key=unique_search_keys[int(choice) - 1])

    save_choice = input('-------------------------------------\nWould you like to save the events to a CSV file (C) or perform tasks? (T): ').strip().lower()
    if save_choice == 'y':
        try:
            save_to_csv(all_events)
        except Exception as e:
            print(f"Error saving events to CSV: {e}")
    else:
        event_manipulation_menu(all_events)


def view_all_events():
    all_events = list(collection.find({}))
    user_selection = 'data-manipulation'
    if len(all_events) == 0:
        print('No events found')
        return
    
    result = display_events(all_events, 0, len(all_events), user_selection, search_key='None')
    
    save_choice = input('-------------------------------------\nWould you like to save the events to a CSV file (C) or perform tasks? (T): ').strip().lower()
    if save_choice == 'y':
        try:
            save_to_csv(all_events)
        except Exception as e:
            print(f"Error saving events to CSV: {e}")
    else:
        event_manipulation_menu(all_events)
        
    

def display_events(events, start_index, end_index, user_selection, search_key):
    collected_events = events[start_index:end_index]
    for data in collected_events:
        if isinstance(data, dict):
            location = data.get('location', 'No location available')
            show_date_time = data.get('show_date_time', 'No date and time available')
            if location != 'No location available' and show_date_time != 'No date and time available':
                print(f'-------------------------------------\n{data["name"]},\n{data["location"]}\nDate & Time: {data["show_date_time"]}\nPrice: {data["event_price"]}')
            else:
                continue # Skip invalid event data
        else:
            continue # Skip invalid event data
            
    if user_selection == 'data-manipulation':
        return
    elif user_selection == 'eventbrite' or user_selection == 'eventbrite_top':
        save_to_mongodb(collection, search_key, collected_events)

    # Cache the events in the hashtable
    cache[search_key] = events
    
def search_events():
    product = input('Enter event type or name: ').replace(' ', '%20')
    location = input('Enter location: ').replace(' ', '%20')
    print('Would you like to enter a date? (Y/N)')
    date_choice = input('Enter your choice: ').strip().lower()
    
    start_date = ''
    end_date = ''
    day = ''
    
    if date_choice == 'y':
        print('Please enter an option: ')
        print('1. Today')
        print('2. Tomorrow')
        print('3. This weekend')
        print('4. Pick a date')
        day = input('Enter the number of choice: ')
        if day == '1':
            day = 'today'
        elif day == '2':
            day = 'tomorrow'
        elif day == '3':
            day = 'this-weekend'
        else:
            start_date = input('Enter the start date (YYYY-MM-DD): ')
            end_date = input('Enter the end date (YYYY-MM-DD): ')
        
    search_key = f'{product}_{location}'
    
    user_selection = 'eventbrite'

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
            events_data, tags_counter = scrape_eventbrite_events(location, day, product, page_number, start_date, end_date)
            unique_events.extend(events_data)
            cache[search_key] = unique_events
    finally:
        spinner.stop()

    result = display_paginated_events(unique_events, search_key, user_selection, location, product, page_number)
    
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
    
    user_selection = 'eventbrite_top'

    def display_categories():
        print("\nPlease choose a category:")
        for i, category in enumerate(categories, 1):
            print(f"{i}. {category}")

    def get_user_choice():
        while True:
            user_input = input(f"Enter the number of your choice, or nothing to search all top events in {location}: ")
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
    print('Would you like to enter a date? (Y/N)')
    date_choice = input('Enter your choice: ').strip().lower()
    
    start_date = ''
    end_date = ''
    day = ''
    
    if date_choice == 'y':
        print('Please enter an option: ')
        print('1. Today')
        print('2. Tomorrow')
        print('3. This weekend')
        print('4. Pick a date')
        day = input('Enter the number of choice: ')
        if day == '1':
            day = 'today'
        elif day == '2':
            day = 'tomorrow'
        elif day == '3':
            day = 'this-weekend'
        else:
            start_date = input('Enter the start date (YYYY-MM-DD): ')
            end_date = input('Enter the end date (YYYY-MM-DD): ')

    display_categories()
    category = get_user_choice()

    
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
            events_data, tags_counter, event_count = scrape_eventbrite_top_events(country, day, location, generate_slug(category), page_number, start_date, end_date)
            unique_events.extend(events_data)
            cache[search_key] = unique_events
    finally:
        spinner.stop()

    result = display_paginated_events(unique_events, search_key, user_selection, location, generate_slug(category), country, page_number)
        
    if result == 'new_search':
        main()
        return


def search_top_events():
    
    country = 'united-kingdom'
    location = input('Enter location: ').replace(' ', '')
    search_key = f'all_top_events_{location}_{country}'
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
            events_data = scrape_eventbrite_top_events_no_category(location, country)
            unique_events.extend(events_data)
            cache[search_key] = unique_events
    finally:
        spinner.stop()

    result = display_paginated_events(unique_events, search_key, 'eventbrite_top', location, country, page_number)
    if result == 'new_search':
        main()
        return


def main():
    welcome = 0
    while True:
        if welcome < 1:
            print("-------------------------------------\nWelcome to Event Hoarder!\nSearch for events and they will be automatically be saved to a database to\nbe used for printing to CSV or performing data manipulation tasks\n-------------------------------------")
            welcome += 1
        print("\nChoose an option:")
        print("1. Quick Search & Collect")
        print("2. Search & Collect Top Events")
        print("3. Search & Collect Top Categories")
        print("4. View Collected Events")
        print("5. Exit")
        print("#. Clear Database")
        choice = input("Enter your choice: ").strip()

        if choice == '1':
            search_events()
        elif choice == '2':
            search_top_events()
        elif choice == '3':
            search_top_categories()
        elif choice == '4':
            collection_menu()    
        elif choice == '5':
            print("Exiting the program.")
            sys.exit()
        elif choice == '#':
            collection.delete_many({})
            print('-------------------------------------\nDatabase cleared\n-------------------------------------.')
            main()
        else:
            print("\nInvalid choice. Please try again.")


def display_paginated_events(unique_events, search_key, user_selection, location=None, country=None, category_slug=None, product=None, page_number=1):
    page_size = 5
    total_events = len(unique_events)
    current_page = 0
    tags_counter = Counter()

    while current_page * page_size < total_events:
        start_index = current_page * page_size
        end_index = min(start_index + page_size, total_events)
        display_events(unique_events, start_index, end_index, user_selection, search_key)
        
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

        user_input = input("-------------------------------------\nPress 'Y' to see more events, 'S' to start a new search, or any other key to exit: ").strip().lower()
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