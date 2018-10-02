from __future__ import absolute_import

import logging
import os

from pip._vendor.six.moves.urllib import parse as urllib_parse

from pip._internal.download import path_to_url
from pip._internal.utils.misc import (
    display_path, make_vcs_requirement_url, rmtree,
)
from pip._internal.vcs import VersionControl, vcs

logger = logging.getLogger(__name__)


class Bazaar(VersionControl):
    name = 'bzr'
    dirname = '.bzr'
    repo_name = 'branch'
    schemes = (
        'bzr', 'bzr+http', 'bzr+https', 'bzr+ssh', 'bzr+sftp', 'bzr+ftp',
        'bzr+lp',
    )

    def __init__(self, url=None, *args, **kwargs):
        super(Bazaar, self).__init__(url, *args, **kwargs)
        # This is only needed for python <2.7.5
        # Register lp but do not expose as a scheme to support bzr+lp.
        if getattr(urllib_parse, 'uses_fragment', None):
            urllib_parse.uses_fragment.extend(['lp'])

    def get_base_rev_args(self, rev):
        return ['-r', rev]

    def export(self, location):
        """
        Export the Bazaar repository at the url to the destination location
        """
        # Remove the location to make sure Bazaar can export it correctly
        if os.path.exists(location):
            rmtree(location)

        url, rev_options = self.get_url_rev_options()
        self.run_command(
            ['export', location, url] + rev_options.to_args(),
            show_stdout=False,
        )

    def fetch_new(self, dest, url, rev_options):
        rev_display = rev_options.to_display()
        logger.info(
            'Checking out %s%s to %s',
            url,
            rev_display,
            display_path(dest),
        )
        cmd_args = (['checkout', '--lightweight', '-q'] +
                    rev_options.to_args() + [url, dest])
        self.run_command(cmd_args)

    def switch(self, dest, url, rev_options):
        self.run_command(['switch', url], cwd=dest)

    def update(self, dest, url, rev_options):
        cmd_args = ['update', '-q'] + rev_options.to_args()
        self.run_command(cmd_args, cwd=dest)

    def get_url_rev_and_auth(self, url):
        # hotfix the URL scheme after removing bzr+ from bzr+ssh:// readd it
        url, rev, user_pass = super(Bazaar, self).get_url_rev_and_auth(url)
        if url.startswith('ssh://'):
            url = 'bzr+' + url
        return url, rev, user_pass

    def get_url(self, location):
        urls = self.run_command(['info'], show_stdout=False, cwd=location)
        for line in urls.splitlines():
            line = line.strip()
            for x in ('checkout of branch: ',
                      'parent branch: '):
                if line.startswith(x):
                    repo = line.split(x)[1]
                    if self._is_local_repository(repo):
                        return path_to_url(repo)
                    return repo
        return None

    def get_revision(self, location):
        revision = self.run_command(
            ['revno'], show_stdout=False, cwd=location,
        )
        return revision.splitlines()[-1]

    def get_src_requirement(self, dist, location):
        repo = self.get_url(location)
        if not repo:
            return None
        if not repo.lower().startswith('bzr:'):
            repo = 'bzr+' + repo
        current_rev = self.get_revision(location)
        egg_project_name = dist.egg_name().split('-', 1)[0]
        return make_vcs_requirement_url(repo, current_rev, egg_project_name)

    def is_commit_id_equal(self, dest, name):
        """Always assume the versions don't match"""
        return False


vcs.register(Bazaar)
