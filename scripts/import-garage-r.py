import json
import re
import time
import urllib.request

from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin

from bs4 import BeautifulSoup


BASE_URL = "https://garage-r.co.jp"
INVENTORY_URL = BASE_URL + "/cars"
GARAGE_R_IMAGE_HOST = "d11ng1m3kmhgeb.cloudfront.net"


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
    "180SX": "180SX",
    "スカイライン": "Skyline",
    "GT-R": "GT-R",
    "フェアレディZ": "Fairlady Z",
    "スープラ": "Supra",
    "86": "86",
    "GR86": "GR86",
    "MR2": "MR2",
    "MR-S": "MR-S",
    "チェイサー": "Chaser",
    "マークII": "Mark II",
    "スイフト": "Swift",
    "ロードスター": "Roadster",
    "RX-7": "RX-7",
    "RX-8": "RX-8",
    "インプレッサ": "Impreza",
    "WRX": "WRX",
    "BRZ": "BRZ",
    "ランサーエボリューション": "Lancer Evolution",
    "シビック": "Civic",
    "インテグラ": "Integra",
    "S2000": "S2000",
    "NSX": "NSX",
}


def download_html(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "Chrome/152 Safari/537.36"
            )
        },
    )

    with urllib.request.urlopen(
        request,
        timeout=30,
    ) as response:
        return response.read().decode(
            "utf-8",
            errors="replace",
        )


def get_card_price(
    link,
    vehicle_no,
):
    current = link

    for _ in range(15):
        current = current.parent

        if current is None:
            break

        text = current.get_text(
            " ",
            strip=True,
        )

        if vehicle_no not in text:
            continue

        match = re.search(
            r"([0-9]+(?:\.[0-9]+)?)"
            r"\s*万円",
            text,
        )

        if match:
            return int(
                float(
                    match.group(1)
                )
                * 10000
            )

        if re.search(
            r"\bAsk\b",
            text,
            flags=re.I,
        ):
            return None

    return None


def get_inventory():
    vehicles = []
    seen = set()

    for page in range(
        1,
        100,
    ):
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
            html = download_html(
                url
            )

        except Exception as error:
            print(
                f"Stopping at page "
                f"{page}: "
                f"{error}"
            )
            break

        soup = BeautifulSoup(
            html,
            "html.parser",
        )

        page_new_count = 0
        page_price_count = 0

        for link in soup.find_all(
            "a",
            href=True,
        ):
            href = link.get(
                "href",
                "",
            )

            match = re.fullmatch(
                r"/cars/(\d+)",
                href,
            )

            if not match:
                continue

            vehicle_no = (
                match.group(1)
            )

            if vehicle_no in seen:
                continue

            seen.add(
                vehicle_no
            )

            price_jpy = (
                get_card_price(
                    link,
                    vehicle_no,
                )
            )

            if (
                price_jpy
                is not None
            ):
                page_price_count += 1

            vehicles.append({
                "source":
                    "GARAGE-R",

                "source_id":
                    vehicle_no,

                "source_url":
                    urljoin(
                        BASE_URL,
                        href,
                    ),

                "price_jpy":
                    price_jpy,
            })

            page_new_count += 1

        print(
            f"New vehicles on page "
            f"{page}: "
            f"{page_new_count}"
        )

        print(
            f"Prices found on page "
            f"{page}: "
            f"{page_price_count}"
        )

        if page_new_count == 0:
            break

        time.sleep(1)

    return vehicles


def write_inventory_ids(
    vehicles,
):
    rows = []

    for vehicle in vehicles:
        rows.append({
            "source":
                vehicle[
                    "source"
                ],

            "source_id":
                vehicle[
                    "source_id"
                ],

            "source_url":
                vehicle[
                    "source_url"
                ],
        })

    with open(
        "data/garage-r-ids.json",
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            rows,
            file,
            ensure_ascii=False,
            indent=2,
        )


def parse_table_values(
    soup,
):
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

    label_set = set(
        labels
    )

    blocked_values = (
        label_set
        | {
            "基本スペック",
            "状態",
            "装備仕様",
        }
    )

    values = {}

    strings = [
        text.strip()
        for text
        in soup.stripped_strings
        if text.strip()
    ]

    for index, text in enumerate(
        strings
    ):
        for label in labels:

            if text == label:

                if (
                    index + 1
                    >= len(strings)
                ):
                    continue

                value = (
                    strings[
                        index + 1
                    ]
                    .strip()
                )

                if (
                    value
                    in blocked_values
                ):
                    continue

                values[
                    label
                ] = value

                continue

            if text.startswith(
                label
            ):
                value = (
                    text[
                        len(label):
                    ]
                    .lstrip(
                        "：: "
                    )
                    .strip()
                )

                if (
                    value
                    and
                    value
                    not in blocked_values
                ):
                    values[
                        label
                    ] = value

    return values


