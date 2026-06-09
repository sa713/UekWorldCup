from __future__ import annotations

import pytest

from worldcup_bot.admin import is_admin_username, normalize_score, parse_score, winner_from_score


def test_admin_username_requires_configured_matching_username():
    assert is_admin_username("project_admin", "project_admin")
    assert is_admin_username("Project_Admin", "project_admin")
    assert is_admin_username("project_admin", "@project_admin")
    assert not is_admin_username(None, "project_admin")
    assert not is_admin_username("other_user", "project_admin")
    assert not is_admin_username("project_admin", None)


def test_parse_score_and_winner_from_score():
    assert parse_score("2:1") == (2, 1)
    assert normalize_score(" 02 : 1 ") == "2:1"
    assert winner_from_score("2:1") == "team1"
    assert winner_from_score("1:2") == "team2"
    assert winner_from_score("0:0") == "draw"


@pytest.mark.parametrize("raw_score", ["", "2-1", "abc", "2:", ":1", "100:0"])
def test_parse_score_rejects_invalid_format(raw_score):
    with pytest.raises(ValueError):
        parse_score(raw_score)
