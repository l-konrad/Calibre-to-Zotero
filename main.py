import os
import sys
import time
import json
import sqlite3
import argparse
from pathlib import Path  
from pyzotero import zotero

# Config
MAX_RETRIES = 12
SECONDS_BETWEEN = 5

def validate_file_path(path_str):
    path = Path(path_str)
    if not path.exists():
        raise argparse.ArgumentTypeError(f"File '{path_str}' does not exist.")
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"Path '{path_str}' is not a file.")
    return path  

def main(zot, calibre_db, books):
    try:
        conn = sqlite3.connect(calibre_db)
        cursor = conn.cursor()
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        return

    for book_path in books:
        book_file = book_path
        print(f"\n--- Processing: {book_file.name} ---")
        
        file_name = book_file.stem
        file_fmt = book_file.suffix.lstrip('.').upper()

        if file_fmt != 'EPUB':
            print(f"Skipping: {book_file.name} is not an EPUB.")
            continue

        # Fetch book ID and Title from Calibre
        query_meta = """
            SELECT B.id, B.title 
            FROM books B 
            JOIN data D ON B.id = D.book 
            WHERE D.name = ? AND D.format = ? 
            LIMIT 1
        """
        
        try:
            cursor.execute(query_meta, (file_name, file_fmt))
            row = cursor.fetchone()

            if not row:
                print(f"Could not find metadata in Calibre DB for: {file_name}")
                continue

            book_id, title = row
            base_url = f"calibre://view-book/_/{book_id}/{file_fmt}"

            # Fetch Annotations
            query_annot = """
                SELECT searchable_text, json_extract(annot_data, '$.start_cfi')
                FROM annotations 
                WHERE book = ? AND annot_data IS NOT NULL
            """
            
            cursor.execute(query_annot, (book_id,))
            annot_rows = cursor.fetchall()
            
            annotations = []
            for raw_text, raw_cfi in annot_rows:
                # normalize whitespace
                clean_text = " ".join(raw_text.split())
                
                if raw_cfi:
                    chars_to_encode = {
                        '[': '%5B',
                        ']': '%5D',
                        ':': '%3A'
                    }
                    
                    encoded_cfi = raw_cfi
                    for char, code in chars_to_encode.items():
                        encoded_cfi = encoded_cfi.replace(char, code)

                    link = f"calibre://view-book/_/{book_id}/EPUB?open_at=epubcfi(/8{encoded_cfi})"
                else:
                    link = base_url

                annotations.append({
                    "text": clean_text,
                    "link": link
                })

            print(f"Title: {title}")
            print(f"Found {len(annotations)} annotations.")

            # Create Linked File Attachment in Zotero
            attachment_payload = {
                'itemType': 'attachment',
                'linkMode': 'linked_file',
                'title': 'ChangeMe.epub',
                'path': str(book_file),
                'contentType': 'application/epub+zip'
            }

            att_res = zot.create_items([attachment_payload])

            if not att_res['successful']:
                print(f"Failed to create link attachment: {att_res}")
                continue

            print("Link created successfully. Waiting for Zotero metadata retrieval...")
            
            # Poll Zotero for the parent item
            parent_key = None
            
            for attempt in range(1, MAX_RETRIES + 1):
                results = zot.items(q=f'"{title}"')
                
                # Check for an exact title match on a parent item
                for item in results:
                    data = item['data']
                    z_title = data.get('title', '').strip().lower()
                    
                    if z_title == title.strip().lower() and data['itemType'] != 'attachment':
                        parent_key = item['key']
                        print(f"Found parent item: {parent_key} ({data['itemType']})")
                        break
                
                if parent_key:
                    break

                print(f"Attempt {attempt}/{MAX_RETRIES}: Item not found. Sleeping {SECONDS_BETWEEN}s...")
                time.sleep(SECONDS_BETWEEN)

            if not parent_key:
                print("Error: Timed out waiting for the book creation in Zotero.")
                sys.exit()

            # Upload Notes
            note_payloads = []
            for item in annotations:
                note_html = (
                    f"<p><strong>Annotation:</strong><br>{item['text']}</p>"
                    f"<hr>"
                    f"<p><strong>Link:</strong><br><a href=\"{item['link']}\">{item['link']}</a></p>"
                )

                note_payloads.append({
                    'itemType': 'note',
                    'parentItem': parent_key,
                    'note': note_html
                })
            
            if note_payloads:
                note_res = zot.create_items(note_payloads)
                if note_res['successful']:
                    print(f"Uploaded {len(note_payloads)} notes.")
                else:
                    print(f"Failed to upload notes: {note_res}")

        except sqlite3.Error as e:
            print(f"SQL Error processing {file_name}: {e}")

    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calibre to Zotero Annotations Sync")
    
    parser.add_argument("-k", "--api-key", dest="api_key", required=True)
    parser.add_argument("-i", "--library-id", dest="library_id", required=True)
    parser.add_argument("-d", "--calibre-db", dest="calibre_db", required=True, type=validate_file_path)
    parser.add_argument("-b", "--books", dest="books", nargs='*', type=validate_file_path, default=[])

    args = parser.parse_args()
    
    zot = zotero.Zotero(args.library_id, 'user', args.api_key)
    
    try:
        zot.top(limit=1)
        print("Connected to Zotero.")
    except Exception:
        print("Could not connect to Zotero.")
        sys.exit(1)

    main(zot, args.calibre_db, args.books)
