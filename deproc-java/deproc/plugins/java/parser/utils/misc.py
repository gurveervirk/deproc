ACCESS_MODIFIERS = {"public", "protected", "private"}
MODIFIER_KEYWORDS = {
    "abstract", "default", "final", "native", "sealed", "static",
    "strictfp", "synchronized", "transient", "volatile",
}

def extract_modifier_names(modifiers_node) -> list[str]:
    if modifiers_node is None:
        return []
    modifiers: list[str] = []
    for child in modifiers_node.children:
        if child.is_named:
            continue
        name = child.type.strip()
        if name in ACCESS_MODIFIERS or name in MODIFIER_KEYWORDS:
            modifiers.append(name)
    return modifiers

def visibility_from_modifiers(modifiers: list[str]) -> str:
    if "public" in modifiers:
        return "public"
    if "protected" in modifiers:
        return "protected"
    if "private" in modifiers:
        return "private"
    return "package-private"
