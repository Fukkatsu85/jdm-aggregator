import re
import urllib.request

from urllib.parse import urljoin

from bs4 import BeautifulSoup


BASE_URL = "https://garage-r.co.jp"
TEST_URL = (
    "https://garage-r.co.jp/"
    "cars/301744"
)


def download_html(url):
    request = urllib.request.Request(
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

    with urllib.request.urlopen(
        request,
        timeout=30,
    ) as response:
        return response.read().decode(
            "utf-8",
            errors="replace",
        )


def interesting(value):
    value = str(value).lower()

    keywords = (
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".avif",
        "image",
        "photo",
        "picture",
        "gallery",
        "swiper",
        "slider",
        "cloudfront",
        "amazonaws",
        "storage",
        "cdn",
        "upload",
        "/api/",
        "car_image",
        "car-image",
        "vehicle_image",
        "vehicle-image",
    )

    return any(
        keyword in value
        for keyword in keywords
    )


def main():
    print()
    print(
        "GARAGE-R IMAGE DIAGNOSTIC"
    )
    print(TEST_URL)
    print()

    html = download_html(
        TEST_URL
    )

    print(
        f"HTML LENGTH: "
        f"{len(html)}"
    )

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    print()
    print(
        "========== META =========="
    )

    for tag in soup.find_all("meta"):
        attrs = dict(tag.attrs)

        if interesting(attrs):
            print(attrs)

    print()
    print(
        "========== IMG TAGS =========="
    )

    for index, tag in enumerate(
        soup.find_all("img"),
        start=1,
    ):
        print(
            f"IMG {index}: "
            f"{dict(tag.attrs)}"
        )

    print()
    print(
        "========== SOURCE TAGS =========="
    )

    for index, tag in enumerate(
        soup.find_all("source"),
        start=1,
    ):
        print(
            f"SOURCE {index}: "
            f"{dict(tag.attrs)}"
        )

    print()
    print(
        "========== PICTURE TAGS =========="
    )

    for index, tag in enumerate(
        soup.find_all("picture"),
        start=1,
    ):
        text = str(tag)

        print(
            f"PICTURE {index}: "
            f"{text[:2000]}"
        )

    print()
    print(
        "========== INTERESTING "
        "TAG ATTRIBUTES =========="
    )

    count = 0

    for tag in soup.find_all(True):
        attrs = dict(tag.attrs)

        if not attrs:
            continue

        if not interesting(attrs):
            continue

        count += 1

        print(
            f"TAG {count} "
            f"<{tag.name}>: "
            f"{attrs}"
        )

        if count >= 200:
            break

    print()
    print(
        "========== IMAGE HREFS =========="
    )

    count = 0

    for tag in soup.find_all(
        "a",
        href=True,
    ):
        href = tag.get(
            "href",
            "",
        )

        if not interesting(href):
            continue

        count += 1

        print(
            f"HREF {count}: "
            f"{urljoin(BASE_URL, href)}"
        )

    print()
    print(
        "========== SCRIPT SRC =========="
    )

    for index, tag in enumerate(
        soup.find_all(
            "script",
            src=True,
        ),
        start=1,
    ):
        src = tag.get(
            "src",
            "",
        )

        print(
            f"SCRIPT SRC {index}: "
            f"{urljoin(BASE_URL, src)}"
        )

    print()
    print(
        "========== INLINE SCRIPT "
        "CLUES =========="
    )

    script_count = 0

    for tag in soup.find_all("script"):
        if tag.get("src"):
            continue

        text = (
            tag.string
            or tag.get_text(
                " ",
                strip=True,
            )
            or ""
        )

        if not interesting(text):
            continue

        script_count += 1

        print()
        print(
            f"INLINE SCRIPT "
            f"{script_count}:"
        )

        matches = []

        for line in text.splitlines():
            if interesting(line):
                matches.append(
                    line.strip()
                )

        if matches:
            for line in matches[:30]:
                print(
                    line[:1500]
                )

        else:
            print(
                text[:5000]
            )

        if script_count >= 20:
            break

    print()
    print(
        "========== ABSOLUTE URL "
        "CANDIDATES =========="
    )

    urls = re.findall(
        r"https?://"
        r"[^\"'\s<>\\]+",
        html,
        flags=re.I,
    )

    seen = set()
    count = 0

    for value in urls:
        value = (
            value
            .replace("&amp;", "&")
        )

        if value in seen:
            continue

        seen.add(value)

        if not interesting(value):
            continue

        count += 1

        print(
            f"URL {count}: "
            f"{value[:2000]}"
        )

        if count >= 200:
            break

    print()
    print(
        "========== RELATIVE IMAGE "
        "CANDIDATES =========="
    )

    patterns = [
        r"""["'](
            [^"']+
            \.(?:jpg|jpeg|png|webp|avif)
            (?:\?[^"']*)?
        )["']""",

        r"""url\(
            ['"]?
            ([^)'" ]+)
            ['"]?
        \)""",
    ]

    seen = set()
    count = 0

    for pattern in patterns:
        matches = re.findall(
            pattern,
            html,
            flags=(
                re.I
                | re.X
            ),
        )

        for value in matches:
            if isinstance(
                value,
                tuple,
            ):
                value = value[0]

            value = (
                value.strip()
                .replace(
                    "&amp;",
                    "&",
                )
            )

            if value in seen:
                continue

            seen.add(value)

            count += 1

            print(
                f"REL {count}: "
                f"{urljoin(
                    BASE_URL,
                    value
                )}"
            )

            if count >= 200:
                break

        if count >= 200:
            break

    print()
    print(
        "========== RAW GALLERY / "
        "IMAGE CLUES =========="
    )

    clue_patterns = (
        "gallery",
        "image",
        "photo",
        "swiper",
        "slider",
        "cloudfront",
        "amazonaws",
        "storage",
        "/api/",
    )

    raw_lines = (
        html
        .replace("><", ">\n<")
        .splitlines()
    )

    count = 0

    for line in raw_lines:
        lower = line.lower()

        if not any(
            clue in lower
            for clue in clue_patterns
        ):
            continue

        count += 1

        print(
            f"CLUE {count}: "
            f"{line.strip()[:2500]}"
        )

        if count >= 150:
            break

    print()
    print(
        "========== END DIAGNOSTIC "
        "=========="
    )


if __name__ == "__main__":
    main()
