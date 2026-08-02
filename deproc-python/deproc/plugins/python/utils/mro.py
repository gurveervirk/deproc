def c3_merge(seqs: list[list[str]]) -> list[str]:
    result: list[str] = []
    while True:
        nonempty = [s for s in seqs if s]
        if not nonempty:
            return result
        for seq in nonempty:
            candidate = seq[0]
            if not any(candidate in s[1:] for s in nonempty):
                result.append(candidate)
                for s in nonempty:
                    if s and s[0] == candidate:
                        s.pop(0)
                break
        else:
            raise ValueError(f"Inconsistent MRO hierarchy: cannot merge {seqs}")

def compute_mro_from_bases(
    self_fqn: str,
    base_mros: dict[str, list[str] | None],
    base_fqns: list[str],
) -> list[str] | None:
    base_mro_lists: list[list[str]] = []
    for fqn in base_fqns:
        mro = base_mros.get(fqn)
        if mro is None:
            return None
        base_mro_lists.append(list(mro))

    merge_lists: list[list[str]] = base_mro_lists + [list(base_fqns)]
    try:
        return [self_fqn] + c3_merge(merge_lists)
    except ValueError:
        return None
