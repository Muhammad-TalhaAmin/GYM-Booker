from selenium import webdriver
from selenium.common import NoSuchElementException, TimeoutException,StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
import os
from selenium.webdriver.support.ui import WebDriverWait
import time

# Target class time to verify later in My Bookings page
TIME="8:00 AM"

# Counters for tracking automation results
CLASSES_BOOKED=0
CLASSES_WAITLISTED=0
AlREADY_JOINED=0
VERIFIED_CLASSES=0

# Login credentials
ACCOUNT_EMAIL="YOUR_EMAIL_HERE"
ACCOUNT_PASSWORD="YOUR_PASSWORD_HERE"

# Gym website URL
GYM_URL="https://appbrewery.github.io/gym/"

# Create a dedicated Chrome profile folder
# so cookies/session data can be reused
user_data_dir=os.path.join(os.getcwd(),"chrome_profile")

# Chrome options
chrome_options = webdriver.ChromeOptions()

# Keep browser open after script finishes
chrome_options.add_experimental_option("detach", True)

# Use custom Chrome profile
chrome_options.add_argument(f"--user-data-dir={user_data_dir}")

# Launch Chrome
driver=webdriver.Chrome(options=chrome_options)

# Open gym website
driver.get(GYM_URL)

# Stores booking actions for summary output
classes_processed=[]

def login():
    # Wait until login button becomes clickable
    login_button=WebDriverWait(driver,10).until(
        ec.element_to_be_clickable((By.ID, "login-button"))
    )
    login_button.click()

    # Wait for email field
    email_input=WebDriverWait(driver,2).until(
        ec.presence_of_element_located((By.XPATH, "//*[@id='email-input']"))
    )

    # Wait for password field
    password=WebDriverWait(driver,2).until(
        ec.presence_of_element_located((By.XPATH, "//*[@id='password-input']"))
    )

    # Enter email
    email_input.clear()
    email_input.send_keys(ACCOUNT_EMAIL)

    # Enter password
    password.clear()
    password.send_keys(ACCOUNT_PASSWORD)

    # Submit login form
    submit_button=driver.find_element(By.ID,value="submit-button")
    submit_button.click()

    # Wait until schedule page loads
    WebDriverWait(driver,2).until(
        ec.presence_of_element_located((By.ID, "schedule-page"))
    )

def click_button(button,description=None):
    # Click booking/waitlist button
    button.click()

    # Wait until button text changes to expected state
    # e.g. "Booked" or "Waitlisted"
    WebDriverWait(driver,5).until(
        lambda d: button.text == description
    )

def book_classes(day,time_):
    # Ensure schedule page is loaded
    WebDriverWait(driver,2).until(
        ec.presence_of_element_located((By.ID,"schedule-page"))
    )

    # Get all class cards
    classes_cards=driver.find_elements(
        By.CSS_SELECTOR,
        value="div[id^='class-card-']"
    )

    global CLASSES_BOOKED,CLASSES_WAITLISTED,AlREADY_JOINED

    for card in classes_cards:
        try:
            # Find parent day container for the class
            class_date=card.find_element(
                By.XPATH,
                value="./ancestor::div[contains(@id,'day-group-')]"
            )

            # Extract day name (Friday, Saturday, etc.)
            class_day=class_date.find_element(
                By.TAG_NAME,
                value="h2"
            ).text

            # Check if current card belongs to desired day
            if day in class_day.lower():

                # Extract class time
                time_text = card.find_element(
                    By.CSS_SELECTOR,
                    "p[id^='class-time-']"
                ).text

                class_info=f"{class_day},{time_text}"

                # Check if time matches target time
                if time_ in time_text:

                    # Extract class name
                    class_name = card.find_element(
                        By.CSS_SELECTOR,
                        "h3[id^='class-name-']"
                    ).text

                    # Find booking button
                    button = card.find_element(
                        By.CSS_SELECTOR,
                        "button[id^='book-button-']"
                    )

                    button_text=button.text

                    # Already booked
                    if "Booked" in button_text:
                        print(f"\n{class_name} on {class_day} already booked.")

                        classes_processed.append(
                            f"[Already Booked]{class_name} on {class_info}"
                        )

                        AlREADY_JOINED+=1

                    # Available for booking
                    elif "Book Class" in button_text:

                        retry(
                            lambda: click_button(button,"Booked"),
                            description=f"Booking"
                        )

                        CLASSES_BOOKED+=1

                        classes_processed.append(
                            f"[Booked]{class_name} on {class_info}"
                        )

                        print(f"\n✓ Booked: {class_name} on {class_day}")

                    # Already waitlisted
                    elif "Waitlisted" in button_text:

                        classes_processed.append(
                            f"[Already Waitlisted]{class_name} on {class_info}"
                        )

                        print(
                            f"\n✓ Already Waitlisted: {class_name} on {class_day}"
                        )

                        AlREADY_JOINED+=1

                    # Join waitlist
                    elif "Join Waitlist" in button_text:

                        classes_processed.append(
                            f"[Waitlisted]{class_name} on {class_info}"
                        )

                        retry(
                            lambda: click_button(button,"Waitlisted"),
                            description=f"Joining waitlist"
                        )

                        print(
                            "\nJoined waitlist for class: ",
                            class_name,
                            " on ",
                            class_day,
                            ""
                        )

                        CLASSES_WAITLISTED+=1

        # Skip card if DOM refreshed and element became stale
        except StaleElementReferenceException:
            continue

