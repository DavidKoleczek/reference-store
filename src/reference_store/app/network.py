"""Who may reach the app when it is served on the local network: devices on that network with its key, and this
machine without one, and only by this machine's own addresses and names."""

import contextlib
from contextvars import ContextVar
from dataclasses import dataclass
import ipaddress
import secrets
import socket

from reference_store.core import config, disk

KEY_FILE = "lan-key"
KEY_COOKIE = "reference_store_key"
KEY_PARAMETER = "key"
# The private ranges, and link-local for two devices joined with no router.
LOCAL_NETWORKS = [
    ipaddress.ip_network(network) for network in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "169.254.0.0/16")
]
# Whether the tool being called was asked for from this machine, which the tools about its disk need.
FROM_THIS_MACHINE: ContextVar[bool] = ContextVar("from_this_machine", default=True)


@dataclass(frozen=True)
class Machine:
    """This machine on the network: its own addresses, and every name a page may be asked for by."""

    addresses: frozenset[str]
    names: frozenset[str]


@dataclass(frozen=True)
class Verdict:
    """What a request gets: refused with a reason, or let in, and whether its key is to be kept as a cookie."""

    allowed: bool
    reason: str = ""
    keep_key: bool = False


def machine() -> Machine:
    """Returns this machine's IPv4 addresses and the names it answers to."""
    addresses = {"127.0.0.1"}
    hostname = socket.gethostname()
    with contextlib.suppress(OSError):
        addresses.update(str(info[4][0]) for info in socket.getaddrinfo(hostname, None, socket.AF_INET))
    primary = lan_address()
    if primary:
        addresses.add(primary)
    names = {*addresses, "localhost", hostname.lower(), f"{hostname.lower()}.local"}
    return Machine(addresses=frozenset(addresses), names=frozenset(names))


def lan_address() -> str | None:
    """Returns the address other devices on the local network reach this machine at, or None without a network."""
    # Connecting a UDP socket sends nothing, and makes the system pick the address it would send from.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        try:
            probe.connect(("10.255.255.255", 1))
            address = str(probe.getsockname()[0])
        except OSError:
            return None
    return address if is_local_network(address) and not address.startswith("127.") else None


def key() -> str:
    """Returns the key devices on the network need, made the first time and kept, so a bookmark keeps working."""
    path = config.home() / KEY_FILE
    kept = (disk.read_text(path) or "").strip()
    if kept:
        return kept
    made = secrets.token_urlsafe(24)
    disk.write_text(path, made + "\n")
    return made


def is_local_network(address: str) -> bool:
    """Returns whether an address is this machine's loopback or on a private network."""
    try:
        parsed = ipaddress.ip_address(address)
    except ValueError:
        return False
    if isinstance(parsed, ipaddress.IPv6Address) and parsed.ipv4_mapped is not None:
        parsed = parsed.ipv4_mapped
    return parsed.is_loopback or any(parsed in network for network in LOCAL_NETWORKS)


def is_this_machine(address: str, here: Machine) -> bool:
    """Returns whether a request came from this machine, by loopback or by one of its own addresses."""
    try:
        parsed = ipaddress.ip_address(address)
    except ValueError:
        return False
    if isinstance(parsed, ipaddress.IPv6Address) and parsed.ipv4_mapped is not None:
        parsed = parsed.ipv4_mapped
    return parsed.is_loopback or str(parsed) in here.addresses


def judge(
    client: str | None,
    host: str | None,
    cookie_key: str | None,
    given_key: str | None,
    key: str,
    here: Machine,
) -> Verdict:
    """Returns whether a request may be answered.

    Its address has to be this machine's or on a private network. `Host` has to name this machine, which keeps a
    website from reaching the app through a domain name it points here. A request from another device needs the key,
    in its cookie or, the first time, in the URL, which is then kept as a cookie.
    """
    if client is None or not is_local_network(client):
        return Verdict(False, "Only devices on the local network can reach this app.")
    name = _host_name(host)
    if name is None or name not in here.names:
        return Verdict(False, "This app only answers to this machine's own addresses and names.")
    if is_this_machine(client, here):
        return Verdict(True)
    if cookie_key is not None and secrets.compare_digest(cookie_key, key):
        return Verdict(True)
    if given_key is not None and secrets.compare_digest(given_key, key):
        return Verdict(True, keep_key=True)
    return Verdict(False, "Open the address or QR code in the app's settings, which has its key.")


def _host_name(host: str | None) -> str | None:
    """The name in a `Host` header, without its port, in lower case."""
    if not host:
        return None
    name = host.strip().lower()
    if name.startswith("["):
        return name[1 : name.find("]")] if "]" in name else None
    return name.rsplit(":", 1)[0] if ":" in name else name
