"""Tests for SkillsLoader class."""

import json
import os
from pathlib import Path

import pytest

from nanobot.agent.skills import SkillsLoader


class TestSkillsLoaderList:
    """Tests for SkillsLoader.list_skills method."""

    def test_list_skills_workspace_only(self, tmp_path: Path) -> None:
        """Create one skill in workspace, verify it appears with source="workspace"."""
        workspace = tmp_path / "workspace"
        workspace_skills = workspace / "skills"
        workspace_skills.mkdir(parents=True)

        skill_dir = workspace_skills / "test_skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("---\nname: test_skill\n---\n# Test Skill\n")

        loader = SkillsLoader(workspace, builtin_skills_dir=tmp_path / "no_builtins")
        skills = loader.list_skills()

        assert len(skills) == 1
        assert skills[0]["name"] == "test_skill"
        assert skills[0]["source"] == "workspace"
        assert str(skill_file) in skills[0]["path"]

    def test_list_skills_builtin_only(self, tmp_path: Path) -> None:
        """Create one skill in builtin dir, verify source="builtin"."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        builtin_dir = tmp_path / "builtin_skills"
        builtin_dir.mkdir()

        skill_dir = builtin_dir / "builtin_skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("---\nname: builtin_skill\n---\n# Builtin Skill\n")

        loader = SkillsLoader(workspace, builtin_skills_dir=builtin_dir)
        skills = loader.list_skills()

        assert len(skills) == 1
        assert skills[0]["name"] == "builtin_skill"
        assert skills[0]["source"] == "builtin"
        assert str(skill_file) in skills[0]["path"]

    def test_list_skills_workspace_overrides_builtin(self, tmp_path: Path) -> None:
        """Same skill name in both; verify workspace wins (only one entry, source="workspace")."""
        workspace = tmp_path / "workspace"
        workspace_skills = workspace / "skills"
        workspace_skills.mkdir(parents=True)

        builtin_dir = tmp_path / "builtin_skills"
        builtin_dir.mkdir()

        # Create skill in workspace
        skill_dir_ws = workspace_skills / "shared_skill"
        skill_dir_ws.mkdir()
        skill_file_ws = skill_dir_ws / "SKILL.md"
        skill_file_ws.write_text("---\nname: shared_skill\n---\n# Workspace Skill\n")

        # Create same skill in builtin
        skill_dir_builtin = builtin_dir / "shared_skill"
        skill_dir_builtin.mkdir()
        skill_file_builtin = skill_dir_builtin / "SKILL.md"
        skill_file_builtin.write_text("---\nname: shared_skill\n---\n# Builtin Skill\n")

        loader = SkillsLoader(workspace, builtin_skills_dir=builtin_dir)
        skills = loader.list_skills()

        assert len(skills) == 1
        assert skills[0]["name"] == "shared_skill"
        assert skills[0]["source"] == "workspace"
        assert str(skill_file_ws) in skills[0]["path"]

    def test_list_skills_no_filter(self, tmp_path: Path) -> None:
        """Skill with unsatisfied bin requirement; with filter_unavailable=True it's excluded,
        False it's included."""
        workspace = tmp_path / "workspace"
        workspace_skills = workspace / "skills"
        workspace_skills.mkdir(parents=True)

        skill_dir = workspace_skills / "requires_bin_skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            "---\n"
            "name: requires_bin_skill\n"
            'metadata: \'{"nanobot": {"requires": {"bins": ["definitely_not_a_real_binary_xyz"]}}}\'\n'
            "---\n"
            "# Requires Binary Skill\n"
        )

        loader = SkillsLoader(workspace, builtin_skills_dir=tmp_path / "no_builtins")
        skills_filtered = loader.list_skills(filter_unavailable=True)
        skills_unfiltered = loader.list_skills(filter_unavailable=False)

        assert len(skills_filtered) == 0
        assert len(skills_unfiltered) == 1

    def test_list_skills_empty(self, tmp_path: Path) -> None:
        """No skills dirs; returns []."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        loader = SkillsLoader(workspace, builtin_skills_dir=tmp_path / "no_builtins")
        skills = loader.list_skills()

        assert skills == []


class TestSkillsLoaderLoad:
    """Tests for SkillsLoader.load_skill method."""

    def test_load_skill_from_workspace(self, tmp_path: Path) -> None:
        """Workspace skill loaded."""
        workspace = tmp_path / "workspace"
        workspace_skills = workspace / "skills"
        workspace_skills.mkdir(parents=True)

        skill_dir = workspace_skills / "test_skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        expected_content = "---\nname: test_skill\n---\n# Test Skill\n\nContent here."
        skill_file.write_text(expected_content)

        loader = SkillsLoader(workspace, builtin_skills_dir=tmp_path / "no_builtins")
        content = loader.load_skill("test_skill")

        assert content == expected_content

    def test_load_skill_from_builtin(self, tmp_path: Path) -> None:
        """Builtin skill loaded when not in workspace."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        builtin_dir = tmp_path / "builtin_skills"
        builtin_dir.mkdir()

        skill_dir = builtin_dir / "builtin_skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        expected_content = "---\nname: builtin_skill\n---\n# Builtin Skill\n\nContent."
        skill_file.write_text(expected_content)

        loader = SkillsLoader(workspace, builtin_skills_dir=builtin_dir)
        content = loader.load_skill("builtin_skill")

        assert content == expected_content

    def test_load_skill_workspace_priority(self, tmp_path: Path) -> None:
        """Same name in both; workspace content returned."""
        workspace = tmp_path / "workspace"
        workspace_skills = workspace / "skills"
        workspace_skills.mkdir(parents=True)

        builtin_dir = tmp_path / "builtin_skills"
        builtin_dir.mkdir()

        # Create skill in workspace
        skill_dir_ws = workspace_skills / "shared_skill"
        skill_dir_ws.mkdir()
        skill_file_ws = skill_dir_ws / "SKILL.md"
        workspace_content = "---\nname: shared_skill\n---\n# Workspace Content"
        skill_file_ws.write_text(workspace_content)

        # Create same skill in builtin
        skill_dir_builtin = builtin_dir / "shared_skill"
        skill_dir_builtin.mkdir()
        skill_file_builtin = skill_dir_builtin / "SKILL.md"
        builtin_content = "---\nname: shared_skill\n---\n# Builtin Content"
        skill_file_builtin.write_text(builtin_content)

        loader = SkillsLoader(workspace, builtin_skills_dir=builtin_dir)
        content = loader.load_skill("shared_skill")

        assert content == workspace_content

    def test_load_skill_not_found(self, tmp_path: Path) -> None:
        """Returns None."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        loader = SkillsLoader(workspace, builtin_skills_dir=tmp_path / "no_builtins")
        content = loader.load_skill("nonexistent_skill")

        assert content is None


class TestSkillsSummary:
    """Tests for SkillsLoader.build_skills_summary method."""

    def test_build_skills_summary_basic(self, tmp_path: Path) -> None:
        """One skill, verify XML structure contains <skills>, <name>, <location>."""
        workspace = tmp_path / "workspace"
        workspace_skills = workspace / "skills"
        workspace_skills.mkdir(parents=True)

        skill_dir = workspace_skills / "test_skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("---\nname: test_skill\n---\n# Test Skill\n")

        loader = SkillsLoader(workspace, builtin_skills_dir=tmp_path / "no_builtins")
        summary = loader.build_skills_summary()

        assert "<skills>" in summary
        assert "<name>test_skill</name>" in summary
        assert "<location>" in summary
        assert "</skills>" in summary

    def test_build_skills_summary_empty(self, tmp_path: Path) -> None:
        """No skills -> returns ""."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        loader = SkillsLoader(workspace, builtin_skills_dir=tmp_path / "no_builtins")
        summary = loader.build_skills_summary()

        assert summary == ""

    def test_build_skills_summary_xml_escaping(self, tmp_path: Path) -> None:
        """Skill name with & or < -> escaped in output."""
        workspace = tmp_path / "workspace"
        workspace_skills = workspace / "skills"
        workspace_skills.mkdir(parents=True)

        skill_dir = workspace_skills / "special&name"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("---\nname: special&name\n---\n# Test Skill\n")

        loader = SkillsLoader(workspace, builtin_skills_dir=tmp_path / "no_builtins")
        summary = loader.build_skills_summary()

        assert "<name>special&amp;name</name>" in summary
        assert "&lt;" not in summary or "special&amp;name" in summary