def parse_year(
    value,
):
    if not value:
        return None

    match = re.search(
        r"(19|20)\d{2}",
        value,
    )

    if not match:
        return None

    return int(
        match.group(0)
    )


def parse_mileage(
    value,
):
    if not value:
        return None

    text = value.replace(
        ",",
        "",
    )

    match = re.search(
        r"([\d.]+)\s*万",
        text,
    )

    if match:
        return int(
            float(
                match.group(1)
            )
            * 10000
        )

    match = re.search(
        r"([\d.]+)"
        r"\s*(?:km|K)",
        text,
        flags=re.I,
    )

    if match:
        return int(
            float(
                match.group(1)
            )
        )

    return None


def normalize_chassis(
    value,
):
    if not value:
        return ""

    value = (
        value.strip()
    )

    if "-" in value:
        return value.split(
            "-"
        )[-1]

    return value


def get_make(
    soup,
):
    strings = [
        text.strip()
        for text
        in soup.stripped_strings
        if text.strip()
    ]

    for text in strings:

        if text in MAKE_NAMES:
            return MAKE_NAMES[
                text
            ]

    page_text = " ".join(
        strings
    )

    for (
        japanese,
        english,
    ) in MAKE_NAMES.items():

        if japanese in page_text:
            return english

    return ""


def get_store(
    soup,
):
    strings = [
        text.strip()
        for text
        in soup.stripped_strings
        if text.strip()
    ]

    for index, text in enumerate(
        strings
    ):

        if text == "販売店名":

            if (
                index + 1
                < len(strings)
            ):
                value = (
                    strings[
                        index + 1
                    ]
                    .strip()
                )

                if value:
                    return value

        if text.startswith(
            "販売店名"
        ):
            value = (
                text[
                    len(
                        "販売店名"
                    ):
                ]
                .lstrip(
                    "：: "
                )
                .strip()
            )

            if value:
                return value

    return ""


def extract_background_url(
    style,
):
    if not style:
        return None

    match = re.search(
        r"""background-image\s*:\s*
        url\(
        ['"]?
        ([^'")]+)
        ['"]?
        \)""",
        style,
        flags=(
            re.I
            | re.X
        ),
    )

    if not match:
        return None

    return (
        match.group(1)
        .strip()
    )


def normalize_gallery_url(
    url,
    vehicle_no,
):
    if not url:
        return None

    url = url.strip()

    expected_path = (
        "/CAR-IMAGE-THUMBNAIL/"
        + vehicle_no
        + "/"
    )

    if (
        GARAGE_R_IMAGE_HOST
        not in url
    ):
        return None

    if (
        expected_path
        not in url
    ):
        return None

    if url.endswith(
        "_sm"
    ):
        url = (
            url[:-3]
            + "_md"
        )

    return url


def get_photos(
    soup,
    vehicle_no,
):
    photos = []
    seen = set()

    slides = soup.select(
        "#carGalleryTrack "
        ".media-gallery-slide"
    )

    for slide in slides:

        url = (
            extract_background_url(
                slide.get(
                    "style",
                    "",
                )
            )
        )

        url = (
            normalize_gallery_url(
                url,
                vehicle_no,
            )
        )

        if not url:
            continue

        if url in seen:
            continue

        seen.add(
            url
        )

        photos.append(
            url
        )

    if photos:
        return photos

    # Fallback if GARAGE-R changes
    # the gallery wrapper but keeps
    # the same image URL format.
    for tag in soup.find_all(
        style=True,
    ):

        url = (
            extract_background_url(
                tag.get(
                    "style",
                    "",
                )
            )
        )

        url = (
            normalize_gallery_url(
                url,
                vehicle_no,
            )
        )

        if not url:
            continue

        if url in seen:
            continue

        seen.add(
            url
        )

        photos.append(
            url
        )

    return photos


def parse_make_and_model(
    title,
    grade,
):
    make = ""
    model_jp = (
        title.strip()
    )

    for (
        japanese,
        english,
    ) in MAKE_NAMES.items():

        if model_jp.startswith(
            japanese
        ):
            make = english

            model_jp = (
                model_jp[
                    len(japanese):
                ]
                .strip()
            )

            break

    if (
        grade
        and
        model_jp.endswith(
            grade
        )
    ):
        model_jp = (
            model_jp[
                :-len(grade)
            ]
            .strip()
        )

    model = MODEL_NAMES.get(
        model_jp,
        model_jp,
    )

    return (
        make,
        model,
        model_jp,
    )


