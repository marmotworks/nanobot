from __future__ import annotations


def match_milestone_label(label: str, milestone_num: str) -> bool:
    """Return True if a registry label matches a milestone number.

    Matches if the label equals the milestone_num exactly, or if the label
    starts with '{milestone_num} ' (with a trailing space, to avoid
    '30.1' matching '30.10').

    Examples:
        match_milestone_label("30.1 tag_in_atomic", "30.1") -> True
        match_milestone_label("30.1", "30.1") -> True
        match_milestone_label("30.10 something", "30.1") -> False
        match_milestone_label("30.2 other", "30.1") -> False
    """
    return label == milestone_num or label.startswith(f"{milestone_num} ")
