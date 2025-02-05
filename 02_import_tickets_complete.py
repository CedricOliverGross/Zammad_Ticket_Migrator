import requests
import json
import os
import base64
import re

# Zammad API details
PROD_API_URL = "https://helpdesk.your.domain.com/api/v1" # Insert url of target system
HEADERS_PROD = {
    "Authorization": "Bearer YOUR-ACCESS-TOKEN", # Insert API token for target system
    "Content-Type": "application/json"
}

# Configuration
# Input Files
TICKETS_FILE = "tickets_full_with_attachments.json"
ATTACHMENTS_DIR = "attachments"
# Output Files
ID_MAPPING_FILE = "id_mapping.json"

# Load tickets from JSON
with open(TICKETS_FILE, "r", encoding="utf-8") as file:
    tickets = json.load(file)

# Load existing ID mapping if available
if os.path.exists(ID_MAPPING_FILE):
    with open(ID_MAPPING_FILE, "r", encoding="utf-8") as file:
        id_mapping = json.load(file)
else:
    id_mapping = {}

# Encode file as Base64
def encode_file_to_base64(file_path):
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return None

    with open(file_path, "rb") as f:
        encoded_string = base64.b64encode(f.read()).decode("utf-8")
        return encoded_string

# Function to sanitize filenames (same as in export script)
def sanitize_filename(filename):
    filename = re.sub(r'[<>:"/\\|?*]', "_", filename)  # Replace invalid characters
    filename = re.sub(r'[\s.]+$', "", filename)  # Remove trailing spaces/dots
    filename = re.sub(r'[#|]', "_", filename)  # Replace problematic symbols like #, |
    return filename[:200]  # Trim length to avoid OS limits

# Modify `create_article()` function
def create_article(ticket_id, article, old_ticket_id):
    article_payload = {k: v for k, v in article.items() if k not in ["id", "ticket_id", "attachments"]}

    # Process attachments
    attachments_payload = []
    for attachment in article.get("attachments", []):
        original_filename = attachment["filename"]  # Get original name
        sanitized_filename = sanitize_filename(original_filename)  # Sanitize it
        file_path = os.path.join(ATTACHMENTS_DIR, sanitized_filename)  # Use sanitized name
        
        encoded_data = encode_file_to_base64(file_path)

        if encoded_data:
            attachments_payload.append({
                "filename": sanitized_filename,  # Store the sanitized filename
                "data": encoded_data,
                "mime-type": attachment["preferences"].get("Mime-Type", "application/octet-stream")
            })
        else:
            print(f"❌ Attachment '{original_filename}' was not found (expected as '{sanitized_filename}'). Skipping.")

    # Add attachments to the article payload
    if attachments_payload:
        article_payload["attachments"] = attachments_payload

    # Send API request
    response = requests.post(
        f"{PROD_API_URL}/ticket_articles",
        headers=HEADERS_PROD,
        json={**article_payload, "ticket_id": ticket_id}
    )

    if response.status_code in [200, 201]:
        new_article_id = response.json().get("id")
        print(f"✅ Created article {article['id']} → {new_article_id} with {len(attachments_payload)} attachments")

        # Store article metadata in mapping
        id_mapping.setdefault(old_ticket_id, {})["articles"] = id_mapping.get(old_ticket_id, {}).get("articles", {})
        id_mapping[old_ticket_id]["articles"][article["id"]] = {
            "new_article_id": new_article_id,
            "created_at": article.get("created_at"),
            "updated_at": article.get("updated_at"),
            "created_by_id": article.get("created_by_id"),
            "updated_by_id": article.get("updated_by_id"),
            "created_by": article.get("created_by"),
            "updated_by": article.get("updated_by"),
            "from": article.get("from"),
        }

        return new_article_id
    else:
        print(f"❌ Failed to create article {article['id']} - {response.text}")
        return None

# Create tickets in production
def create_ticket(ticket):
    old_ticket_id = ticket["id"]  # Store the old ticket ID
    old_created_at = ticket["created_at"]
    old_updated_at = ticket["updated_at"]
    old_created_by_id = ticket["created_by_id"]
    old_updated_by_id = ticket["updated_by_id"]
    old_last_contact_at = ticket["last_contact_at"]
    old_last_contact_customer_at = ticket["last_contact_customer_at"]
    old_last_owner_update_at = ticket["last_owner_update_at"]

    # Fix invalid state_id (Change "merged" state (5) to "closed" (4) bc merged is not allowed for new created tickets)
    if ticket.get("state_id") == 5:
        print(f"⚠️ Changing state 'merged' (5) to 'closed' (4) for ticket {old_ticket_id}.")
        ticket["state_id"] = 4  # Closed state

    ticket_payload = {k: v for k, v in ticket.items() if k not in [
        "id", "number", "created_at", "updated_at", "created_by_id",
        "updated_by_id", "last_contact_at", "last_contact_customer_at",
        "last_owner_update_at", "articles"
    ]}
    
    response = requests.post(PROD_API_URL + "/tickets", headers=HEADERS_PROD, json=ticket_payload)

    if response.status_code in [200, 201]:
        new_ticket_id = response.json().get("id")
        print(f"✅ Created ticket {old_ticket_id} → {new_ticket_id}")

        # Store mapping for later timestamp and metadata update
        id_mapping[old_ticket_id] = {
            "new_id": new_ticket_id,
            "created_at": old_created_at,
            "updated_at": old_updated_at,
            "created_by_id": old_created_by_id,  
            "updated_by_id": old_updated_by_id,  
            "last_contact_at": old_last_contact_at,  
            "last_contact_customer_at": old_last_contact_customer_at,  
            "last_owner_update_at": old_last_owner_update_at,  
            "articles": {}
        }

        # Create articles for the ticket
        for article in ticket.get("articles", []):
            create_article(new_ticket_id, article, old_ticket_id)

        return new_ticket_id
    else:
        print(f"❌ Failed to import ticket {old_ticket_id}: {response.text}")
        return None

# Process all tickets
for ticket in tickets:
    create_ticket(ticket)

# Save ID mapping to file
with open(ID_MAPPING_FILE, "w", encoding="utf-8") as file:
    json.dump(id_mapping, file, indent=4)

print(f"--- Import process completed. Old to new ticket ID mapping saved in {ID_MAPPING_FILE}. ---")