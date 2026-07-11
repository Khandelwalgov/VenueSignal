from enum import Enum

class NodeStatus(str, Enum):
    OPEN = "OPEN"
    RESTRICTED = "RESTRICTED"
    CLOSED = "CLOSED"

class EdgeStatus(str, Enum):
    OPEN = "OPEN"
    RESTRICTED = "RESTRICTED"
    CLOSED = "CLOSED"

class AssetStatus(str, Enum):
    OPERATIONAL = "OPERATIONAL"
    DEGRADED = "DEGRADED"
    OUT_OF_SERVICE = "OUT_OF_SERVICE"
    UNKNOWN = "UNKNOWN"

class ZoneStatus(str, Enum):
    NORMAL = "NORMAL"
    BUSY = "BUSY"
    RESTRICTED = "RESTRICTED"
    CLOSED = "CLOSED"
