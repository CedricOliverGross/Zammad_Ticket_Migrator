import json

# Configuration
INPUT_JSON_FILE = "id_mapping.json"
OUTPUT_SQL_FILE = "update_metadata.sql"

# Load JSON data
with open(INPUT_JSON_FILE, "r", encoding="utf-8") as file:
    data = json.load(file)

# SQL Query List
queries = []

# Process each ticket
for old_ticket_id, ticket_data in data.items():
    new_ticket_id = ticket_data["new_id"]

    # Generate UPDATE query for ticket metadata
    ticket_update_query = f"""
    UPDATE tickets 
    SET 
        created_at = '{ticket_data["created_at"]}',
        updated_at = '{ticket_data["updated_at"]}',
        created_by_id = {ticket_data["created_by_id"]},
        updated_by_id = {ticket_data["updated_by_id"]},
        last_contact_at = {'NULL' if ticket_data["last_contact_at"] is None else f"'{ticket_data['last_contact_at']}'"},
        last_contact_customer_at = {'NULL' if ticket_data["last_contact_customer_at"] is None else f"'{ticket_data['last_contact_customer_at']}'"},
        last_owner_update_at = {'NULL' if ticket_data["last_owner_update_at"] is None else f"'{ticket_data['last_owner_update_at']}'"}
    WHERE id = {new_ticket_id};
    """
    queries.append(ticket_update_query)

    # Process articles
    for old_article_id, article_data in ticket_data.get("articles", {}).items():
        new_article_id = article_data["new_article_id"]

        # Generate UPDATE query for article metadata
        article_update_query = f"""
        UPDATE ticket_articles 
        SET 
            created_at = '{article_data["created_at"]}',
            updated_at = '{article_data["updated_at"]}',
            created_by_id = {article_data["created_by_id"]},
            updated_by_id = {article_data["updated_by_id"]}
        WHERE id = {new_article_id};
        """
        queries.append(article_update_query)

# Save queries to file
with open(OUTPUT_SQL_FILE, "w", encoding="utf-8") as file:
    file.write("\n".join(queries))

print(f"--- SQL update queries generated and saved to {OUTPUT_SQL_FILE} ---")