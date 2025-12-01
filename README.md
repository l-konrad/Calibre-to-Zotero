# Here's how you can get your annotations from your e-book and Calibre to Zotero

1. [[#Usage]]
2. [[#Example with Kobo]]
3. [[#Options for other E-Readers]]
4. [[#Some nerd make this easier please]]

## Usage

```sh
usage: main.py [-h] -k API_KEY -i LIBRARY_ID -d CALIBRE_DB [-b [BOOKS ...]]

Calibre to Zotero Annotations Sync

options:
  -h, --help            show this help message and exit
  -k API_KEY, --api-key API_KEY
  -i LIBRARY_ID, --library-id LIBRARY_ID
  -d CALIBRE_DB, --calibre-db CALIBRE_DB
  -b [BOOKS ...], --books [BOOKS ...]
```

1. First install the Zotero Plugin
    This retrieves the metadata for the uploaded book (so you don't have to do that manually)

    1. Download the `export-metadata-helper.xpi` from Releases 
    2. Put it into Tools -> Plugins -> Install Plugin from file
2. Run the script with uv

Example:
uv run main.py \
    -k YourAPIKey \
    -i Your libaryID \
    -d ~/Calibre\ Library/metadata.db \
    -b ~/Calibre\ Library/Folder/book.epub


## Example with Kobo

With github.com/valeriangalliat/kobo-highlights-to-calibre we can export the highlights from Kobo to Calibre

I've cloned the repo and done a monkey patch so it works for me in the kobo folder

After you exported your highlights to Calibre you can follow [[##Usage]]

## Options for other E-Readers

It might be possible to sync annotations from an EPUB to calibre with KOReader

PDF's should also not have this problem as they don't use a CIF for annotations, so you could also just convert it into a PDF and then do your annotations and they should show up as annotations in Zotero
KOReader should make reading PDF's easier

Also something I still have yet to try


## Some nerd make this easier please

Hey! If anyone has some free time, figuring out how to convert the Calibre CFI to a Zotero CFI that would be amazing! 
These links might help with that:

    https://github.com/fread-ink/epub-cfi-resolver
    https://github.com/eliascotto/export-kobo

or if someone at Zotero could make annoations easier to import through the API, please!
