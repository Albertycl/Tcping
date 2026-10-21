from flask import Blueprint, request, jsonify
from model import db, WhitelistCondition
import re
from utils import probe_sim
from datetime import datetime
import struct

whitelist_blueprint = Blueprint("whitelist_blueprint", __name__)

@whitelist_blueprint.route('/api/whitelist', methods=['GET'])
def get_whitelist():
    conditions = WhitelistCondition.query.order_by(WhitelistCondition.id.desc()).all()
    return jsonify([c.serialize for c in conditions])

@whitelist_blueprint.route('/api/whitelist', methods=['POST'])
def add_whitelist():
    print(f"DEBUG: WhitelistCondition bind key: {getattr(WhitelistCondition, '__bind_key__', 'None')}")
    data = request.json
    new_condition = WhitelistCondition(
        condition_type=data.get('condition_type'),
        condition_pattern=data.get('condition_pattern'),
        condition_name=data.get('condition_name'),
        description=data.get('description'),
        is_enabled=data.get('is_enabled', True),
        country_specific=data.get('country_specific')
    )
    db.session.add(new_condition)
    db.session.commit()
    
    # Verify persistence
    all_conditions = WhitelistCondition.query.order_by(WhitelistCondition.id.desc()).limit(5).all()
    print(f"DEBUG: All conditions after commit: {[c.id for c in all_conditions]}")
    
    return jsonify(new_condition.serialize), 201

@whitelist_blueprint.route('/api/whitelist/<int:id>', methods=['PUT'])
def update_whitelist(id):
    condition = WhitelistCondition.query.get_or_404(id)
    data = request.json
    
    condition.condition_type = data.get('condition_type', condition.condition_type)
    condition.condition_pattern = data.get('condition_pattern', condition.condition_pattern)
    condition.condition_name = data.get('condition_name', condition.condition_name)
    condition.description = data.get('description', condition.description)
    condition.is_enabled = data.get('is_enabled', condition.is_enabled)
    condition.country_specific = data.get('country_specific', condition.country_specific)
    
    db.session.commit()
    return jsonify(condition.serialize)

@whitelist_blueprint.route('/api/whitelist/<int:id>', methods=['DELETE'])
def delete_whitelist(id):
    condition = WhitelistCondition.query.get_or_404(id)
    db.session.delete(condition)
    db.session.commit()
    return jsonify({"message": "Deleted successfully"})

@whitelist_blueprint.route('/api/check_whitelist', methods=['POST'])
def check_whitelist():
    data = request.json
    content = data.get('content', '')
    country = data.get('country', '')

    print(f"DEBUG check_whitelist: country='{country}', content_length={len(content)}, content_preview='{content[:200]}'")

    # Map ISP codes to their country for whitelist matching
    ISP_TO_COUNTRY = {
        "CT": "China",   # China Telecom
        "CU": "China",   # China Unicom
        "CM": "China",   # China Mobile
    }
    country = ISP_TO_COUNTRY.get(country.upper(), country) if country else country

    # Fetch all enabled conditions
    conditions = WhitelistCondition.query.filter_by(is_enabled=True).all()

    # Separate failure and success conditions
    failure_conditions = [c for c in conditions if c.condition_type == 'failure']
    success_conditions = [c for c in conditions if c.condition_type == 'success']

    # CHECK FAILURE CONDITIONS FIRST (blacklist)
    for condition in failure_conditions:
        # If condition is country-specific, check if it matches the request country
        if condition.country_specific:
            if not country or condition.country_specific.upper() != country.upper():
                continue

        if condition.condition_pattern:
            try:
                # Case insensitive search
                if re.search(condition.condition_pattern, content, re.IGNORECASE):
                    return jsonify({
                        "status": "failure",
                        "reason": f"Blocked: {condition.condition_name or condition.condition_pattern}",
                        "matched_condition": condition.serialize
                    })
            except re.error:
                # Fallback to simple string check if regex fails
                if condition.condition_pattern.lower() in content.lower():
                    return jsonify({
                        "status": "failure",
                        "reason": f"Blocked: {condition.condition_name or condition.condition_pattern}",
                        "matched_condition": condition.serialize
                    })

    # Then check success conditions (whitelist)
    for condition in success_conditions:
        # If condition is country-specific, check if it matches the request country
        if condition.country_specific:
            if not country or condition.country_specific.upper() != country.upper():
                continue

        if condition.condition_pattern:
            try:
                # Case insensitive search
                if re.search(condition.condition_pattern, content, re.IGNORECASE):
                    return jsonify({
                        "status": "success",
                        "matched_condition": condition.serialize
                    })
            except re.error:
                # Fallback to simple string check if regex fails
                if condition.condition_pattern.lower() in content.lower():
                    return jsonify({
                        "status": "success",
                        "matched_condition": condition.serialize
                    })

    return jsonify({
        "status": "failure",
        "reason": "No whitelist match found (DB rules)"
    })


def decimal_to_ip(decimal_val):
    """Convert a decimal value to IP address (big-endian, like ping does)"""
    try:
        packed = struct.pack('>I', int(decimal_val))
        return '.'.join(str(b) for b in packed)
    except:
        return None


