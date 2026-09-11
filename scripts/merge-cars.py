import json


BEFORWARD_FILE = "data/cars.json"
GARAGE_R_FILE = "data/garage-r-cars.json"
OUTPUT_FILE = "data/cars.json"


def load_json(path):
    with open(
        path,
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def save_json(
    path,
    data,
):
    with open(
        path,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )


def normalize_beforward(car):
    result = dict(car)

    result["price_currency"] = "USD"

    if result.get("price_usd") is not None:
        result["price_value"] = (
            result["price_usd"]
        )

        result["price_display"] = (
            "$"
            + format(
                result["price_usd"],
                ",",
            )
        )
    else:
        result["price_value"] = None
        result["price_display"] = (
            "Price unavailable"
        )

    if "price_jpy" not in result:
        result["price_jpy"] = None

    return result


def normalize_garage_r(car):
    result = dict(car)

    result["price_currency"] = "JPY"

    if result.get("price_jpy") is not None:
        result["price_value"] = (
            result["price_jpy"]
        )

        result["price_display"] = (
            "¥"
            + format(
                result["price_jpy"],
                ",",
            )
        )
    else:
        result["price_value"] = None
        result["price_display"] = "ASK"

    if "price_usd" not in result:
        result["price_usd"] = None

    return result


def dedupe_cars(cars):
    seen = set()
    result = []

    for car in cars:
        car_id = car.get("id")

        if not car_id:
            continue

        if car_id in seen:
            continue

        seen.add(car_id)
        result.append(car)

    return result


def main():
    beforward_cars = load_json(
        BEFORWARD_FILE
    )

    garage_r_cars = load_json(
        GARAGE_R_FILE
    )

    print(
        "BE FORWARD cars: "
        + str(
            len(beforward_cars)
        )
    )

    print(
        "GARAGE-R cars: "
        + str(
            len(garage_r_cars)
        )
    )

    normalized_beforward = [
        normalize_beforward(car)
        for car in beforward_cars
        if car.get("source")
        == "BE FORWARD"
    ]

    normalized_garage_r = [
        normalize_garage_r(car)
        for car in garage_r_cars
        if car.get("source")
        == "GARAGE-R"
    ]

    combined = (
        normalized_beforward
        + normalized_garage_r
    )

    combined = dedupe_cars(
        combined
    )

    save_json(
        OUTPUT_FILE,
        combined,
    )

    print()

    print(
        "MERGED CAR INVENTORY"
    )

    print(
        "BE FORWARD: "
        + str(
            len(
                normalized_beforward
            )
        )
    )

    print(
        "GARAGE-R: "
        + str(
            len(
                normalized_garage_r
            )
        )
    )

    print(
        "TOTAL: "
        + str(
            len(combined)
        )
    )


if __name__ == "__main__":
    main()
