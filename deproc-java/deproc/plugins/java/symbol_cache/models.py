type compilation_unit_fqn = str
type symbol_name = str
type cache_key = tuple[compilation_unit_fqn, symbol_name]
type cache_value = tuple[set[str], set[str]]
