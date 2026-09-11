import json
import re
import socket
import time
import urllib.error
import urllib.request

from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin

from bs4 import BeautifulSoup


BASE_URL = "https://sp.beforward.jp"
DATA_FILE = "data/cars.json"

S15_SEARCH_URLS = [
    BASE_URL
    + "/stocklist/make=3/model=452/model_code=S15",
]

S13_SEARCH_URLS = [
    BASE_URL
    + "/stocklist/make=3/model=452/model_code=S13",

    BASE_URL
    + "/stocklist/make=3/model=452/model_code=E-S13",

    BASE_URL
    + "/stocklist/make=3/model=452/model_code=PS13",

    BASE_URL
    + "/stocklist/make=3/model=452/model_code=E-PS13",

    BASE_URL
    + "/stocklist/make=3/model=452/model_code=KPS13",

    BASE_URL
    + "/stocklist/make=3/model=452/model_code=E-KPS13",

    BASE_URL
    + "/stocklist/make=3/model=452/model_code=KS13",

    BASE_URL
    + "/stocklist/make=3/model=452/model_code=E-KS13",
]

S14_SEARCH_URLS = [
    BASE_URL
    + "/stocklist/make=3/model=452/model_code=S14",

    BASE_URL
    + "/stocklist/make=3/model=452/model_code=CS14",
]


def download_html(
    url,
    attempts=3,
    timeout=45,
):
    last_error = None

    for attempt in range(
        1,
        attempts + 1,
    ):
        request = (
            urllib.request.Request(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 "
                        "(Windows NT 10.0; "
                        "Win64; x64) "
                        "AppleWebKit/537.36 "
                        "Chrome/152 Safari/537.36"
                    )
                },
            )
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=timeout,
            ) as response:

                return (
                    response
                    .read()
                    .decode(
                        "utf-8",
                        errors="replace",
                    )
                )

        except urllib.error.HTTPError as error:
            if error.code == 404:
                raise

            last_error = error

        except (
            urllib.error.URLError,
            TimeoutError,
            socket.timeout,
        ) as error:

            last_error = error

        except Exception as error:
            last_error = error

        if attempt < attempts:
            print(
                f"  Attempt "
                f"{attempt}/"
                f"{attempts} failed: "
                f"{last_error}"
            )

            print(
                "  Retrying..."
            )

            time.sleep(3)

    raise last_error


def clean(text):
    if text is None:
        return None

    text = re.sub(
        r"\s+",
        " ",
        str(text),
    ).strip()

    return text or None


def parse_number(value):
    if not value:
        return None

    value = value.replace(
        ",",
        "",
    )

    match = re.search(
        r"\d+",
        value,
    )

    if not match:
        return None

    return int(
        match.group()
    )


