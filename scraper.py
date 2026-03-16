import json
import re
from dataclasses import asdict, dataclass, field
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
    image_urls: list[str] = field(default_factory=list)
    options: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
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
            data.image_urls.extend([_clean(x) for x in image if _clean(x)])
            data.image_url = data.image_url or _clean(image[0])
        else:
            image_value = _clean(image)
            if image_value:
                data.image_urls.append(image_value)
                data.image_url = data.image_url or image_value

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


def _extract_next_data_payload(html: str) -> dict[str, Any] | None:
    match = re.search(
        r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if not match:
        return None
    try:
        payload = json.loads(match.group(1).strip())
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _walk_json(node: Any):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk_json(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_json(item)


def _extract_images_from_payload(payload: dict[str, Any]) -> list[str]:
    images: list[str] = []
    for node in _walk_json(payload):
        for key, value in node.items():
            key_name = str(key).lower()
            if isinstance(value, str) and key_name in {"url", "image", "imageurl", "thumb_url", "small_url", "large_url"}:
                if value.startswith("http") and re.search(r"\.(jpg|jpeg|png|webp)", value, flags=re.IGNORECASE):
                    images.append(value)
            if "image" in key_name or "photo" in key_name:
                if isinstance(value, str) and value.startswith("http"):
                    images.append(value)
                elif isinstance(value, list):
                    for element in value:
                        if isinstance(element, str) and element.startswith("http"):
                            images.append(element)
                        elif isinstance(element, dict):
                            for subvalue in element.values():
                                if isinstance(subvalue, str) and subvalue.startswith("http"):
                                    images.append(subvalue)

    dedup: list[str] = []
    for img in images:
        cleaned = img.split("?")[0]
        if cleaned not in dedup:
            dedup.append(cleaned)
    return dedup[:5]


def _extract_attributes_from_payload(data: VehicleData, payload: dict[str, Any]) -> None:
    mapping = {
        "année": "year",
        "annee": "year",
        "kilométrage": "mileage",
        "kilometrage": "mileage",
        "énergie": "fuel",
        "energie": "fuel",
        "carburant": "fuel",
        "boîte de vitesse": "gearbox",
        "boite de vitesse": "gearbox",
        "boîte": "gearbox",
        "boite": "gearbox",
        "puissance fiscale": "power",
        "puissance": "power",
        "prix": "price",
    }

    for node in _walk_json(payload):
        key_candidate = _clean(node.get("key_label") or node.get("label") or node.get("name") or node.get("key"))
        value_candidate = _clean(
            node.get("value_label")
            or node.get("value")
            or node.get("values")
            or node.get("formatted")
        )

        if key_candidate and value_candidate:
            key_norm = key_candidate.lower()
            for fragment, target in mapping.items():
                if fragment in key_norm and not getattr(data, target):
                    setattr(data, target, value_candidate)

        if not data.title:
            title = _clean(node.get("subject") or node.get("title") or node.get("name"))
            if title and len(title) > 6:
                data.title = title

        if not data.price:
            price_raw = node.get("price")
            if isinstance(price_raw, (int, float)):
                data.price = f"{int(price_raw):,} €".replace(",", " ")


def _extract_options_from_description(text: str) -> list[str]:
    if not text:
        return []
    cleaned = re.sub(r"\s+", " ", text)
    chunks = re.split(r"[\n\r•;|,]", cleaned)
    candidates: list[str] = []

    keywords = [
        "clim", "gps", "camera", "radar", "toit", "cuir", "carplay", "android auto",
        "régulateur", "regulateur", "limiteur", "jantes", "bluetooth", "sièges", "sieges",
        "xénon", "xenon", "led", "attelage", "keyless", "démarrage", "demarrage", "4x4",
    ]

    for chunk in chunks:
        part = chunk.strip(" -\t")
        if len(part) < 4 or len(part) > 60:
            continue
        lowered = part.lower()
        if any(word in lowered for word in keywords):
            candidates.append(part)

    dedup: list[str] = []
    for option in candidates:
        if option not in dedup:
            dedup.append(option)
    return dedup[:8]


def extract_vehicle_data(url: str, timeout: int = 20) -> VehicleData:
    req = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
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

    next_payload = _extract_next_data_payload(html)
    if next_payload:
        _extract_attributes_from_payload(data, next_payload)
        images = _extract_images_from_payload(next_payload)
        if images:
            data.image_urls = images
            data.image_url = data.image_url or images[0]

        description_text = ""
        for node in _walk_json(next_payload):
            if not description_text:
                for key in ("description", "body", "text"):
                    candidate = node.get(key)
                    if isinstance(candidate, str) and len(candidate) > 10:
                        description_text = candidate
                        break
        if description_text:
            data.options = _extract_options_from_description(description_text)

    _extract_text_fallback(data, text)

    if not data.options:
        data.options = _extract_options_from_description(text)

    if data.title and (not data.make or not data.model):
        parts = data.title.split()
        if parts:
            data.make = data.make or parts[0]
        if len(parts) > 1:
            data.model = data.model or parts[1]

    if data.image_url and not data.image_urls:
        data.image_urls = [data.image_url]

    return data
