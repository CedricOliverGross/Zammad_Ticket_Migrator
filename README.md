# Ticket Migration

These are Scripts to Migrate a specified Range of Tickets to a new Zammad System. It handles tickets, articles and attachments.

While creating new Tickets via API in Zammad, some System generated fields can not be set / get overwritten. To handle with this problem, the third script generates a sql script that must be executed locally on the server.


## Prerequisites
* SSH Access to Source and Target System
* Zammad Admin User with all rights on source and target system
* API Token (Bearer) for the two Admin Users, best with all rights
* Python3 package "requests" installed
* Ticked-ID Range for the Tickets you want to migrate
* Zammad database user credentials (in /opt/zammad/config/database.yml)


To install python3 requirements (at best in venv):
````
pip install -r requirements.txt
````



## 1. Export Tickets
What it does:
* Iterates through a defined range of ticket IDs, making API requests to retrieve ticket details.
* Fetches Articles
* Downloads Attachments
* Saves Data Locally


To export the tickets wanted, modify id range, your source url, then run: 
````
python3 01_export_tickets_complete.py
````

## 2. Import Tickets

### Python Script to Push Tickets and Track Both Timestamps:
What it does:
* Reads tickets from tickets_full_with_attachments.json.
* Processes Attachments: Sanitizes filenames, encodes attachments to Base64, and prepares them for API upload.
* Creates Tickets: Sends a POST request to Zammad API to create new tickets.
* Creates Articles: Associates articles with tickets, uploads attachments, and stores new article IDs in id_mapping.json.
* Saves & Completes Migration: Stores old-to-new ticket mappings, logs success/failure messages, and confirms migration completion.

Modify source url and bearer token, the run:

````
python3 02_import_tickets_test.py
````

## 3. Create SQL Script

Now that we have id_mapping.json, we generate an SQL script to update timestamps:

````
python3 03_update_timestamps.py
````

## 4. Update timestamps in Database

1. Copy the generated update_metadata.slq to the target system, where zammad runs

````
scp /path/to/update_metadata.sql targetsystem:/destination/path
````

2. Run the SQL script to update timestamps
Copy the generated update_metadata.slq to the target system, where zammad runs

login into database and execute:

````
\i /path/to/update_timestamps.sql
````