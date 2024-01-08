"""Testing `pulumi_state_splitter.fs`."""

import typeguard

with typeguard.install_import_hook("pulumi_state_splitter"):
    import pulumi_state_splitter.fs

from . import util


class TestStateFileFilesystem(util.TmpDirTest):
    """Testing `pulumi_state_splitter.fs`."""

    def test_rmdir_if_empty_empty(self):
        """Testing successful removal of an empty directory."""
        pulumi_state_splitter.fs.rmdir_if_empty(self._tmp_dir)
        self.assertFalse(self._tmp_dir.exists())

    def test_rmdir_if_empty_nonempty(self):
        """Testing skipping of removal of a non-empty directory."""
        filename = self._tmp_dir / "foo.txt"
        filename.touch()
        pulumi_state_splitter.fs.rmdir_if_empty(self._tmp_dir)
        self.assertTrue(filename.exists())
        self.assertTrue(self._tmp_dir.exists())

    def test_rmdir_if_empty_fail(self):
        """Testing error handling."""
        with self.assertRaises(FileNotFoundError):
            pulumi_state_splitter.fs.rmdir_if_empty(self._tmp_dir / "nonexistant")
