"""
CyberDeck Bookmarks

Simple JSON-backed bookmark list.
"""


import json
import os

from paths import DATA_DIR


BOOKMARKS_FILE = os.path.join(
    DATA_DIR,
    "cyberdeck_bookmarks.json"
)




def load_bookmarks():

    if not os.path.exists(BOOKMARKS_FILE):

        return []


    try:

        with open(BOOKMARKS_FILE, "r") as f:

            return json.load(f)

    except Exception:

        return []




def save_bookmarks(bookmarks):

    with open(BOOKMARKS_FILE, "w") as f:

        json.dump(

            bookmarks,

            f,

            indent=4

        )




def add_bookmark(
    title,
    url
):

    bookmarks = load_bookmarks()


    for entry in bookmarks:

        if entry.get("url") == url:

            return bookmarks


    bookmarks.append(
        {
            "title": title or url,
            "url": url
        }
    )

    save_bookmarks(
        bookmarks
    )

    return bookmarks
