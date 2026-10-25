def vlans_in_range(start, end):
    return list(range(start, end + 1))


def mask_to_prefix(mask):
    return sum(bin(int(o)).count("1") for o in mask.split("."))


def add_vlan(vlan, vlans=None):
    vlans = list(vlans) if vlans is not None else []
    vlans.append(vlan)
    return vlans


def safe_get(data, path):
    cur = data
    for key in path.split("."):
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


def is_valid_vlan(value):
    if isinstance(value, bool):
        return False
    if isinstance(value, str):
        if not value.isdigit():
            return False
        value = int(value)
    if not isinstance(value, int):
        return False
    return 1 <= value <= 4094
