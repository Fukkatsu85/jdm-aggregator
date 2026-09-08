import json
import re
import time
import urllib.request

from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin

from bs4 import BeautifulSoup


BASE_URL = "https://garage-r.co.jp"
INVENTORY_URL = BASE_URL + "/cars"

MAKE_NAMES = {
    "日産": "Nissan",
    "トヨタ": "Toyota",
    "マツダ": "Mazda",
    "ホンダ": "Honda",
    "三菱": "Mitsubishi",
    "スバル": "Subaru",
    "スズキ": "Suzuki",
    "ダイハツ": "Daihatsu",
    "レクサス": "Lexus",
}

MODEL_NAMES = {
    "シルビア": "Silvia",
    "スカイライン": "Skyline",
    "フェアレディZ": "Fairlady Z",
    "スイフト": "Swift",
    "ロードスター": "Roadster",
    "インプレッサ": "Impreza",
    "ランサーエボリューション":
        "Lancer Evolution",
}


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


def parse_table_values(soup):

    labels = [
        "年式",
        "走行距離",
        "修理歴",
        "改造/チューニング内容",
        "特記事項",
        "外装色",
        "型式",
        "グレード",
        "乗車定員",
        "排気量",
        "ハンドル",
        "ボディタイプ",
        "燃料",
        "シフト",
        "駆動方式",
    ]

    values = {}

    strings = [
        text.strip()
        for text in soup.stripped_strings
        if text.strip()
    ]

    for index, text in enumerate(strings):

        for label in labels:

            if text == label:

                if index + 1 < len(strings):
                    values[label] = (
                        strings[index + 1]
                    )

                continue

            if text.startswith(label):

                value = text[
                    len(label):
                ].strip()

                if value:
                    values[label] = value

    return values


def parse_year(value):

    if not value:
        return None

    match = re.search(
        r"(19|20)\d{2}",
        value
    )

    if not match:
        return None

    return int(match.group(0))


def parse_mileage(value):

    if not value:
        return None

    text = value.replace(
        ",",
        ""
    )

    match = re.search(
        r"([\d.]+)\s*万",
        text
    )

    if match:
        return int(
            float(match.group(1))
            * 10000
        )

    match = re.search(
        r"([\d.]+)\s*(?:km|K)",
        text,
        flags=re.I
    )

    if match:
        return int(
            float(match.group(1))
        )

    return None


def parse_price(text):

    match = re.search(
        r"本体価格"
        r"(?:\(税込\))?"
        r".{0,100}?"
        r"([\d.]+)\s*万円",
        text,
        flags=re.S
    )

    if not match:
        return None

    return int(
        float(match.group(1))
        * 10000
    )


def normalize_chassis(value):

    if not value:
        return ""

    value = value.strip()

    if "-" in value:
        return value.split("-")[-1]

    return value


def get_photos(
    soup,
    vehicle_no
):

    photos = []
    seen = set()

    for image in soup.find_all("img"):

        candidates = []

        for attribute in (
            "src",
            "data-src",
            "data-lazy-src"
        ):

            value = image.get(
                attribute
            )

            if value:
                candidates.append(
                    value
                )

        srcset = image.get("srcset")

        if srcset:

            for item in srcset.split(","):

                value = (
                    item.strip()
                    .split(" ")[0]
                )

                if value:
                    candidates.append(
                        value
                    )

        for value in candidates:

            url = urljoin(
                BASE_URL,
                value
            )

            if (
                "cloudfront.net"
                not in url
                and
                "garage-cms"
                not in url
            ):
                continue

            if (
                f"/{vehicle_no}/"
                not in url
            ):
                continue

            if url in seen:
                continue

            seen.add(url)
            photos.append(url)

    return photos