class TestSkillsRequirements:
    """Tests for SkillsLoader requirement checking methods."""

    def test_check_requirements_no_requires(self, tmp_path: Path) -> None:
        """Empty meta -> True."""
        workspace = tmp_path / "workspace"
        workspace_skills = workspace / "skills"
        workspace_skills.mkdir(parents=True)

        skill_dir = workspace_skills / "test_skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("---\nname: test_skill\n---\n# Test Skill\n")

        loader = SkillsLoader(workspace, builtin_skills_dir=tmp_path / "no_builtins")
        skill_meta = loader._get_skill_meta("test_skill")

        assert loader._check_requirements(skill_meta) is True

    def test_check_requirements_bin_found(self, tmp_path: Path) -> None:
        """Bin exists (use "python3" which is always present) -> True."""
        workspace = tmp_path / "workspace"
        workspace_skills = workspace / "skills"
        workspace_skills.mkdir(parents=True)

        skill_dir = workspace_skills / "test_skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            "---\n"
            "name: test_skill\n"
            'metadata: \'{"nanobot": {"requires": {"bins": ["python3"]}}}\'\n'
            "---\n"
            "# Test Skill\n"
        )

        loader = SkillsLoader(workspace, builtin_skills_dir=tmp_path / "no_builtins")
        skill_meta = loader._get_skill_meta("test_skill")

        assert loader._check_requirements(skill_meta) is True

    def test_check_requirements_bin_missing(self, tmp_path: Path) -> None:
        """Bin "definitely_not_a_real_binary_xyz" -> False."""
        workspace = tmp_path / "workspace"
        workspace_skills = workspace / "skills"
        workspace_skills.mkdir(parents=True)

        skill_dir = workspace_skills / "test_skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            "---\n"
            "name: test_skill\n"
            'metadata: \'{"nanobot": {"requires": {"bins": ["definitely_not_a_real_binary_xyz"]}}}\'\n'
            "---\n"
            "# Test Skill\n"
        )

        loader = SkillsLoader(workspace, builtin_skills_dir=tmp_path / "no_builtins")
        skill_meta = loader._get_skill_meta("test_skill")

        assert loader._check_requirements(skill_meta) is False

    def test_check_requirements_env_present(self, tmp_path: Path) -> None:
        """Set env var, check -> True."""
        workspace = tmp_path / "workspace"
        workspace_skills = workspace / "skills"
        workspace_skills.mkdir(parents=True)

        skill_dir = workspace_skills / "test_skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            "---\n"
            "name: test_skill\n"
            'metadata: \'{"nanobot": {"requires": {"env": ["NANOBOT_TEST_ENV_VAR"]}}}\'\n'
            "---\n"
            "# Test Skill\n"
        )

        loader = SkillsLoader(workspace, builtin_skills_dir=tmp_path / "no_builtins")
        skill_meta = loader._get_skill_meta("test_skill")

        os.environ["NANOBOT_TEST_ENV_VAR"] = "1"
        try:
            assert loader._check_requirements(skill_meta) is True
        finally:
            del os.environ["NANOBOT_TEST_ENV_VAR"]

    def test_check_requirements_env_missing(self, tmp_path: Path) -> None:
        """Env var not set -> False."""
        workspace = tmp_path / "workspace"
        workspace_skills = workspace / "skills"
        workspace_skills.mkdir(parents=True)

        skill_dir = workspace_skills / "test_skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            "---\n"
            "name: test_skill\n"
            'metadata: \'{"nanobot": {"requires": {"env": ["NANOBOT_MISSING_ENV_VAR"]}}}\'\n'
            "---\n"
            "# Test Skill\n"
        )

        loader = SkillsLoader(workspace, builtin_skills_dir=tmp_path / "no_builtins")
        skill_meta = loader._get_skill_meta("test_skill")

        assert loader._check_requirements(skill_meta) is False