def fetch_vehicle(
    vehicle,
):
    vehicle_no = (
        vehicle[
            "source_id"
        ]
    )

    try:
        html = download_html(
            vehicle[
                "source_url"
            ]
        )

        soup = BeautifulSoup(
            html,
            "html.parser",
        )

        values = (
            parse_table_values(
                soup
            )
        )

        title_tag = (
            soup.find(
                "h1"
            )
        )

        if title_tag:
            title = (
                title_tag
                .get_text(
                    " ",
                    strip=True,
                )
            )
        else:
            title = ""

        grade = values.get(
            "グレード",
            "",
        )

        (
            title_make,
            model,
            model_jp,
        ) = (
            parse_make_and_model(
                title,
                grade,
            )
        )

        model_code = (
            values.get(
                "型式",
                "",
            )
        )

        make = (
            title_make
            or get_make(
                soup
            )
        )

        photos = (
            get_photos(
                soup,
                vehicle_no,
            )
        )

        car = {
            "id":
                "garage-r-"
                + vehicle_no,

            "source":
                "GARAGE-R",

            "source_id":
                vehicle_no,

            "make":
                make,

            "model":
                model,

            "model_jp":
                model_jp,

            "grade":
                grade,

            "year":
                parse_year(
                    values.get(
                        "年式"
                    )
                ),

            "price_jpy":
                vehicle.get(
                    "price_jpy"
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
                    "",
                ),

            "drive":
                values.get(
                    "駆動方式",
                    "",
                ),

            "engine_cc":
                values.get(
                    "排気量",
                    "",
                ),

            "fuel":
                values.get(
                    "燃料",
                    "",
                ),

            "body_type":
                values.get(
                    "ボディタイプ",
                    "",
                ),

            "color":
                values.get(
                    "外装色",
                    "",
                ),

            "repair_history":
                values.get(
                    "修理歴",
                    "",
                ),

            "tuning_notes_jp":
                values.get(
                    "改造/チューニング内容",
                    "",
                ),

            "special_notes_jp":
                values.get(
                    "特記事項",
                    "",
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
                photos,
        }

        return (
            car,
            None,
        )

    except Exception as error:

        return (
            None,
            str(error),
        )


def main():
    print()

    print(
        "Downloading complete "
        "GARAGE-R inventory..."
    )

    vehicles = (
        get_inventory()
    )

    write_inventory_ids(
        vehicles
    )

    print()

    print(
        "FOUND GARAGE-R VEHICLES: "
        + str(
            len(vehicles)
        )
    )

    priced = sum(
        1
        for vehicle
        in vehicles
        if vehicle.get(
            "price_jpy"
        )
        is not None
    )

    print(
        "FOUND GARAGE-R PRICES: "
        + str(
            priced
        )
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
            vehicles,
        )

        for (
            index,
            result,
        ) in enumerate(
            results,
            start=1,
        ):

            car, error = result

            vehicle_no = (
                vehicles[
                    index - 1
                ][
                    "source_id"
                ]
            )

            if error:
                errors += 1

                print(
                    "Detail "
                    + str(index)
                    + "/"
                    + str(
                        len(
                            vehicles
                        )
                    )
                    + ": "
                    + vehicle_no
                    + " ERROR "
                    + error
                )

                continue

            cars.append(
                car
            )

            print(
                "Detail "
                + str(index)
                + "/"
                + str(
                    len(
                        vehicles
                    )
                )
                + ": "
                + vehicle_no
                + " "
                + car["make"]
                + " "
                + car["model"]
                + " ¥"
                + str(
                    car[
                        "price_jpy"
                    ]
                )
                + " - "
                + str(
                    len(
                        car[
                            "photo_urls"
                        ]
                    )
                )
                + " photos"
            )

    with open(
        "data/garage-r-cars.json",
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            cars,
            file,
            ensure_ascii=False,
            indent=2,
        )

    cars_with_photos = sum(
        1
        for car
        in cars
        if car.get(
            "photo_urls"
        )
    )

    total_photos = sum(
        len(
            car.get(
                "photo_urls",
                [],
            )
        )
        for car
        in cars
    )

    print()

    print(
        "WROTE "
        + str(
            len(cars)
        )
        + " GARAGE-R CARS TO "
        + "data/garage-r-cars.json"
    )

    print(
        "CARS WITH PHOTOS: "
        + str(
            cars_with_photos
        )
    )

    print(
        "TOTAL GARAGE-R PHOTOS: "
        + str(
            total_photos
        )
    )

    print(
        "FAILED DETAILS: "
        + str(
            errors
        )
    )


if __name__ == "__main__":
    main()
