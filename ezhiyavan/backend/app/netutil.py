"""Client-IP resolution for rate limiting."""

def client_ip(xff, client_host, trust_proxy=False, hops=1):
    """Behind N trusted reverse proxies each proxy APPENDS the address it saw, so the real client is the Nth entry from the RIGHT.
    The leftmost entries are supplied by the client and can be forged, so they must never be used for rate limiting."""
    if trust_proxy and xff:
        parts = [p.strip() for p in xff.split(",") if p.strip()]
        hops = max(1, int(hops))
        if len(parts) >= hops: return parts[-hops]
    return client_host or "?"
