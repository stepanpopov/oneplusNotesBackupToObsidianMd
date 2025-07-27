import os
import json
import re
import time
from datetime import datetime

from bs4 import BeautifulSoup
from markdownify import markdownify as md

HIDDEN_FOLDER_GUID = "55a54008-ad1b-3589-aa21-0d2629c1df41"

def html_to_markdown(html):
    soup = BeautifulSoup(html, 'html.parser')
    # Convert checkboxes
    for checkbox in soup.find_all('input', {'type': 'checkbox'}):
        checked = checkbox.has_attr('checked')
        markdown_box = '- [x] ' if checked else '- [ ] '
        checkbox.replace_with(markdown_box)
    # Update img src attributes
    for img in soup.find_all('img'):
        src = img.get('src')
        if src:
            # Only append if not already ending with _thumb.png
            if not src.endswith('_thumb.png'):
                img['src'] = src + '_thumb.png'
    return md(str(soup))


def safe_filename(name):
    # Remove or replace unsafe characters for filenames
    return re.sub(r'[\\/:*?"<>|]', ' ', name).strip()

def timestamp_to_epoch(ts):
    # Handles both ms timestamps and string dates
    if isinstance(ts, int):
        # Assume ms since epoch
        return ts // 1000
    if isinstance(ts, str):
        # Try to parse string date
        try:
            dt = datetime.strptime(ts, '%b %d, %Y %H:%M:%S')
            return int(dt.timestamp())
        except Exception:
            return int(time.time())
    return int(time.time())

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base_dir, 'folder.json'), encoding='utf-8') as f:
        folders = json.load(f)
    folder_map = {folder['guid']: folder['name'] for folder in folders}

    # Hidden folder.
    folder_map[HIDDEN_FOLDER_GUID] = 'Hidden Notes'

    with open(os.path.join(base_dir, 'rich_note.json'), encoding='utf-8') as f:
        notes = json.load(f)


    created_files = 0
    for entry in notes:
        rich_note = entry.get('richNote')
        if not rich_note:
            continue
        folder_guid = rich_note.get('folderGuid', '00000000_0000_0000_0000_000000000000')
        folder_name = folder_map.get(folder_guid, 'Unsorted')
        base_folder_path = os.path.join(base_dir, 'exported_notes_md', safe_filename(folder_name))

        # Check for pin (topTime > 0)
        top_time = rich_note.get('topTime', 0)
        if isinstance(top_time, str):
            try:
                top_time = int(top_time)
            except Exception:
                top_time = 0
        if top_time > 0:
            folder_path = os.path.join(base_folder_path, 'pin')
        else:
            folder_path = base_folder_path
        os.makedirs(folder_path, exist_ok=True)

        text = rich_note.get('text', '')
        title = rich_note.get('title', '').strip()
        if not title:
            # Use first 20 symbols of content as filename
            preview = text[:20].replace('\n', ' ').strip() or 'Untitled'
            filename = safe_filename(preview)
        else:
            filename = safe_filename(title)

        file_path = os.path.join(folder_path, filename + '.md')
        # Handle file name collisions
        original_file_path = file_path
        count = 1
        while os.path.exists(file_path):
            file_path = os.path.join(folder_path, f"{filename}_{count}.md")
            count += 1

        html_text = rich_note.get('htmlText', '')

        assert not os.path.exists(file_path), f"File {file_path} already exists."
        with open(file_path, 'w', encoding='utf-8') as out:
            out.write(html_to_markdown(html_text))
        created_files += 1

        # Set file times
        create_time = timestamp_to_epoch(rich_note.get('createTime', int(time.time()*1000)))
        update_time = timestamp_to_epoch(rich_note.get('updateTime', int(time.time()*1000)))
        try:
            os.utime(file_path, (create_time, update_time))
        except Exception as e:
            print(f"Error setting times for {file_path}: {e}")

    print(f"Created {created_files} files for {len(notes)} notes.")

if __name__ == '__main__':
    main()