def load_previous_beforward():
    try:
        with open(
            DATA_FILE,
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(
                file
            )

    except (
        FileNotFoundError,
        json.JSONDecodeError,
    ):
        return []

    if not isinstance(
        data,
        list,
    ):
        return []

    return [
        car
        for car in data
        if (
            car.get("source")
            == "BE FORWARD"
        )
    ]


def previous_by_chassis(
    previous_cars,
    chassis,
):
    return [
        car
        for car in previous_cars
        if (
            str(
                car.get(
                    "chassis",
                    "",
                )
            ).upper()
            ==
            chassis.upper()
        )
    ]


def previous_by_ref(
    previous_cars,
):
    result = {}

    for car in previous_cars:
        ref_no = car.get(
            "ref_no"
        )

        if ref_no:
            result[
                str(ref_no)
            ] = car

    return result


def find_listing_container(
    link,
):
    node = link

    for _ in range(10):
        if not node:
            return None

        text = (
            clean(
                node.get_text(
                    " ",
                    strip=True,
                )
            )
            or ""
        )

        if (
            "Ref No." in text
            and
            "Year:" in text
            and
            "Mileage:" in text
        ):
            return node

        node = node.parent

    return None


def extract_listing(
    link,
    chassis,
):
    container = (
        find_listing_container(
            link
        )
    )

    if not container:
        return None

    text = (
        clean(
            container.get_text(
                " ",
                strip=True,
            )
        )
        or ""
    )

    ref_match = re.search(
        r"Ref No\.\s*"
        r"([A-Z0-9]+)",
        text,
        flags=re.I,
    )

    if not ref_match:
        return None

    ref_no = (
        ref_match.group(1)
    )

    price_match = re.search(
        r"Price\s*\$\s*"
        r"([0-9,]+)",
        text,
        flags=re.I,
    )

    year_match = re.search(
        r"Year:\s*"
        r"(\d{4})"
        r"(?:\s*/\s*"
        r"(\d{1,2}))?",
        text,
        flags=re.I,
    )

    mileage_match = re.search(
        r"Mileage:\s*"
        r"([0-9,]+)"
        r"\s*km",
        text,
        flags=re.I,
    )

    image_url = None

    image = container.find(
        "img"
    )

    if image:
        image_url = (
            image.get(
                "data-src"
            )
            or image.get(
                "data-lazy-src"
            )
            or image.get(
                "src"
            )
        )

        if image_url:
            image_url = urljoin(
                BASE_URL,
                image_url,
            )

    return {
        "source":
            "BE FORWARD",

        "ref_no":
            ref_no,

        "make":
            "Nissan",

        "model":
            "Silvia",

        "chassis":
            chassis,

        "year":
            (
                int(
                    year_match.group(1)
                )
                if year_match
                else None
            ),

        "month":
            (
                int(
                    year_match.group(2)
                )
                if (
                    year_match
                    and
                    year_match.group(2)
                )
                else None
            ),

        "price_usd":
            (
                parse_number(
                    price_match.group(1)
                )
                if price_match
                else None
            ),

        "mileage_km":
            (
                parse_number(
                    mileage_match.group(1)
                )
                if mileage_match
                else None
            ),

        "source_url":
            urljoin(
                BASE_URL,
                link.get(
                    "href"
                ),
            ),

        "thumbnail_url":
            image_url,
    }


def scrape_chassis(
    chassis,
    search_urls,
    previous_cars,
):
    listings = []
    seen = set()

    transient_failure = False

    for search_url in (
        search_urls
    ):
        print()

        print(
            f"Checking "
            f"{chassis} source:",
            search_url,
        )

        source_had_page = False

        for page in range(
            1,
            10,
        ):
            if page == 1:
                url = search_url

            else:
                url = (
                    search_url
                    + f"/page={page}"
                )

            print(
                f"Downloading "
                f"{chassis} "
                f"page {page}..."
            )

            try:
                html = (
                    download_html(
                        url
                    )
                )

            except urllib.error.HTTPError as error:
                if error.code == 404:
                    print(
                        f"Stopping this "
                        f"{chassis} source "
                        f"at page {page}: "
                        f"HTTP 404"
                    )

                    break

                print(
                    f"Transient "
                    f"{chassis} "
                    f"source failure "
                    f"at page {page}: "
                    f"{error}"
                )

                transient_failure = True
                break

            except Exception as error:
                print(
                    f"Transient "
                    f"{chassis} "
                    f"source failure "
                    f"at page {page}: "
                    f"{error}"
                )

                transient_failure = True
                break

            source_had_page = True

            soup = BeautifulSoup(
                html,
                "html.parser",
            )

            page_new_count = 0

            for link in soup.find_all(
                "a",
                href=True,
            ):
                href = link.get(
                    "href",
                    "",
                )

                if (
                    "/nissan/silvia/"
                    not in href.lower()
                    or
                    "/id/"
                    not in href.lower()
                ):
                    continue

                listing = (
                    extract_listing(
                        link,
                        chassis,
                    )
                )

                if not listing:
                    continue

                ref_no = listing[
                    "ref_no"
                ]

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
                f"New {chassis} "
                f"listings on "
                f"page {page}: "
                f"{page_new_count}"
            )

            if page_new_count == 0:
                break

            time.sleep(1)

        if not source_had_page:
            continue

    previous = (
        previous_by_chassis(
            previous_cars,
            chassis,
        )
    )

    if transient_failure:
        if previous:
            print()

            print(
                f"{chassis} had a "
                f"transient source "
                f"failure."
            )

            print(
                f"Preserving "
                f"{len(previous)} "
                f"previous "
                f"{chassis} listings "
                f"and merging "
                f"fresh results."
            )

            for old_car in previous:
                ref_no = str(
                    old_car.get(
                        "ref_no",
                        "",
                    )
                )

                if (
                    ref_no
                    and
                    ref_no not in seen
                ):
                    seen.add(
                        ref_no
                    )

                    listings.append(
                        old_car
                    )

        else:
            raise RuntimeError(
                f"{chassis} source "
                f"failed and there is "
                f"no previous "
                f"{chassis} inventory "
                f"to preserve. "
                f"Stopping before "
                f"live inventory can "
                f"be wiped."
            )

    return listings


def get_detail_photos(
    url,
):
    html = download_html(
        url,
        attempts=2,
        timeout=45,
    )

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    photos = []
    seen = set()

    def add_photo(
        image_url,
    ):
        if not image_url:
            return

        image_url = urljoin(
            BASE_URL,
            image_url,
        )

        image_url = (
            image_url.replace(
                "/medium/",
                "/large/",
            )
        )

        image_url = (
            image_url
            .split("?")[0]
            .split("#")[0]
        )

        if (
            "image-cdn.beforward.jp/"
            "large/"
            not in image_url
        ):
            return

        key = (
            image_url.lower()
        )

        if key in seen:
            return

        seen.add(
            key
        )

        photos.append(
            image_url
        )

    for link in soup.find_all(
        "a",
        href=True,
    ):
        add_photo(
            link.get(
                "href"
            )
        )

    for image in soup.find_all(
        "img"
    ):
        for attribute in (
            "src",
            "data-src",
            "data-lazy-src",
        ):
            add_photo(
                image.get(
                    attribute
                )
            )

    return photos


