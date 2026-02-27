import ipaddress

def validate_ip(ip_addr: str):
    """
    Validates IPv4/IPv6 addresses.
    Raises ValueError if invalid.
    """
    ip_addr = ip_addr.strip()
    try:
        ipaddress.ip_address(ip_addr)
    except ValueError:
        raise
    return ip_addr