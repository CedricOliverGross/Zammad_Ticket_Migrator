import requests
import json
import os
import re

# API Endpoints
API_URL = "https://helpdesk.your.domain.com/api/v1/tickets" # Insert url for source system
ARTICLE_URL = "https://helpdesk.your.domain.com/api/v1/ticket_articles/by_ticket/{}?sort_by=created_at&order=desc" # Insert url for source system
ATTACHMENT_URL = "https://helpdesk.your.domain.com/api/v1/ticket_attachment/{}/{}/{}" # Insert url for source system

# Headers
HEADERS = {
    "Authorization": "Bearer YOUR-ACCESS-TOKEN", # Insert API token for source system
    "Content-Type": "application/json"
}

# Configuration
TICKET_ID_RANGE = range(11111, 22222)  # Ticket ID Range, add +1 to the second number
# Output Files
ATTACHMENTS_DIR = "attachments"
JSON_OUTPUT_FILE = "tickets_full_with_attachments.json"

# Ensure attachments directory exists
os.makedirs(ATTACHMENTS_DIR, exist_ok=True)

# Track downloaded attachments to prevent duplicates
downloaded_attachment_ids = set()

# Function to sanitize filenames
def sanitize_filename(filename):
    filename = re.sub(r'[<>:"/\\|?*]', "_", filename)  # Replace invalid characters
    filename = re.sub(r'[\s.]+$', "", filename)  # Remove trailing spaces/dots
    filename = re.sub(r'[#|]', "_", filename)  # Replace problematic symbols like #, |
    return filename[:200]  # Trim length to avoid OS limits

# Function to fetch articles (LIMIT to 50 newest)
def fetch_articles(ticket_id):
    response = requests.get(ARTICLE_URL.format(ticket_id), headers=HEADERS)
    if response.status_code == 200:
        articles = response.json()[:50]  # Only keep the 50 newest articles
        for article in articles:
            article_id = article.get("id")
            article["attachments"] = fetch_attachments(ticket_id, article_id, article.get("attachments", []))
        return articles
    else:
        print(f"⚠️ Warning: Could not fetch articles for ticket {ticket_id}")
        return []

# Function to fetch attachments
def fetch_attachments(ticket_id, article_id, attachments):
    downloaded_attachments = []
    for attachment in attachments:
        attachment_id = attachment.get("id")

        # Skip if already downloaded
        if attachment_id in downloaded_attachment_ids:
            print(f"🔄 Skipping duplicate attachment: {attachment.get('filename')}")
            continue

        file_name = sanitize_filename(attachment.get("filename"))
        file_path = os.path.join(ATTACHMENTS_DIR, file_name)
        url = ATTACHMENT_URL.format(ticket_id, article_id, attachment_id)

        response = requests.get(url, headers=HEADERS, stream=True)
        if response.status_code == 200:
            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"✅ Downloaded attachment: {file_name}")
            attachment["local_path"] = file_path

            # Mark attachment as downloaded
            downloaded_attachment_ids.add(attachment_id)

            downloaded_attachments.append(attachment)
        else:
            print(f"❌ Failed to download attachment {file_name}: {response.status_code}")

    return downloaded_attachments

# Fetch tickets and process them
all_tickets = []

for ticket_id in TICKET_ID_RANGE:
    response = requests.get(f"{API_URL}/{ticket_id}", headers=HEADERS)
    
    if response.status_code == 200:
        ticket = response.json()
        ticket["articles"] = fetch_articles(ticket_id)
        all_tickets.append(ticket)
        print(f"✅ Fetched ticket {ticket_id}, total tickets so far: {len(all_tickets)}")
    else:
        print(f"❌ Error fetching ticket {ticket_id}: {response.status_code} {response.text}")

# Save tickets to the configured JSON file
with open(JSON_OUTPUT_FILE, "w", encoding="utf-8") as file:
    json.dump(all_tickets, file, indent=4)

print(f"🎉 Tickets with articles and attachments saved to {JSON_OUTPUT_FILE}")