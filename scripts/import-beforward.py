import json
import re
import urllib.request
import time

from urllib.parse import urljoin
from bs4 import BeautifulSoup


BASE_URL = "https://sp.beforward.jp"

SEARCH_URL = (
    BASE_URL
    + "/stocklist/make=3/model=452/model_code=S15"
)


def download_html(url):

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent":
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "Chrome/152 Safari/537.36"
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=30
    ) as response:

        return response.read().decode(
            "utf-8",
            errors="replace"
        )


def clean(text):

    if text is None:
        return None

    text = re.sub(
        r"\s+",
        " ",
        str(text)
    ).strip()

    return text or None


def parse_number(value):

    if not value:
        return None

    value = value.replace(",", "")

    match = re.search(
        r"\d+",
        value
    )

    if not match:
        return None

    return int(
        match.group()
    )


def find_listing_container(link):

    node = link

    # Walk upward until we find the HTML block
    # containing this vehicle's complete summary.

    for _ in range(10):

        if not node:
            return None

        text = clean(
            node.get_text(
                " ",
                strip=True
            )
        ) or ""

        if (
            "Ref No." in text
            and "Year:" in text
            and "Mileage:" in text
        ):
            return node

        node = node.parent

    return None


def extract_listing(link):

    container = find_listing_container(
        link
    )

    if not container:
        return None

    text = clean(
        container.get_text(
            " ",
            strip=True
        )
    ) or ""


    ref_match = re.search(
        r"Ref No\.\s*([A-Z0-9]+)",
        text,
        flags=re.I
    )

    if not ref_match:
        return None

    ref_no = ref_match.group(1)


    chassis_match = re.search(
        r"\(([^()]*(?:S15|GF-S15)[^()]*)\)",
        text,
        flags=re.I
    )


    price_match = re.search(
        r"Price\s*\$\s*([0-9,]+)",
        text,
        flags=re.I
    )


    year_match = re.search(
        r"Year:\s*(\d{4})"
        r"(?:\s*/\s*(\d{1,2}))?",
        text,
        flags=re.I
    )


    mileage_match = re.search(
        r"Mileage:\s*([0-9,]+)\s*km",
        text,
        flags=re.I
    )


    image_url = None

    image = container.find("img")

    if image:

        image_url = (
            image.get("data-src")
            or image.get("data-lazy-src")
            or image.get("src")
        )

        if image_url:
            image_url = urljoin(
                BASE_URL,
                image_url
            )


    listing = {
        "source": "BE FORWARD",

        "ref_no": ref_no,

        "make": "Nissan",

        "model": "Silvia",

        "chassis": (
            clean(
                chassis_match.group(1)
            )
            if chassis_match
            else "S15"
        ),

        "year": (
            int(year_match.group(1))
            if year_match
            else None
        ),

        "month": (
            int(year_match.group(2))
            if (
                year_match
                and year_match.group(2)
            )
            else None
        ),

        "price_usd": (
            parse_number(
                price_match.group(1)
            )
            if price_match
            else None
        ),

        "mileage_km": (
            parse_number(
                mileage_match.group(1)
            )
            if mileage_match
            else None
        ),

        "source_url": urljoin(
            BASE_URL,
            link.get("href")
        ),

        "thumbnail_url": image_url,
    }

    return listing

def get_detail_photos(url):

    html = download_html(url)

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    photos = []
    seen = set()


    def add_photo(image_url):

        if not image_url:
            return

        image_url = urljoin(
            BASE_URL,
            image_url
        )

        # Always use the high-resolution version.
        image_url = image_url.replace(
            "/medium/",
            "/large/"
        )

        # Remove resize/query parameters so the same
        # image cannot appear twice at different sizes.
        image_url = (
            image_url
            .split("?")[0]
            .split("#")[0]
        )

        if (
            "image-cdn.beforward.jp/large/"
            not in image_url
        ):
            return

        # Case-insensitive key catches duplicate JPG/jpg URLs.
        key = image_url.lower()

        if key in seen:
            return

        seen.add(key)
        photos.append(image_url)


    # Gallery links
    for link in soup.find_all(
        "a",
        href=True
    ):

        add_photo(
            link.get("href")
        )


    # Gallery image elements
    for image in soup.find_all("img"):

        for attribute in [
            "src",
            "data-src",
            "data-lazy-src"
        ]:

            add_photo(
                image.get(attribute)
            )


    return photos
    
def get_s15_listings():

    listings = []
    seen = set()

    for page in range(1, 10):

        if page == 1:
            url = SEARCH_URL
        else:
            url = SEARCH_URL + f"/page={page}"

        print(
            f"Downloading page {page}..."
        )

        try:
            html = download_html(url)
        except Exception as error:
            print(
                f"Stopping at page {page}:",
                error
            )
            break

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        page_new_count = 0

        for link in soup.find_all(
            "a",
            href=True
        ):

            href = link.get(
                "href",
                ""
            )

            if (
                "/nissan/silvia/" not in href.lower()
                or "/id/" not in href.lower()
            ):
                continue

            listing = extract_listing(
                link
            )

            if not listing:
                continue

            ref_no = listing["ref_no"]

            if ref_no in seen:
                continue

            seen.add(
                ref_no
            )

            listings.append(
                listing
            )

            page_new_count += 1


        print(
            f"New listings on page {page}: "
            f"{page_new_count}"
        )


        if page_new_count == 0:
            break


        time.sleep(1)


    return listings


def main():

    print()
    print(
        "Downloading BE FORWARD "
        "S15 inventory..."
    )

    listings = get_s15_listings()

    print()
    print(
        f"FOUND S15 LISTINGS: "
        f"{len(listings)}"
    )

    cars = []

    for index, listing in enumerate(listings, start=1):

        print(
            f"Fetching gallery {index}/{len(listings)}: "
            f"{listing['ref_no']}"
        )

        try:
            photos = get_detail_photos(
                listing["source_url"]
            )

        except Exception as error:

            print(
                "Gallery error:",
                error
            )

            photos = []

        if (
            not photos
            and listing["thumbnail_url"]
        ):

            photos = [
                listing["thumbnail_url"]
                    .replace(
                        "/medium/",
                        "/large/"
                    )
                    .split("?")[0]
            ]

        car = {
            "id": f"beforward-{listing['ref_no']}",
            "source": "BE FORWARD",
            "ref_no": listing["ref_no"],
            "make": listing["make"],
            "model": listing["model"],
            "chassis": listing["chassis"],
            "year": listing["year"],
            "month": listing["month"],
            "price_usd": listing["price_usd"],
            "mileage_km": listing["mileage_km"],
            "source_url": listing["source_url"],
            "photo_urls": photos
        }

        cars.append(car)

        print(
            f"  Photos found: {len(photos)}"
        )

        time.sleep(0.5)

    with open(
        "data/cars.json",
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            cars,
            file,
            ensure_ascii=False,
            indent=2
        )

    print()
    print(
        f"WROTE {len(cars)} CARS "
        "TO data/cars.json"
    )
if __name__ == "__main__":
    main()
