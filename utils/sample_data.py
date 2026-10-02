"""Small public sample catalog so a new visitor can try the pipeline."""

import zipfile
from io import BytesIO

import pandas as pd


def build_sample_catalog_zip() -> bytes:
    """Three months of a generic catalog with the default column names."""
    products = [
        ("Cedar Pour Over Kettle", "Northbeam", "In stock", 42, "Home"),
        ("Trail Runner Socks 3 Pack", "Fieldline", "In stock", 18, "Apparel"),
        ("Glass Storage Jar 1L", "Harbor & Co", "Low stock", 16, "Home"),
        ("Wireless Desk Lamp", "Northbeam", "In stock", 54, "Lighting"),
    ]
    # Lower rank = more popular. Values shift by month so peaks are visible.
    popularity = {
        "Jan": [4, 2, 6, 1],
        "Jun": [2, 5, 3, 4],
        "Dec": [1, 3, 4, 2],
    }

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for month, ranks in popularity.items():
            frame = pd.DataFrame(
                [
                    {
                        "Product Title": title,
                        "Brand": brand,
                        "Availability": availability,
                        "Price range max.": price,
                        "Popularity rank": rank,
                        "Category": category,
                    }
                    for (title, brand, availability, price, category), rank in zip(products, ranks)
                ]
            )
            payload = BytesIO()
            frame.to_csv(payload, index=False)
            archive.writestr(f"{month}-2024.csv", payload.getvalue())
    return buffer.getvalue()