def decimal_to_ip_reversed(decimal_val):
    """Convert a decimal value to IP address (little-endian / reversed bytes)"""
    try:
        packed = struct.pack('>I', int(decimal_val))
        return '.'.join(str(b) for b in reversed(packed))
    except:
        return None


def get_ltm_config_urls():
    """Generate dynamic LTM config file URLs based on current date and yesterday"""
    from datetime import timedelta

    today = datetime.now()
    yesterday = today - timedelta(days=1)

    date_str_today = today.strftime("%Y%m%d")
    date_str_yesterday = yesterday.strftime("%Y%m%d")

    base_url = "http://ltm-backup.demo.invalid/RIO_Config"

    # Generate URLs for both Alpha and Bravo datacenters, for today and yesterday
    urls = [
        # Today's configs
        f"{base_url}/Alpha_{date_str_today}/Alpha-LTM01_{date_str_today}-1700.txt",
        f"{base_url}/Bravo_{date_str_today}/Bravo-LTM01_{date_str_today}-1700.txt",
        # Yesterday's configs (in case today's aren't available yet)
        f"{base_url}/Alpha_{date_str_yesterday}/Alpha-LTM01_{date_str_yesterday}-1700.txt",
        f"{base_url}/Bravo_{date_str_yesterday}/Bravo-LTM01_{date_str_yesterday}-1700.txt",
    ]

    return urls


def extract_f5_cookies(content):
    """Extract IPs from all F5 BigIP encoded cookies in curl response.

    F5 cookie format: cookiename=decimal.port.0000
    Examples: oneapi=1613238026.20480.0000, tap-aff=1764232970.20480.0000
    """
    # Pattern matches: cookie_name=decimal.port.0000
    # The decimal is 8-10 digits, port is typically 5 digits
    pattern = r'([a-zA-Z0-9_-]+)=(\d{8,10})\.(\d+)\.0000'
    matches = re.findall(pattern, content)

    cookies = []
    for cookie_name, decimal_val, port in matches:
        ip_big_endian = decimal_to_ip(decimal_val)
        ip_little_endian = decimal_to_ip_reversed(decimal_val)
        cookies.append({
            "cookie_name": cookie_name,
            "decimal": decimal_val,
            "port": port,
            "ip_standard": ip_big_endian,      # 96.40.15.10 format
            "ip_reversed": ip_little_endian    # reversed byte order (F5 uses this)
        })

    return cookies if cookies else None


@whitelist_blueprint.route('/api/check_ltm_config', methods=['POST'])
def check_ltm_config():
    """
    Check if server IPs from F5 BigIP cookies exist in LTM backup config files.
    Checks all cookies with format: name=decimal.port.0000
    """
    data = request.json
    content = data.get('content', '')

    # Extract all F5 cookies from content
    cookies = extract_f5_cookies(content)

    if not cookies:
        return jsonify({
            "status": "no_cookie",
            "message": "No F5 BigIP cookies found in response",
            "available_files": []
        })

    config_urls = get_ltm_config_urls()
    available_files = []  # Only files that exist (not 404)
    config_contents = {}  # Cache config file contents

    # Fetch all config files once
    for url in config_urls:
        try:
            text = probe_sim.ltm_config_text(url)
            if text is not None:
                available_files.append(url)
                config_contents[url] = text
        except Exception as e:
            print(f"Error fetching LTM config {url}: {e}")

    # Check each cookie against all config files
    matched_cookies = []
    unmatched_cookies = []

    for cookie in cookies:
        cookie_matched = False
        cookie_matches = []

        for url, config_content in config_contents.items():
            # Search for both IP formats
            if cookie["ip_standard"] and cookie["ip_standard"] in config_content:
                cookie_matches.append({
                    "url": url,
                    "matched_ip": cookie["ip_standard"],
                    "ip_format": "standard"
                })
                cookie_matched = True
            elif cookie["ip_reversed"] and cookie["ip_reversed"] in config_content:
                cookie_matches.append({
                    "url": url,
                    "matched_ip": cookie["ip_reversed"],
                    "ip_format": "reversed"
                })
                cookie_matched = True

        if cookie_matched:
            matched_cookies.append({
                "cookie": cookie,
                "matched_files": cookie_matches
            })
        else:
            unmatched_cookies.append(cookie)

    if matched_cookies:
        return jsonify({
            "status": "success",
            "message": f"Found {len(matched_cookies)} cookie(s) with IP in LTM config",
            "matched_cookies": matched_cookies,
            "unmatched_cookies": unmatched_cookies,
            "available_files": available_files,
            # Keep backward compatibility
            "ip_info": cookies[0] if cookies else None,
            "matched_files": matched_cookies[0]["matched_files"] if matched_cookies else []
        })
    else:
        cookie_ips = [f"{c['cookie_name']}={c['ip_reversed']}" for c in cookies]
        return jsonify({
            "status": "failure",
            "message": f"No cookie IPs found in LTM configs: {', '.join(cookie_ips)}",
            "cookies": cookies,
            "unmatched_cookies": unmatched_cookies,
            "available_files": available_files,
            # Keep backward compatibility
            "ip_info": cookies[0] if cookies else None
        })
