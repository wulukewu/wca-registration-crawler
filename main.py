import os
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from dotenv import load_dotenv
load_dotenv()

# Define ANSI escape codes for colors
class Colors:
    INFO = '\033[94m'  # Blue
    WARN = '\033[93m'  # Yellow
    ERROR = '\033[91m'  # Red
    END = '\033[0m'  # Reset to default color

# Define print functions with colors
def print_info(message):
    print(f'{Colors.INFO}[INFO]\t{message}{Colors.END}')
def print_warn(message):
    print(f'{Colors.WARN}[WARN]\t{message}{Colors.END}')
def print_error(message):
    print(f'{Colors.ERROR}[ERROR]\t{message}{Colors.END}')

def main():

    # Set up ChromeDriver with options
    options = webdriver.ChromeOptions()
    options.add_argument('--disable-blink-features=AutomationControlled')
    if no_ui:
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920x1080')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--allow-insecure-localhost')

    # Initialize the ChromeDriver
    driver = webdriver.Chrome(options=options)

    # Print the Chrome version and ChromeDriver version
    print_info(f'Chrome version: {driver.capabilities['browserVersion']}')
    print_info(f'ChromeDriver version: {driver.capabilities['chrome']['chromedriverVersion']}')

    # Open the URL
    driver.get('https://cubing-tw.net/event/')

    # Wait for the register to be available
    if no_ui:
        start_time = time.time()
    while True:
        try:
            WebDriverWait(driver, .1).until(EC.presence_of_element_located((By.CLASS_NAME, 'btn-secondary')))
            print_info('Register time is not available yet')
        except Exception as e:
            print_info('Register time is available')
            
            try:
                WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, 'btn-primary')))
                register_link = driver.find_element(By.CLASS_NAME, 'btn-primary').get_attribute('href')
                print_info(f'Found register link: {register_link}')
                break
            except Exception as e:
                print_warn(f'Failed to find register link')
                print_info('Retrying in 5 seconds...')

        finally:
            if no_ui:
                if time.time() - start_time > 5 * 60 * 60:
                    print_error('Cannot find the register link')
                    print_error('Exiting the program...')
                    driver.quit()
                    return 'Cannot find the register link'

            print_info('Refreshing the page...')
            driver.refresh()

    # Open the register link
    driver.get(register_link)

    # Enter the WCA ID
    try:
        WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.ID, 'WCAID_input')))
        driver.find_element(By.ID, 'WCAID_input').clear()
        driver.find_element(By.ID, 'WCAID_input').send_keys(wca_id)
        print_info(f'Entered WCA ID: {wca_id}')
        driver.find_element(By.ID, 'WCAID_Button').click()
        print_info('Clicked the \'GO!\' button')

    except Exception as e:
        if no_ui:
            print_error('Cannot find the WCA ID input')
            print_error('Exiting the program...')
            driver.quit()
            return 'Cannot find the WCA ID input'

        print_warn('Failed to enter WCA ID')
        print_info('Please enter the WCA ID manually')
        input('Press Enter to continue...')

    # Enter the birthday
    try:
        WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.ID, 'div_birthday')))

        select_year = driver.find_element(By.ID, 'form_birthday_year')
        for option in select_year.find_elements(By.TAG_NAME, 'option'):
            if option.text == birthday_year:
                option.click()
                break
        print_info(f'Selected birthday year: {birthday_year}')

        select_month = driver.find_element(By.ID, 'form_birthday_month')
        for option in select_month.find_elements(By.TAG_NAME, 'option'):
            if option.text == birthday_month:
                option.click()
                break
        print_info(f'Selected birthday month: {birthday_month}')

        select_day = driver.find_element(By.ID, 'form_birthday_day')
        for option in select_day.find_elements(By.TAG_NAME, 'option'):
            if option.text == birthday_day:
                option.click()
                break
        print_info(f'Selected birthday day: {birthday_day}')

    except Exception as e:
        if no_ui:
            print_error('Cannot find the birthday input')
            print_error('Exiting the program...')
            driver.quit()
            return 'Cannot find the birthday input'

        print_warn('Failed to enter birthday')
        print_info('Please enter the birthday manually')
        input('Press Enter to continue...')

    # Enter the email
    try:
        WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.ID, 'form_email')))
        driver.find_element(By.ID, 'form_email').clear()
        driver.find_element(By.ID, 'form_email').send_keys(email)
        print_info(f'Entered email: {email}')

    except Exception as e:
        if no_ui:
            print_error('Cannot find the email input')
            print_error('Exiting the program...')
            driver.quit()
            return 'Cannot find the email input'

        print_warn('Failed to enter email')
        print_info('Please enter the email manually')
        input('Press Enter to continue...')

    # Select all event options
    try:
        WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.ID, 'div_events')))
        event_checkboxes = driver.find_elements(By.CSS_SELECTOR, '#div_events .form-check-input')
        for checkbox in event_checkboxes:
            if not checkbox.is_selected():
                checkbox.click()
        print_info('Selected all event options')

    except Exception as e:
        if no_ui:
            print_error('Cannot find the event options')
            print_error('Exiting the program...')
            driver.quit()
            return 'Cannot find the event options'

        print_warn('Failed to select event options')
        print_info('Please select the event options manually')
        input('Press Enter to continue...')

    # Enter the phone number
    if phone:
        try:
            WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.ID, 'form_phone')))
            driver.find_element(By.ID, 'form_phone').clear()
            driver.find_element(By.ID, 'form_phone').send_keys(phone)
            print_info(f'Entered phone number: {phone}')
        except Exception as e:
            print_warn('Failed to enter phone number')
            print_info('Skipping the phone number')
    else:
        print_info('Skipping the phone number')

    # Click the 'Preview' button
    try:
        WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.ID, 'BTN_Preview')))
        driver.find_element(By.ID, 'BTN_Preview').click()
        print_info('Clicked the \'Preview\' button')
    except Exception as e:
        if no_ui:
            print_error('Cannot find the \'Preview\' button')
            print_error('Exiting the program...')
            driver.quit()
            return 'Cannot find the \'Preview\' button'

        print_warn('Failed to click the \'Preview\' button')
        print_info('Please click the \'Preview\' button manually')
        input('Press Enter to continue...')

    # Click the 'Send' button
    try:
        WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.ID, 'BTN_Send')))
        driver.find_element(By.ID, 'BTN_Send').click()
        print_info('Clicked the \'Send\' button')
    except Exception as e:
        if no_ui:
            print_error('Cannot find the \'Send\' button')
            print_error('Exiting the program...')
            driver.quit()
            return 'Cannot find the \'Send\' button'

        print_warn('Failed to click the \'Send\' button')
        print_info('Please click the \'Send\' button manually')
        input('Press Enter to continue...')

    # Quit the ChromeDriver when Ctrl+C is pressed
    print_info('Finished all tasks')
    if no_ui:
        driver.quit()
        return 'Run Successfully'

    print_info('(Press Ctrl+C to quit)')
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print_info('Ctrl+C pressed')
        print_info('Bye!')
        driver.quit()
        return 'Run Successfully'

# Check if the script is running in a user interface
no_ui = os.getenv('NO_UI', 'true').lower() == 'false'
print_info(f'Not running in user interface: {no_ui}')

# User settings
try: wca_id = os.environ['WCA_ID']
except: wca_id = input('Enter your WCA ID: ').strip()
try: birthday_year = os.environ['BIRTHDAY_YEAR']
except: birthday_year = input('Enter your birthday year: ').strip()
try: birthday_month = os.environ['BIRTHDAY_MONTH']
except: birthday_month = input('Enter your birthday month: ').strip()
try: birthday_day = os.environ['BIRTHDAY_DAY']
except: birthday_day = input('Enter your birthday day: ').strip()
try: email = os.environ['EMAIL']
except: email = input('Enter your email: ').strip()
try: phone = os.environ['PHONE']
except: phone = input('(Optional, leave blank if not required)\nEnter your phone number: ').strip()

if __name__ == '__main__':
    return_message = main()