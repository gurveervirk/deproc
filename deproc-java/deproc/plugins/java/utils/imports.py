def resolve_java_import(
    import_path: str,
    import_kind: str,
) -> str:
    """Resolve a Java import path to a fully qualified type or package name.

    import_kind:
        "single_type"       → import com.example.Foo;          → "com.example.Foo"
        "on_demand"         → import com.example.*;             → "com.example"
        "single_static"     → import static com.example.Foo.bar; → "com.example.Foo"
        "static_on_demand"  → import static com.example.Foo.*;  → "com.example.Foo"

    For "on_demand", returns the package FQN (caller must search registry for types in that package).
    For "static_on_demand", returns the containing class FQN (caller must search for static members).
    """
    if import_kind in ("on_demand", "static_on_demand"):
        if import_path.endswith(".*"):
            return import_path[:-2]
        return import_path
    if import_kind == "single_static":
        if "." in import_path:
            return import_path.rsplit(".", 1)[0]
        return import_path
    return import_path
