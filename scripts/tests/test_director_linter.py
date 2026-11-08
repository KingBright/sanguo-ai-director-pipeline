import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pipeline import director_linter


class ReferenceImageResolutionTests(unittest.TestCase):
    def make_project(self, root):
        project = root / "project"
        project.mkdir()
        (project / "fact_sheet.toml").write_text("[acoustic_spaces.studio]\n", encoding="utf-8")
        manifest = project / "movie.toml"
        manifest.write_text(
            '[[scenes]]\n'
            'id = "greeting"\n'
            'era = "modern"\n'
            'characters = ["hero"]\n'
            'ref_image = "images/hero.png"\n'
            'line = "你好"\n'
            'action = "The actor nods."\n'
            'arc_phase = "phase_1_daily_empathy"\n'
            'acoustic_space = "studio"\n'
            'camera_motion = "50mm lens, static shot"\n',
            encoding="utf-8",
        )
        return project, manifest

    def make_anchor(self, root):
        anchor = root / "images" / "hero.png"
        anchor.parent.mkdir(parents=True)
        anchor.touch()  # The linter validates existence, not image decoding.

    def test_custom_project_resolves_reference_beside_fact_sheet(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project, manifest = self.make_project(root)
            self.make_anchor(project)
            with patch.object(director_linter, "BASE_DIR", root / "repository"):
                report = director_linter.DirectorLinter(project / "fact_sheet.toml").lint_manifest(manifest)
            self.assertTrue(report.passed, report.format_report())

    def test_custom_project_still_accepts_repository_relative_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project, manifest = self.make_project(root)
            repository = root / "repository"
            self.make_anchor(repository)
            with patch.object(director_linter, "BASE_DIR", repository):
                report = director_linter.DirectorLinter(project / "fact_sheet.toml").lint_manifest(manifest)
            self.assertTrue(report.passed, report.format_report())

    def test_reference_missing_from_both_roots_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project, manifest = self.make_project(root)
            with patch.object(director_linter, "BASE_DIR", root / "repository"):
                report = director_linter.DirectorLinter(project / "fact_sheet.toml").lint_manifest(manifest)
            self.assertFalse(report.passed)
            self.assertTrue(any(
                issue.layer == "L2-视觉资产事实锁" and "文件不存在" in issue.message
                for issue in report.issues
            ))

    def test_default_project_keeps_repository_relative_resolution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project, manifest = self.make_project(root)
            self.make_anchor(project)
            with patch.object(director_linter, "BASE_DIR", project):
                report = director_linter.DirectorLinter().lint_manifest(manifest)
            self.assertTrue(report.passed, report.format_report())


if __name__ == "__main__":
    unittest.main()
