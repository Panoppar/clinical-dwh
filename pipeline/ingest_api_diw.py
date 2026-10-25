"""Crawls DIW's factory registry (3 provinces: Bangkok, Samut Prakan,
Chachoengsao) amphoe by amphoe and lands each amphoe's raw XLS response in
the landing zone. Does not parse -- that's extract_load_api_diw.py's job.

Adapted from kmch-ml's fetch_diw()/diw_list_amphoe() (Paiiyahh/kmch-ml,
private repo). DIW has no single "whole dataset" endpoint: the tree is
walked province -> amphoe, one throttled POST per amphoe, each returning a
legacy .xls (BIFF, cp874-encoded) file of that amphoe's registered factories.
"""

import re
import time

import requests

import landing_store

DIW_BASE = "http://userdb.diw.go.th/factoryPublic"
DIW_TREE_URL = f"{DIW_BASE}/tumbol.asp"
DIW_DATA_URL = f"{DIW_BASE}/results3.asp"
DIW_PROVINCE_CODES: dict[str, tuple[int, int]] = {
    "กรุงเทพมหานคร": (1, 10), "สมุทรปราการ": (1, 11), "ฉะเชิงเทรา": (4, 24),
}
DIW_MIN_DELAY_S = 1.0
_AMPHOE_LINK_RE_TEMPLATE = r'javascript:sclk\({level0},{level1},(\d+),0\)">([^<]*)</a>'


class _Throttle:
    def __init__(self, min_delay: float):
        self.min_delay = min_delay
        self.last = 0.0

    def wait(self) -> None:
        elapsed = time.monotonic() - self.last
        if elapsed < self.min_delay:
            time.sleep(self.min_delay - elapsed)
        self.last = time.monotonic()


def _list_amphoe(session: requests.Session, throttle: _Throttle, level0: int, level1: int) -> list[tuple[int, str]]:
    throttle.wait()
    resp = session.post(DIW_TREE_URL, data={"level0": str(level0), "level1": str(level1), "level2": "0", "level3": "0"}, timeout=60)
    resp.raise_for_status()
    text = resp.content.decode("cp874", errors="replace")
    pattern = re.compile(_AMPHOE_LINK_RE_TEMPLATE.format(level0=level0, level1=level1))
    out = [(int(code), label.strip()) for code, label in pattern.findall(text)]
    if not out:
        raise RuntimeError(f"DIW: no amphoe list for level0={level0} level1={level1}")
    return out


def run() -> None:
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 kmch-phase3-diw/1.0"})
    throttle = _Throttle(DIW_MIN_DELAY_S)

    for province, (level0, level1) in DIW_PROVINCE_CODES.items():
        amphoe_list = _list_amphoe(session, throttle, level0, level1)
        for level2, amphoe_label in amphoe_list:
            throttle.wait()
            resp = session.post(DIW_DATA_URL, data={"level0": str(level0), "level1": str(level1), "level2": str(level2), "level3": ""}, timeout=60)
            resp.raise_for_status()
            stem = f"{level0}_{level1}_{level2}"
            key, is_new = landing_store.save_version("diw", stem, "xls", resp.content)
            status = "landed new version" if is_new else "unchanged, already landed"
            print(f"[ingest_api_diw] {province} / {amphoe_label}: {status}: {key}")


if __name__ == "__main__":
    run()
