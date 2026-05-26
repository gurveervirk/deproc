def visibility_from_name(name: str) -> str:
    if name.startswith("__") and not name.endswith("__"):
        return "private"
    elif name.startswith("_"):
        return "protected"
    else:
        return "public"
    