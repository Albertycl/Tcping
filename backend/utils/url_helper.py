"""
URL helper utilities for parsing and sanitizing URLs with paths.
"""
from urllib.parse import urlparse, quote


def parse_target_url(target):
    """
    Parse a target URL and extract components.

    Args:
        target: A URL string like "https://www.example.com/service/api/status"
                or just a hostname like "example.com"

    Returns:
        dict with keys:
            - hostname: The hostname portion (e.g., "www.example.com")
            - port: The port number or None
            - path: The path portion (e.g., "/service/api/status")
            - scheme: "http" or "https" or None
            - full_url: The original target or reconstructed full URL
            - is_url: True if the target was a URL (has scheme)
    """
    result = {
        "hostname": target,
        "port": None,
        "path": "",
        "scheme": None,
        "full_url": target,
        "is_url": False
    }

    # Check if it looks like a URL
    if target.startswith("http://") or target.startswith("https://"):
        result["is_url"] = True
        try:
            parsed = urlparse(target)
            result["hostname"] = parsed.hostname or target
            result["port"] = parsed.port
            result["path"] = parsed.path or ""
            if parsed.query:
                result["path"] += "?" + parsed.query
            result["scheme"] = parsed.scheme
            result["full_url"] = target
        except Exception:
            # If parsing fails, just strip the scheme
            result["hostname"] = target.replace("https://", "").replace("http://", "").split("/")[0]
    else:
        # Check for hostname:port format
        if ":" in target and "/" not in target:
            parts = target.split(":")
            result["hostname"] = parts[0]
            try:
                result["port"] = int(parts[1])
            except (ValueError, IndexError):
                pass
        # Check for hostname/path format (unlikely but possible)
        elif "/" in target:
            parts = target.split("/", 1)
            result["hostname"] = parts[0]
            result["path"] = "/" + parts[1] if len(parts) > 1 else ""

    return result


def sanitize_filename(target):
    """
    Sanitize a target URL/hostname for use in a filename.
    Replaces problematic characters with underscores.

    Args:
        target: A URL or hostname string

    Returns:
        A sanitized string safe for use in filenames
    """
    # Remove scheme
    sanitized = target.replace("https://", "").replace("http://", "")
    # Replace slashes, colons, and other problematic characters
    for char in ['/', '\\', ':', '?', '&', '=', '#', ' ']:
        sanitized = sanitized.replace(char, "_")
    # Remove any double underscores
    while "__" in sanitized:
        sanitized = sanitized.replace("__", "_")
    # Remove trailing underscores
    sanitized = sanitized.strip("_")
    return sanitized
