def resolve_relative_import_path(
    relative_path: str,
    parent_fqn: str,
    parent_is_package: bool,
) -> str:
    relative_parts = relative_path.split(".")
    parent_parts = parent_fqn.split(".")
    num_leading_dots = len(relative_path) - len(relative_path.lstrip("."))
    levels_to_pop = num_leading_dots - (1 if parent_is_package else 0)
    for _ in range(levels_to_pop):
        if parent_parts:
            parent_parts.pop()
    relative_parts = [p for p in relative_parts if p]
    return ".".join(parent_parts + relative_parts)
