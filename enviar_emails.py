# send_emails.py (FINAL VERSION - Adjusted for Secondary Emails)

import os
import smtplib
import time
import pandas as pd
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

# --- CONFIGURATION ---
try:
    from config import SENDER_EMAIL, APP_PASSWORD
except ImportError:
    print("CRITICAL ERROR: config.py file not found or is missing SENDER_EMAIL/APP_PASSWORD.")
    exit()

# --- CUSTOMIZE YOUR EMAIL (As provided by you) ---
CV_FILENAME = "CV.pdf" 
SUBJECT = "Candidatura para puesto en {clinic_name} - Juan García"
EMAIL_BODY = """
Hola, equipo de {clinic_name},

Le escribo para ofrecer mis servicios en caso de que tenga una vacante como odontólogo general.

Soy Juan García, me he graduado este año de odontología en ...

"""

def get_secondary_recipient_data(csv_file):
    """
    Reads the CSV, finds rows with multiple emails, and returns a list of all emails
    EXCEPT the first one in each list.
    """
    print(f"Reading data from {csv_file} to find secondary emails...")
    try:
        df = pd.read_csv(csv_file)
        if 'Email' not in df.columns or 'Name' not in df.columns:
            print(f"ERROR: The CSV must have 'Email' and 'Name' columns.")
            return []
        
        # --- ADJUSTED FILTERING LOGIC ---
        # 1. Filter out rows where the email is 'Not found'.
        df_valid = df[df['Email'].str.lower() != 'not found'].copy()
        
        # 2. Find only the rows that contain multiple emails (i.e., have a comma).
        df_multiple = df_valid[df_valid['Email'].str.contains(',')].copy()
        
        if df_multiple.empty:
            print("No rows with multiple emails were found.")
            return []
            
        print(f"Found {len(df_multiple)} clinics with more than one email address.")
        
        recipients_to_send = []
        # 3. Iterate through these specific rows.
        for index, row in df_multiple.iterrows():
            clinic_name = row['Name']
            # Split emails into a list
            all_emails = [email.strip() for email in row['Email'].split(',')]
            
            # Get all emails from the second one onwards
            secondary_emails = all_emails[1:]
            
            for email in secondary_emails:
                recipients_to_send.append({'Name': clinic_name, 'Email': email})
        
        # 4. Remove any duplicate secondary emails across the entire list
        if not recipients_to_send:
            return []
        
        final_df = pd.DataFrame(recipients_to_send).drop_duplicates(subset=['Email'])
        final_recipients = final_df.to_dict('records')
        
        print(f"Found {len(final_recipients)} unique secondary email addresses to process.")
        return final_recipients

    except FileNotFoundError:
        print(f"ERROR: The file '{csv_file}' was not found.")
        return []
    except Exception as e:
        print(f"An error occurred while reading the CSV file: {e}")
        return []

def send_email(recipient_email, clinic_name):
    """Constructs and sends a single, personalized email."""
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = recipient_email
        msg['Subject'] = SUBJECT.format(clinic_name=clinic_name)
        body_personalized = EMAIL_BODY.format(clinic_name=clinic_name)
        msg.attach(MIMEText(body_personalized, 'plain'))

        with open(CV_FILENAME, 'rb') as f:
            attach = MIMEApplication(f.read(), _subtype='pdf')
            attach.add_header('Content-Disposition', 'attachment', filename=str(CV_FILENAME))
            msg.attach(attach)

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"  -> Successfully sent to {recipient_email}")
        return True

    except smtplib.SMTPAuthenticationError:
        print("\nCRITICAL ERROR: SMTP Authentication Failed. Check your App Password.")
        return False
    except Exception as e:
        print(f"  -> FAILED to send to {recipient_email}. Error: {e}")
        return True

if __name__ == "__main__":
    if not os.path.exists(CV_FILENAME):
        print(f"CRITICAL ERROR: The CV file '{CV_FILENAME}' was not found.")
        exit()

    # --- MAIN EXECUTION BLOCK ---
    # Call the new function to get only the secondary emails
    recipients = get_secondary_recipient_data('dental_clinics_madrid_places.csv')

    if not recipients:
        print("No new secondary emails found to send. Exiting.")
        exit()
        
    print("\n--- Starting Email Sending Process for SECONDARY EMAILS ---")
    
    for i, recipient in enumerate(recipients):
        clinic_name = recipient['Name'].strip()
        email_address = recipient['Email'].strip()
        
        print(f"Sending email {i+1} of {len(recipients)} to: {email_address} (Clinic: {clinic_name})")
        
        if not send_email(email_address, clinic_name):
            break
        
        print("    (Waiting 10 seconds before next email...)")
        time.sleep(10)
        
    print("\n--- Email Sending Process Finished ---")