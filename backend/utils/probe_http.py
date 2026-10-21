import re

import requests

from utils import probe_sim


class _Response:
    def __init__(self, sim, url):
        self.status_code = sim.status_code
        self.text = sim.text
        self.url = url

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} Error for url: {self.url}")


def fetch(url, timeout=None):
    """Same call shape as requests.get for http://<probe>:8787/<file>, answered by probe_sim."""
    m = re.match(r"^http://([^:/]+):8787/(.+)$", url)
    if not m:
        raise requests.exceptions.InvalidURL(url)
    try:
        return _Response(probe_sim.fetch_result(m.group(1), m.group(2)), url)
    except probe_sim.SimConnectionError as e:
        raise requests.ConnectionError(str(e))
