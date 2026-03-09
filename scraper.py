import json
import re
from dataclasses import asdict, dataclass
from html import unescape
from typing import Any
from urllib.request import Request, urlopen


@dataclass
class VehicleData:
    source_url: str = ""
    title: str = ""
    make: str = ""
    model: str = ""
    version: str = ""
    year: str = ""
    mileage: str = ""
    fuel: str = ""
    gearbox: str = ""
    power: str = ""
    price: str = ""
    image_url: str = ""

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _find_meta_content(html: str, name: str) -> str:
    pattern = re.compile(
        rf'<meta[^>]+(?:property|name)=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']+)["\']',
        flags=re.IGNORECASE,
    )
    match = pattern.search(html)
    return unescape(match.group(1)).strip() if match else ""


def _extract_json_ld_blocks(html: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for script_data in re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        raw = script_data.strip()
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue

        if isinstance(payload, list):
            blocks.extend([x for x in payload if isinstance(x, dict)])
        elif isinstance(payload, dict):
            blocks.append(payload)

    return blocks


def _extract_from_jsonld(data: VehicleData, blocks: list[dict[str, Any]]) -> None:
    for block in blocks:
        types = block.get("@type", "")
        type_list = types if isinstance(types, list) else [types]
        lowered = " ".join(str(t).lower() for t in type_list)

        if "vehicle" not in lowered and "product" not in lowered:
            continue

        data.title = data.title or _clean(block.get("name"))

        image = block.get("image")
        if isinstance(image, list) and image:
            data.image_url = data.image_url or _clean(image[0])
        else:
            data.image_url = data.image_url or _clean(image)

        brand = block.get("brand")
        if isinstance(brand, dict):
            data.make = data.make or _clean(brand.get("name"))
        else:
            data.make = data.make or _clean(brand)

        model = block.get("model")
        if isinstance(model, dict):
            data.model = data.model or _clean(model.get("name"))
        else:
            data.model = data.model or _clean(model)

        data.version = data.version or _clean(block.get("vehicleConfiguration"))
        data.fuel = data.fuel or _clean(block.get("fuelType"))
        data.gearbox = data.gearbox or _clean(block.get("vehicleTransmission"))

        mileage = block.get("mileageFromOdometer")
        if isinstance(mileage, dict):
            value = _clean(mileage.get("value"))
            unit = _clean(mileage.get("unitCode"))
            data.mileage = data.mileage or f"{value} {unit}".strip()

        offers = block.get("offers")
        if isinstance(offers, dict):
            price = _clean(offers.get("price"))
            currency = _clean(offers.get("priceCurrency")) or "EUR"
            if price:
                data.price = data.price or f"{price} {currency}"

        if not data.year:
            release = _clean(block.get("releaseDate"))
            if release:
                data.year = release[:4]


def _extract_text_fallback(data: VehicleData, text: str) -> None:
    rules = {
        "price": r"(\d{1,3}(?:[ .]\d{3})*(?:,\d{2})?)\s?(?:€|EUR)",
        "year": r"\b(19\d{2}|20\d{2})\b",
        "mileage": r"(\d{1,3}(?:[ .]\d{3})*)\s?km\b",
        "power": r"(\d{2,4})\s?(?:ch|cv)\b",
        "fuel": r"\b(essence|diesel|hybride|électrique|electrique|gpl)\b",
        "gearbox": r"\b(manuelle?|automatique)\b",
    }

    if not data.price and (m := re.search(rules["price"], text, flags=re.IGNORECASE)):
        data.price = f"{m.group(1)} €"
    if not data.year and (m := re.search(rules["year"], text)):
        data.year = m.group(1)
    if not data.mileage and (m := re.search(rules["mileage"], text, flags=re.IGNORECASE)):
        data.mileage = f"{m.group(1)} km"
    if not data.power and (m := re.search(rules["power"], text, flags=re.IGNORECASE)):
        data.power = f"{m.group(1)} ch"
    if not data.fuel and (m := re.search(rules["fuel"], text, flags=re.IGNORECASE)):
        data.fuel = m.group(1).capitalize()
    if not data.gearbox and (m := re.search(rules["gearbox"], text, flags=re.IGNORECASE)):
        data.gearbox = m.group(1).capitalize()


def extract_vehicle_data(url: str, timeout: int = 15) -> VehicleData:
    req = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
        },
    )
    with urlopen(req, timeout=timeout) as response:  # noqa: S310
        html = response.read().decode("utf-8", errors="ignore")

    text = unescape(re.sub(r"<[^>]+>", " ", html))
    text = re.sub(r"\s+", " ", text)

    data = VehicleData(source_url=url)
    _extract_from_jsonld(data, _extract_json_ld_blocks(html))

    data.title = data.title or _find_meta_content(html, "og:title")
    data.image_url = data.image_url or _find_meta_content(html, "og:image")

    _extract_text_fallback(data, text)

    if data.title and (not data.make or not data.model):
        parts = data.title.split()
        if parts:
            data.make = data.make or parts[0]
        if len(parts) > 1:
            data.model = data.model or parts[1]

    return data