class TestSkillsFrontmatter:
    """Tests for SkillsLoader frontmatter handling methods."""

    def test_strip_frontmatter_with_yaml(self, tmp_path: Path) -> None:
        """Content with ---\\nkey: val\\n---\\nbody -> returns "body"."""
        content = "---\nkey: val\n---\nbody content here"
        loader = SkillsLoader(tmp_path / "workspace", builtin_skills_dir=tmp_path / "no_builtins")

        result = loader._strip_frontmatter(content)

        assert result == "body content here"

    def test_strip_frontmatter_no_yaml(self, tmp_path: Path) -> None:
        """Content without --- -> returned unchanged."""
        content = "plain content without frontmatter"
        loader = SkillsLoader(tmp_path / "workspace", builtin_skills_dir=tmp_path / "no_builtins")

        result = loader._strip_frontmatter(content)

        assert result == "plain content without frontmatter"

    def test_strip_frontmatter_empty(self, tmp_path: Path) -> None:
        """Empty string -> returned unchanged."""
        content = ""
        loader = SkillsLoader(tmp_path / "workspace", builtin_skills_dir=tmp_path / "no_builtins")

        result = loader._strip_frontmatter(content)

        assert result == ""


class TestSkillsMetadata:
    """Tests for SkillsLoader metadata parsing methods."""

    def test_parse_nanobot_metadata_nanobot_key(self, tmp_path: Path) -> None:
        """JSON with "nanobot" key -> returns inner dict."""
        loader = SkillsLoader(tmp_path / "workspace", builtin_skills_dir=tmp_path / "no_builtins")

        raw_json = json.dumps({"nanobot": {"description": "Test skill", "always": True}})
        result = loader._parse_nanobot_metadata(raw_json)

        assert result == {"description": "Test skill", "always": True}

    def test_parse_nanobot_metadata_openclaw_key(self, tmp_path: Path) -> None:
        """JSON with "openclaw" key -> returns inner dict."""
        loader = SkillsLoader(tmp_path / "workspace", builtin_skills_dir=tmp_path / "no_builtins")

        raw_json = json.dumps({"openclaw": {"description": "Test skill", "always": True}})
        result = loader._parse_nanobot_metadata(raw_json)

        assert result == {"description": "Test skill", "always": True}

    def test_parse_nanobot_metadata_invalid_json(self, tmp_path: Path) -> None:
        """Invalid JSON -> returns {}."""
        loader = SkillsLoader(tmp_path / "workspace", builtin_skills_dir=tmp_path / "no_builtins")

        result = loader._parse_nanobot_metadata("not valid json {")

        assert result == {}

    def test_parse_nanobot_metadata_empty_string(self, tmp_path: Path) -> None:
        """Empty string -> returns {}."""
        loader = SkillsLoader(tmp_path / "workspace", builtin_skills_dir=tmp_path / "no_builtins")

        result = loader._parse_nanobot_metadata("")

        assert result == {}


