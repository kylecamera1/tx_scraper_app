from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import pandas as pd
import re

# Constants
URL = "https://www.txdirectory.com/login/"
USERNAME = "Kyle1!"
PASSWORD = "your_password"
SENATE_DIRECTORY_URL = "https://www.txdirectory.com/online/txsenate/"

# Set up Selenium WebDriver
options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def login():
    driver.get(URL)
    time.sleep(5)
    print("DEBUG: Loaded login page")
    
    try:
        email_field = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "exampleInputEmail1")))
        password_field = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "exampleInputPassword1")))
        login_button = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Log in Now')]")))
    except Exception as e:
        print(f"ERROR: Unable to locate login fields - {e}")
        return
    
    email_field.send_keys(USERNAME)
    password_field.send_keys(PASSWORD)
    login_button.click()
    time.sleep(5)
    print("DEBUG: Logged in successfully")

def scrape_senate_staff():
    staff_list = []
    driver.get(SENATE_DIRECTORY_URL)
    time.sleep(5)
    print("DEBUG: Loaded Senate directory")
    
    try:
        members = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.XPATH, "//table/tbody/tr/td[1]//a")))
        parties = driver.find_elements(By.XPATH, "//table/tbody/tr/td[1]/small")
    except Exception as e:
        print("DEBUG: No members found for Senate (Trying alternative method)")
        return staff_list
    
    for i in range(len(members)):
        name = members[i].text.strip()
        url = members[i].get_attribute("href")
        party = parties[i].text.strip() if i < len(parties) else "Unknown"
        
        if "(R)" not in party:
            print(f"DEBUG: Skipping non-Republican {name}")
            continue  
        
        print(f"DEBUG: Processing {name} - Party: Republican")
        driver.get(url)
        time.sleep(3)

        office_phone_match = re.search(r"\(512\) \d{3}-\d{4}", driver.page_source)
        office_phone = office_phone_match.group() if office_phone_match else "N/A"

        staffers = driver.find_elements(By.XPATH, "//table/tbody/tr/td[2]/a[contains(@href, 'staff=')]")
        titles = driver.find_elements(By.XPATH, "//table/tbody/tr/td[1]")  # Extract titles from member page
        staffer_data = [(staffers[j].text.strip(), titles[j].text.strip(), staffers[j].get_attribute("href")) for j in range(len(staffers))]

        for staff_name, member_page_title, staff_url in staffer_data:
            driver.get(staff_url)
            time.sleep(3)
            
            page_text = driver.find_element(By.TAG_NAME, "body").text
            
            # Extracting title (fallback to staffer page if missing from member page)
            title = member_page_title if member_page_title else "N/A"
            title_element = driver.find_elements(By.XPATH, "//h3")
            if title == "N/A" and title_element:
                title = title_element[0].text.strip().split("\n")[0]
            
            # Extracting emails
            email_elements = driver.find_elements(By.XPATH, "//a[contains(@href, 'mailto:')]")
            emails = [email.get_attribute("href").replace("mailto:", "").strip() for email in email_elements]
            if not emails:
                email_match = re.findall(r"[a-zA-Z0-9._%+-]+@senate\.texas\.gov", page_text)
                emails = email_match if email_match else ["N/A"]

            # Extracting phone numbers
            phone_numbers = re.findall(r"\(\d{3}\) \d{3}-\d{4}", page_text)
            filtered_numbers = [num for num in phone_numbers if num != "(512) 473-2447"]
            staff_phone = filtered_numbers[0] if filtered_numbers else office_phone
            phone_2 = filtered_numbers[1] if len(filtered_numbers) > 1 else "N/A"

            print(f"DEBUG: Extracted {staff_name} - Title: {title}, Emails: {emails}, Phones: {staff_phone}, {phone_2}")

            staff_list.append({
                "Member Office": name,
                "Chamber": "Senate",
                "Name": staff_name,
                "Title": title,
                "Email 1": emails[0] if len(emails) > 0 else "N/A",
                "Email 2": emails[1] if len(emails) > 1 else "N/A",
                "Phone Number 1": staff_phone,
                "Phone Number 2": phone_2
            })

            driver.get(url)
            time.sleep(3)

    return staff_list

def save_to_csv(data):
    if not data:
        print("DEBUG: No data to save.")
        return
    
    df = pd.DataFrame(data)
    df.to_csv("tx_senate_staff.csv", index=False)
    print("DEBUG: Data saved to tx_senate_staff.csv")

def main():
    login()
    staff_data = scrape_senate_staff()
    save_to_csv(staff_data)
    driver.quit()
    print("Scraping complete. Data saved to tx_senate_staff.csv")

if __name__ == "__main__":
    main()