def get_bookings():
    global VERIFIED_CLASSES,CLASSES_BOOKED,CLASSES_WAITLISTED,AlREADY_JOINED

    try:
        # Wait for My Bookings link
        WebDriverWait(driver,5).until(
            ec.presence_of_element_located((By.ID,"my-bookings-link"))
        )

        # Open My Bookings page
        bookings=driver.find_element(By.ID,value="my-bookings-link")
        bookings.click()

        # Wait until bookings page loads
        WebDriverWait(driver,5).until(
            ec.presence_of_element_located((By.ID,"my-bookings-page"))
        )

        # Get all booking cards
        cards=driver.find_elements(
            By.CSS_SELECTOR,
            value="div[id*='card-']"
        )

        # Safety check
        if not bookings:
            print("No bookings found")
            return

        print("\n--------------Verifying Bookings---------------")

        # Verify matching bookings
        for booking in cards:

            when_class=booking.find_element(
                By.XPATH,
                value=".//p[strong[text()='When:']]"
            )

            when_text=when_class.text

            # Only verify selected days and target time
            if ("Sat" in when_text or "Fri" in when_text) and TIME in when_text:

                class_verified=booking.find_element(
                    By.TAG_NAME,
                    value="h3"
                ).text

                print(f"✅Verified booking: {class_verified}")

                VERIFIED_CLASSES+=1

    except (NoSuchElementException,StaleElementReferenceException):
        print("No bookings found")

    # Calculate total processed classes
    TOTAL_CLASSES=(
        CLASSES_BOOKED+
        CLASSES_WAITLISTED+
        AlREADY_JOINED
    )

    # Compare verified count against processed count
    if VERIFIED_CLASSES==TOTAL_CLASSES:
        print(
            f"Total Bookings verified✅: "
            f"{VERIFIED_CLASSES}/{TOTAL_CLASSES}"
        )
    else:
        print(
            f"Mismatched ❌: "
            f"{TOTAL_CLASSES-VERIFIED_CLASSES} Missing"
        )

    # Summary output
    print("\n--- BOOKING SUMMARY ---")
    print(f"Classes booked: {CLASSES_BOOKED}")
    print(f"Waitlists joined: {CLASSES_WAITLISTED}")
    print(f"Already booked/waitlisted: {AlREADY_JOINED}")

    print(
        f"\nTotal Tuesday,Thursday classes processed: "
        f"{CLASSES_BOOKED+CLASSES_WAITLISTED+AlREADY_JOINED}\n"
    )

    # Print all processed classes
    for item in classes_processed:
        print(item)

def retry(func, retries=7, description=None):
    # Retry wrapper for transient Selenium failures
    for i in range(retries):
        try:
            return func()

        # Retry on timeout or stale element
        except (TimeoutException,StaleElementReferenceException):

            # Re-raise exception if all retries exhausted
            if i == retries - 1:
                raise

            # Small delay before retrying
            time.sleep(1)

# Login
retry(login, description="Login")

# Book Friday 8 AM classes
book_classes("fri","8:00 AM")

# Book Saturday 8 AM classes
book_classes("sat","8:00 AM")

# Verify bookings
retry(get_bookings,description="Get bookings")