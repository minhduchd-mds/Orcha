"""Loopback desktop bootstrap and same-origin mutation protection."""
import secrets
import ipaddress
from urllib.parse import urlsplit

TOKEN = secrets.token_urlsafe(32)
MAX_BODY = 16 * 1024 * 1024


def guard(handler):
    if not ipaddress.ip_address(handler.client_address[0]).is_loopback:return 403, 'Loopback clients only'
    host = handler.headers.get('Host', '')
    parsed = urlsplit('http://' + host)
    try:
        valid = parsed.hostname in {'localhost', '127.0.0.1', '::1'} and parsed.port == handler.server.server_port
    except ValueError:
        valid = False
    if not valid:
        return 403, 'Untrusted Host'
    origin = handler.headers.get('Origin')
    if origin and origin != 'http://' + host:
        return 403, 'Untrusted Origin'
    if handler.headers.get('Sec-Fetch-Site') == 'cross-site':
        return 403, 'Cross-site request blocked'
    if handler.command == 'POST':
        if handler.headers.get('Content-Type', '').split(';')[0].strip() != 'application/json':
            return 415, 'Content-Type must be application/json'
        if not secrets.compare_digest(handler.headers.get('X-Orcha-Token', ''), TOKEN):
            return 403, 'Desktop session token required'
        try:
            size = int(handler.headers.get('Content-Length', '0'))
        except ValueError:
            return 400, 'Invalid Content-Length'
        if not 0 <= size <= MAX_BODY or handler.headers.get('Transfer-Encoding'):
            return 413, 'Request body too large or unsupported encoding'
    return None
