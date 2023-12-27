"""Testing `pulumi_state_splitter.backend`."""

import typeguard

from . import data, util

with typeguard.install_import_hook("pulumi_state_splitter"):
    import pulumi_state_splitter.backend


class TestBackend(util.TmpDirTest):
    """Testing `pulumi_state_splitter.backend`."""

    def test_split(self):
        """Testing `backend.split`."""
        data.multi_stack_unsplit.save(self._tmp_dir)
        pulumi_state_splitter.backend.split(self._tmp_dir)
        got = util.Directory.load(self._tmp_dir)
        data.multi_stack_split.compare(got, self)

    def test_unsplit(self):
        """Testing `backend.unsplit`."""
        data.multi_stack_split.save(self._tmp_dir)
        pulumi_state_splitter.backend.unsplit(self._tmp_dir)
        got = util.Directory.load(self._tmp_dir)
        data.multi_stack_unsplit.compare(got, self)
