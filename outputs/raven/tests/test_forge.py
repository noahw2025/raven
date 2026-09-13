import pytest
from fastapi import HTTPException

from app.forge import safe_repo_path


@pytest.mark.parametrize("value,expected",[(".","."),("outputs/raven","outputs/raven"),(r"work\hermes-agent","work/hermes-agent"),("external/my-website","external/my-website")])
def test_safe_repo_path_accepts_workspace_relative_paths(value,expected):
    assert safe_repo_path(value)==expected


@pytest.mark.parametrize("value",["../outside","/etc","C:/Users/private","outputs/raven/.env",".git"])
def test_safe_repo_path_rejects_escape_and_secret_paths(value):
    with pytest.raises(HTTPException):safe_repo_path(value)
