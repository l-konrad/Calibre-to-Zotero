import os
import sqlite3
import json
from argparse import ArgumentParser
import argparse
import sys

from pyzotero import zotero

def validate_file_path(path_str):
    if not os.path.exists(path_str):
        raise argparse.ArgumentTypeError(f"The file '{path_str}' does not exist.")
    if not os.path.isfile(path_str):
        raise argparse.ArgumentTypeError(f"The path '{path_str}' is not a file.")
    return path_str

def main(zot, calibre_db, books):
    # Connect to the Calibre Database
    try:
        conn = sqlite3.connect(calibre_db)
        cursor = conn.cursor()
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
        return

    for book_path in books:
        print(f"\n--- Processing: {os.path.basename(book_path)} ---")
        
        file_name = os.path.splitext(os.path.basename(book_path))[0] 
        file_fmt = os.path.splitext(book_path)[1][1:].upper()
        if file_fmt != 'EPUB':
            print(f"Skipping: '{path_obj.name}' is not an EPUB.")
            continue

        # 2. Get Book Metadata First
        meta_query = """
        SELECT 
            B.id,
            B.title
        FROM books B
        JOIN data D ON B.id = D.book
        WHERE D.name = ? AND D.format = ?
        LIMIT 1;
        """
       
        try:
            cursor.execute(meta_query, (file_name, file_fmt))
            row = cursor.fetchone()

            if row:
                book_id = row[0]
                title = row[1]
                url = f"calibre://view-book/_/{book_id}/{file_fmt}"

                # 3. Get Annotations separately for this book
                # We fetch raw text and the CFI data needed to build the link
                annot_query = """
                SELECT 
                    searchable_text, 
                    json_extract(annot_data, '$.start_cfi')
                FROM annotations 
                WHERE book = ? AND annot_data IS NOT NULL
                """
                
                cursor.execute(annot_query, (book_id,))
                annot_rows = cursor.fetchall()
                
                annotations = [] 
                
                for a_row in annot_rows:
                    raw_text = a_row[0]
                    raw_cfi = a_row[1]
                    
                    clean_text = raw_text.replace('\r', ' ').replace('\n', ' ').strip()
                    
                    if raw_cfi:
                        encoded_cfi = raw_cfi.replace('[', '%5B').replace(']', '%5D').replace(':', '%3A')
                        # Note: The /8 prefix is standard for Calibre EPUB paths in CFIs
                        link = f"calibre://view-book/_/{book_id}/EPUB?open_at=epubcfi(/8{encoded_cfi})"
                    else:
                        link = url # Fallback to main book url if CFI missing

                    # Append dictionary to list
                    annotations.append({
                        "text": clean_text,
                        "link": link
                    })

                # --- DEBUG PRINT ---
                print(f"Title:   {title}")
                print(f"Found {len(annotations)} annotations.")
                
                # Example: Print the first 2 to show structure
                for i, item in enumerate(annotations[:2]):
                    print(f"\n-- Item {i+1} --")
                    print(f"Text: {item['text'][:100]}...") # Truncated for display
                    print(f"Link: {item['link']}")
                
                # TODO: Pass 'title', 'authors', 'url', and the 'annotations' list to Zotero logic
                template = zot.item_template('book')
                template['title'] = title
                book_result = zot.create_items([template])

                if book_result['successful']:
                    book_item = book_result['successful']['0']
                    book_key = book_item['key']
                    print(f"Book created: {book_key}")

                    # 2. Create the Attachment Item (The Child)
                    # We must explicitly create an item meant to hold a file
                    attachment_template = {
                        'itemType': 'attachment',
                        'parentItem': book_key,  # LINK IT TO THE BOOK HERE
                        'linkMode': 'imported_file',
                        'title': 'My_Book_File.epub',
                        'contentType': 'application/epub+zip'
                    }
                    
                    # Create the attachment placeholder in Zotero
                    att_result = zot.create_items([attachment_template])
                    
                    if att_result['successful']:
                        attachment_item = att_result['successful']['0']
                        
                        # 3. Upload the file to the ATTACHMENT item (Not the book item)
                        print("Uploading file...")
                        zot.attachment_simple(attachment_item, )
                        print("Upload complete.")
                    else:
                        print("Failed to create attachment item.")
                else:
                    print("Failed to create book item.")
                                   
                                
            else:
                print(f"Could not find metadata in Calibre DB for file: {file_name}")

        except sqlite3.Error as e:
            print(f"SQL Error processing {file_name}: {e}")

    conn.close()


if __name__ == "__main__":
    parser = ArgumentParser(description="Zotero Connector Script")
    
    parser.add_argument("-k", "--api-key", dest="api_key", required=True)
    parser.add_argument("-i", "--library-id", dest="library_id", required=True)
    parser.add_argument("-d", "--calibre_db_path", dest="calibre_db", required=True, type=validate_file_path)
    parser.add_argument("-b", "--book_paths", dest="books", nargs='*', type=validate_file_path, default=[])

    args = parser.parse_args()
    
    # Init Zotero (Placeholder)
    zot = zotero.Zotero(args.library_id, 'user', args.api_key)
    try:
        zot.top(limit=1)
        print("Connection to zotero successful.")
    except:
        print("Could not connect to Zotero.")
        sys.exit()
    else:
        pass

    main(zot, args.calibre_db, args.books)
