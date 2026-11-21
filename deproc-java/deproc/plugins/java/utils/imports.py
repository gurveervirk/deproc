def resolve_java_import(
    import_path: str,
    import_kind: str,
) -> str:
    """Resolve a Java import path to a fully qualified type or package name.

    Args:
        import_path: The imported name, for example ``com.example.Foo.bar`` or
            ``com.example.*``.
        import_kind: ``single_type``, ``on_demand``, ``single_static``, or
            ``static_on_demand``.

    Returns:
        The type for ``single_type``, the package for ``on_demand``, and the
        containing class for the two static kinds. For the on-demand kinds, the
        caller searches for the package's types or the class's static members.
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
