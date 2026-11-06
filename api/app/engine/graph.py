"""The catalogue as a small knowledge graph.

    BusinessType --in--> Segment --typically_needs--> Need --served_by--> Product
    Product --requires_one_of--> Product          (from the catalogue)
    Product --eligible_if--> Rule                 (tier, staff, sites, GSTIN, feasibility)

Needs are what the owner cares about ("UPI must not fail"); products are what Accel sells.
Segment defaults are grounded in what last quarter's activated customers actually bought.
"""
from __future__ import annotations

from dataclasses import dataclass

# need -> ordered chain of products that can serve it (first eligible wins)
NEED_CHAIN: dict[str, tuple[str, ...]] = {
    "internet": (),            # resolved by choose_connectivity()
    "high_speed": (),          # connectivity with speed >= 1 Gbps preference
    "dedicated_line": (),      # connectivity with SLA preference
    "mobile_lines": ("P08", "P07"),
    "guest_wifi": ("P22",),
    "cctv": ("P23",),
    "pos": ("P19",),
    "whatsapp": ("P15",),
    "sms": ("P14",),
    "website": ("P18",),
    "email": ("P16",),
    "backup": ("P17",),
    "endpoint": ("P20",),
    "firewall": ("P21",),
    "failover": ("P09",),
    "sdwan": ("P10",),
    "static_ip": ("P11",),
    "telephony": ("P12",),
    "toll_free": ("P13",),
    "iot": ("P24",),
    "fleet": ("P25",),
}

# When the first choice is not allowed, offer this instead (and say why).
FALLBACK: dict[str, str] = {
    "P03": "P02",  # 1 Gbps -> 300 Mbps
    "P06": "P05",  # leased line 100 -> 20
    "P05": "P02",  # leased line -> fibre 300 (+ failover suggested)
    "P10": "P09",  # SD-WAN -> per-site failover
    "P12": "P08",  # cloud telephony -> business postpaid lines
    "P21": "P20",  # managed firewall -> endpoint security
    "P15": "P18",  # WhatsApp API (needs GSTIN) -> website starter
    "P02": "P01",
    "P01": "P04",  # fibre not feasible -> AirFiber
}

CONNECTIVITY = ("P01", "P02", "P03", "P04", "P05", "P06")
FIBRE = ("P01", "P02", "P03")

# Default needs per segment, from the take rates of activated bundles (smb_leads.csv).
SEGMENT_DEFAULTS: dict[str, tuple[str, ...]] = {
    "micro": ("internet", "mobile_lines"),
    "prof": ("internet", "email", "mobile_lines", "endpoint", "backup"),
    "multi": ("internet", "mobile_lines", "failover", "pos", "cctv", "sdwan"),
    "mfg": ("internet", "email", "mobile_lines", "endpoint", "firewall"),
}
# Shown as one-tap add-ons on the quote screen.
SEGMENT_ADDONS: dict[str, tuple[str, ...]] = {
    "micro": ("guest_wifi", "pos", "cctv", "whatsapp", "website"),
    "prof": ("static_ip", "failover", "telephony", "sms", "website"),
    "multi": ("toll_free", "whatsapp", "guest_wifi", "fleet", "telephony"),
    "mfg": ("cctv", "iot", "static_ip", "fleet", "failover"),
}
# Counter-based micro businesses usually want billing on day one.
COUNTER_BUSINESSES = {"kirana store", "pharmacy", "bakery", "sweet shop", "stationery shop", "hardware store"}

# How a product's quantity is derived (unit in the catalogue -> profile slot).
QTY_RULE: dict[str, str] = {
    "per site": "sites", "per user": "users", "per device": "devices", "per camera": "cameras",
    "per counter": "counters", "per line": "lines", "per channel": "channels", "per vehicle": "vehicles",
    "per IP": "one", "per number": "one", "per pack": "one", "per account": "one",
}
# product-specific overrides (P24 is "per device" but counts machines)
QTY_OVERRIDE = {"P24": "machines"}

PRIORITY = [
    "dedicated_line", "high_speed", "internet", "failover", "sdwan", "static_ip", "mobile_lines",
    "telephony", "toll_free", "guest_wifi", "pos", "cctv", "whatsapp", "sms", "website", "email",
    "backup", "endpoint", "firewall", "iot", "fleet",
]


@dataclass(frozen=True)
class NeedInfo:
    code: str
    label: str


NEED_LABELS = {
    "internet": "Reliable internet", "high_speed": "High-speed internet (1 Gbps)",
    "dedicated_line": "Dedicated line with uptime SLA", "mobile_lines": "Business mobile lines",
    "guest_wifi": "Customer Wi-Fi", "cctv": "CCTV", "pos": "Billing and UPI/card counter",
    "whatsapp": "WhatsApp catalogue and chats", "sms": "Bulk SMS", "website": "Website",
    "email": "Business email", "backup": "Cloud backup", "endpoint": "Antivirus for PCs and phones",
    "firewall": "Managed firewall", "failover": "Backup internet when the main link fails",
    "sdwan": "Central management of all sites", "static_ip": "Static IP", "telephony": "Office phone lines with IVR",
    "toll_free": "Toll-free number", "iot": "Machine monitoring", "fleet": "Vehicle tracking",
}