def fetch_gallery(
    listing,
    previous_map,
):
    ref_no = str(
        listing.get(
            "ref_no",
            "",
        )
    )

    try:
        photos = (
            get_detail_photos(
                listing[
                    "source_url"
                ]
            )
        )

        if (
            not photos
            and
            listing.get(
                "thumbnail_url"
            )
        ):
            photos = [
                listing[
                    "thumbnail_url"
                ]
                .replace(
                    "/medium/",
                    "/large/",
                )
                .split("?")[0]
            ]

        return (
            listing,
            photos,
            None,
        )

    except Exception as error:
        previous = (
            previous_map.get(
                ref_no
            )
        )

        if (
            previous
            and
            previous.get(
                "photo_urls"
            )
        ):
            return (
                listing,
                previous[
                    "photo_urls"
                ],
                error,
            )

        thumbnail = (
            listing.get(
                "thumbnail_url"
            )
        )

        if thumbnail:
            return (
                listing,
                [
                    thumbnail
                    .replace(
                        "/medium/",
                        "/large/",
                    )
                    .split("?")[0]
                ],
                error,
            )

        return (
            listing,
            [],
            error,
        )


def main():
    previous_cars = (
        load_previous_beforward()
    )

    previous_map = (
        previous_by_ref(
            previous_cars
        )
    )

    print()

    print(
        "PREVIOUS BE FORWARD CARS: "
        f"{len(previous_cars)}"
    )

    print()

    print(
        "Downloading BE FORWARD "
        "S15 inventory..."
    )

    s15_listings = (
        scrape_chassis(
            "S15",
            S15_SEARCH_URLS,
            previous_cars,
        )
    )

    print()

    print(
        "FOUND S15 LISTINGS: "
        f"{len(s15_listings)}"
    )

    print()

    print(
        "Downloading BE FORWARD "
        "S13 inventory..."
    )

    s13_listings = (
        scrape_chassis(
            "S13",
            S13_SEARCH_URLS,
            previous_cars,
        )
    )

    print()

    print(
        "FOUND S13 LISTINGS: "
        f"{len(s13_listings)}"
    )

    print()

    print(
        "Downloading BE FORWARD "
        "S14 inventory..."
    )

    s14_listings = (
        scrape_chassis(
            "S14",
            S14_SEARCH_URLS,
            previous_cars,
        )
    )

    print()

    print(
        "FOUND S14 LISTINGS: "
        f"{len(s14_listings)}"
    )

    listings = []
    seen = set()

    for listing in (
        s15_listings
        + s14_listings
        + s13_listings
    ):
        ref_no = str(
            listing.get(
                "ref_no",
                "",
            )
        )

        if (
            not ref_no
            or
            ref_no in seen
        ):
            continue

        seen.add(
            ref_no
        )

        listings.append(
            listing
        )

    print()

    print(
        "TOTAL UNIQUE "
        "BE FORWARD CARS: "
        f"{len(listings)}"
    )

    cars = []

    with ThreadPoolExecutor(
        max_workers=5
    ) as executor:

        results = executor.map(
            lambda listing:
                fetch_gallery(
                    listing,
                    previous_map,
                ),
            listings,
        )

        for index, result in enumerate(
            results,
            start=1,
        ):
            (
                listing,
                photos,
                error,
            ) = result

            print(
                f"Gallery "
                f"{index}/"
                f"{len(listings)}: "
                f"{listing['ref_no']} "
                f"({listing['chassis']})"
            )

            if error:
                print(
                    "  Gallery fetch "
                    "failed; using "
                    "preserved/fallback "
                    "photos:",
                    error,
                )

            print(
                "  Photos found: "
                f"{len(photos)}"
            )

            car = {
                "id":
                    "beforward-"
                    + listing[
                        "ref_no"
                    ],

                "source":
                    "BE FORWARD",

                "ref_no":
                    listing[
                        "ref_no"
                    ],

                "make":
                    listing[
                        "make"
                    ],

                "model":
                    listing[
                        "model"
                    ],

                "chassis":
                    listing[
                        "chassis"
                    ],

                "year":
                    listing[
                        "year"
                    ],

                "month":
                    listing[
                        "month"
                    ],

                "price_usd":
                    listing[
                        "price_usd"
                    ],

                "mileage_km":
                    listing[
                        "mileage_km"
                    ],

                "source_url":
                    listing[
                        "source_url"
                    ],

                "photo_urls":
                    photos,
            }

            cars.append(
                car
            )

    with open(
        DATA_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            cars,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print()

    print(
        f"WROTE "
        f"{len(cars)} "
        f"BE FORWARD CARS TO "
        f"{DATA_FILE}"
    )


if __name__ == "__main__":
    main()