class TestAlwaysSkills:
    """Tests for SkillsLoader.get_always_skills method."""

    def test_get_always_skills_none(self, tmp_path: Path) -> None:
        """No always skills -> []."""
        workspace = tmp_path / "workspace"
        workspace_skills = workspace / "skills"
        workspace_skills.mkdir(parents=True)

        skill_dir = workspace_skills / "normal_skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("---\nname: normal_skill\n---\n# Normal Skill\n")

        # Use a clean builtin dir without the memory skill
        builtin_dir = tmp_path / "builtin_skills"
        builtin_dir.mkdir()

        loader = SkillsLoader(workspace, builtin_skills_dir=builtin_dir)
        always_skills = loader.get_always_skills()

        assert always_skills == []

    def test_get_always_skills_with_always(self, tmp_path: Path) -> None:
        """Skill with `always: true` in frontmatter metadata JSON -> returned."""
        workspace = tmp_path / "workspace"
        workspace_skills = workspace / "skills"
        workspace_skills.mkdir(parents=True)

        skill_dir = workspace_skills / "always_skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            "---\n"
            "name: always_skill\n"
            'metadata: \'{"nanobot": {"always": true}}\'\n'
            "---\n"
            "# Always Skill\n"
        )

        # Use a clean builtin dir without the memory skill
        builtin_dir = tmp_path / "builtin_skills"
        builtin_dir.mkdir()

        loader = SkillsLoader(workspace, builtin_skills_dir=builtin_dir)
        always_skills = loader.get_always_skills()

        assert always_skills == ["always_skill"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
