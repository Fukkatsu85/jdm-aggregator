import json
import re
import time
import urllib.request

from urllib.parse import urljoin
from bs4 import BeautifulSoup


BASE_URL = "https://garage-r.co.jp"
INVENTORY_URL = BASE_URL + "/cars"


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


def get_inventory():

    vehicles = []
    seen = set()

    for page in range(1, 100):

        if page == 1:
            url = INVENTORY_URL
        else:
            url = (
                INVENTORY_URL
                + f"?page={page}"
            )

        print(
            f"Downloading GARAGE-R "
            f"page {page}..."
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

            match = re.fullmatch(
                r"/cars/(\d+)",
                href
            )

            if not match:
                continue

            vehicle_no = match.group(1)

            if vehicle_no in seen:
                continue

            seen.add(vehicle_no)

            vehicles.append({
                "source": "GARAGE-R",
                "source_id": vehicle_no,
                "source_url": urljoin(
                    BASE_URL,
                    href
                )
            })

            page_new_count += 1

        print(
            f"New vehicles on page "
            f"{page}: {page_new_count}"
        )

        if page_new_count == 0:
            break

        time.sleep(1)

    return vehicles


def main():

    print()
    print(
        "Downloading complete "
        "GARAGE-R inventory..."
    )

    vehicles = get_inventory()

    print()
    print(
        f"FOUND GARAGE-R VEHICLES: "
        f"{len(vehicles)}"
    )

    with open(
        "data/garage-r-ids.json",
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            vehicles,
            file,
            ensure_ascii=False,
            indent=2
        )

    print(
        "WROTE GARAGE-R IDS TO "
        "data/garage-r-ids.json"
    )


if __name__ == "__main__":
    main()