def parse_make_and_model(
    title,
    grade
):

    make = ""
    model_jp = title

    for japanese, english in (
        MAKE_NAMES.items()
    ):

        if title.startswith(
            japanese
        ):

            make = english

            model_jp = title[
                len(japanese):
            ].strip()

            break

    if (
        grade
        and
        model_jp.endswith(grade)
    ):

        model_jp = (
            model_jp[
                :-len(grade)
            ]
            .strip()
        )

    model = MODEL_NAMES.get(
        model_jp,
        model_jp
    )

    return (
        make,
        model,
        model_jp
    )


def get_store(soup):

    for text in soup.stripped_strings:

        if text.startswith(
            "販売店名："
        ):

            return text.split(
                "：",
                1
            )[1].strip()

    return ""


def fetch_vehicle(vehicle):

    vehicle_no = vehicle[
        "source_id"
    ]

    try:

        html = download_html(
            vehicle["source_url"]
        )

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        values = parse_table_values(
            soup
        )

        title_tag = soup.find("h1")

        title = (
            title_tag.get_text(
                " ",
                strip=True
            )
            if title_tag
            else ""
        )

        grade = values.get(
            "グレード",
            ""
        )

        make, model, model_jp = (
            parse_make_and_model(
                title,
                grade
            )
        )

        page_text = soup.get_text(
            " ",
            strip=True
        )

        model_code = values.get(
            "型式",
            ""
        )

        car = {
            "id":
                f"garage-r-{vehicle_no}",

            "source": "GARAGE-R",

            "source_id": vehicle_no,

            "make": make,

            "model": model,

            "model_jp": model_jp,

            "grade": grade,

            "year": parse_year(
                values.get(
                    "年式"
                )
            ),

            "price_jpy":
                parse_price(
                    page_text
                ),

            "mileage_km":
                parse_mileage(
                    values.get(
                        "走行距離"
                    )
                ),

            "chassis":
                normalize_chassis(
                    model_code
                ),

            "model_code":
                model_code,

            "transmission":
                values.get(
                    "シフト",
                    ""
                ),

            "drive":
                values.get(
                    "駆動方式",
                    ""
                ),

            "engine_cc":
                values.get(
                    "排気量",
                    ""
                ),

            "fuel":
                values.get(
                    "燃料",
                    ""
                ),

            "body_type":
                values.get(
                    "ボディタイプ",
                    ""
                ),

            "color":
                values.get(
                    "外装色",
                    ""
                ),

            "repair_history":
                values.get(
                    "修理歴",
                    ""
                ),

            "tuning_notes_jp":
                values.get(
                    "改造/チューニング内容",
                    ""
                ),

            "special_notes_jp":
                values.get(
                    "特記事項",
                    ""
                ),

            "store":
                get_store(
                    soup
                ),

            "source_url":
                vehicle[
                    "source_url"
                ],

            "photo_urls":
                get_photos(
                    soup,
                    vehicle_no
                )
        }

        return (
            car,
            None
        )

    except Exception as error:

        return (
            None,
            str(error)
        )


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

    cars = []
    errors = 0

    print()
    print(
        "Downloading GARAGE-R "
        "vehicle details..."
    )

    with ThreadPoolExecutor(
        max_workers=4
    ) as executor:

        results = executor.map(
            fetch_vehicle,
            vehicles
        )

        for index, result in enumerate(
            results,
            start=1
        ):

            car, error = result

            vehicle_no = vehicles[
                index - 1
            ]["source_id"]

            if error:

                errors += 1

                print(
                    f"Detail {index}/"
                    f"{len(vehicles)}: "
                    f"{vehicle_no} ERROR "
                    f"{error}"
                )

                continue

            cars.append(car)

            print(
                f"Detail {index}/"
                f"{len(vehicles)}: "
                f"{vehicle_no} "
                f"{car['make']} "
                f"{car['model']} "
                f"- "
                f"{len(car['photo_urls'])} "
                f"photos"
            )

    with open(
        "data/garage-r-cars.json",
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
        f"WROTE {len(cars)} "
        "GARAGE-R CARS TO "
        "data/garage-r-cars.json"
    )

    print(
        f"FAILED DETAILS: "
        f"{errors}"
    )


if __name__ == "__main__":
    main()
