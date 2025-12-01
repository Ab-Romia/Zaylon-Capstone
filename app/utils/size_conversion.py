"""
Size Conversion Utilities
Handles conversion between EU, US, and UK sizing systems for shoes and clothing.
"""

from typing import List, Set, Optional


# Shoe size conversion tables (Men's shoes)
SHOE_SIZE_CONVERSIONS = {
    # EU: (US, UK)
    39: (6.5, 6),
    40: (7, 6.5),
    41: (8, 7),
    42: (8.5, 7.5),
    43: (9.5, 8.5),
    44: (10, 9),
    45: (11, 10),
    46: (12, 11),
    47: (13, 12),
    48: (14, 13),
}

# Clothing size conversion (general approximation)
CLOTHING_SIZE_CONVERSIONS = {
    # EU: (US, UK)
    44: ("XS", "XS"),
    46: ("S", "S"),
    48: ("M", "M"),
    50: ("L", "L"),
    52: ("XL", "XL"),
    54: ("XXL", "XXL"),
}


def normalize_size(size: str) -> List[str]:
    """
    Normalize a size to include all equivalent sizes across sizing systems.

    Args:
        size: Size string (e.g., "47", "12", "L", "EU 47", "US 12")

    Returns:
        List of all equivalent sizes (e.g., ["47", "13", "12"] for EU 47)
    """
    size_clean = size.strip().upper()
    equivalent_sizes = [size_clean]

    # Remove prefixes like "EU", "US", "UK"
    for prefix in ["EU", "US", "UK", "SIZE"]:
        size_clean = size_clean.replace(prefix, "").strip()

    # Try to parse as numeric size (shoes)
    try:
        size_num = int(float(size_clean))

        # Check if it's an EU size
        if size_num in SHOE_SIZE_CONVERSIONS:
            us_size, uk_size = SHOE_SIZE_CONVERSIONS[size_num]
            equivalent_sizes.extend([
                str(size_num),  # EU
                str(us_size),   # US
                str(uk_size),   # UK
                f"EU {size_num}",
                f"US {us_size}",
                f"UK {uk_size}"
            ])
        # Check if it might be a US size (reverse lookup)
        else:
            for eu, (us, uk) in SHOE_SIZE_CONVERSIONS.items():
                if us == size_num or us == float(size_clean):
                    equivalent_sizes.extend([
                        str(eu),
                        str(us),
                        str(uk),
                        f"EU {eu}",
                        f"US {us}",
                        f"UK {uk}"
                    ])
                    break
                elif uk == size_num:
                    equivalent_sizes.extend([
                        str(eu),
                        str(us),
                        str(uk),
                        f"EU {eu}",
                        f"US {us}",
                        f"UK {uk}"
                    ])
                    break
    except ValueError:
        # Not a numeric size, might be clothing (S, M, L, XL)
        # Clothing sizes are usually universal, just normalize format
        pass

    # Remove duplicates and return
    return list(set(equivalent_sizes))


def get_equivalent_sizes(size: str) -> str:
    """
    Get a human-readable string of equivalent sizes.

    Args:
        size: Size string

    Returns:
        Formatted string of equivalents (e.g., "EU 47 / US 13 / UK 12")
    """
    sizes = normalize_size(size)

    # Extract numeric sizes for formatting
    eu_size = None
    us_size = None
    uk_size = None

    try:
        size_num = int(float(size.strip().upper().replace("EU", "").replace("US", "").replace("UK", "").strip()))

        if size_num in SHOE_SIZE_CONVERSIONS:
            eu_size = size_num
            us_size, uk_size = SHOE_SIZE_CONVERSIONS[size_num]
        else:
            # Try reverse lookup
            for eu, (us, uk) in SHOE_SIZE_CONVERSIONS.items():
                if us == size_num or us == float(size_num):
                    eu_size = eu
                    us_size = us
                    uk_size = uk
                    break
                elif uk == size_num:
                    eu_size = eu
                    us_size = us
                    uk_size = uk
                    break

        if eu_size and us_size and uk_size:
            return f"EU {eu_size} / US {us_size} / UK {uk_size}"
    except:
        pass

    return size


def match_size_with_variants(requested_size: str, available_sizes: List[str]) -> Optional[str]:
    """
    Check if a requested size matches any available sizes, considering size system conversions.

    Args:
        requested_size: The size the customer is asking for (e.g., "47", "US 12")
        available_sizes: List of sizes available for the product

    Returns:
        The matching size from available_sizes, or None if no match
    """
    # Normalize the requested size to get all equivalents
    normalized_requested = normalize_size(requested_size)

    # Check if any normalized size matches available sizes
    for available_size in available_sizes:
        available_clean = available_size.strip().upper()

        # Direct match
        if available_clean in normalized_requested:
            return available_size

        # Check if available size's equivalents match
        normalized_available = normalize_size(available_size)
        if any(req in normalized_available for req in normalized_requested):
            return available_size

    return None
