import gspread

gc = gspread.service_account(filename="creds.json")

sheet = gc.open('Project3Python').sheet1


sheet.update_cell(1, 1, 'I just wrote a message to google!')