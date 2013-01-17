"""
This participant is used to extract ts files from -ts-devel binary RPMs
and upload them to translation Git repositories.

:term:`Workitem` fields IN

:Parameters:
    ev.actions(list):
        submit request data structure :term:`actions`

:term:`Workitem` fields OUT

:Returns:
    result(boolean):
        True if everything is OK, False otherwise
"""

import os
import shutil
import requests
import json

from tempfile import mkdtemp
from subprocess import check_call, check_output

from boss.obs import BuildServiceParticipant, RepositoryMixin
from boss.rpm import extract_rpm

class ParticipantHandler(BuildServiceParticipant, RepositoryMixin):
    """Participant class as defined in SkyNET API."""

    def __init__(self):
        """Initializator."""

        self.gitconf = None

    def handle_wi_control(self, ctrl):
        """Control job thread."""
        pass

    @BuildServiceParticipant.get_oscrc
    def handle_lifecycle_control(self, ctrl):
        """Control participant thread."""

        if ctrl.message == "start":
            self.gitconf = {
                "basedir":  ctrl.config.get("git", "basedir"),
                "username": ctrl.config.get("git", "username"),
                "password": ctrl.config.get("git", "password"),
                "apiurl":   ctrl.config.get("git", "apiurl"),
                "server":   ctrl.config.get("git", "server"),
            }

    @BuildServiceParticipant.setup_obs
    def handle_wi(self, wid):
        """Handle workitem."""

        wid.result = False

        if not wid.fields.ev.actions:
            raise RuntimeError("Missing mandatory field \"ev.actions\"")

        tmpdir = mkdtemp()

        for action in wid.fields.ev.actions:
            if action["type"] != "submit":
                continue

            obsproject = action["targetproject"]
            packagename = action["targetpackage"]
            targetrepo = self.get_project_targets(obsproject, wid)[0]
            bins = self.get_binary_list(obsproject, packagename, targetrepo)

            workdir = os.path.join(tmpdir, packagename)
            os.mkdir(workdir)
            tsfiles = []
            for tsbin in [pkg for pkg in bins if "-ts-devel-" in pkg]:
                self.download_binary(obsproject, packagename, targetrepo,
                                     tsbin, tmpdir)
                tsfiles.extend(extract_rpm(os.path.join(tmpdir, tsbin),
                                           workdir, "*.ts"))
            if len(tsfiles) == 0:
                print "No ts files in '%s'. Continue..." % packagename
                continue

            projectdir = self.init_gitdir(packagename)

            tpldir = os.path.join(projectdir, "templates")
            if not os.path.isdir(tpldir):
                os.mkdir(tpldir)

            for tsfile in tsfiles:
                shutil.copy(os.path.join(workdir, tsfile), tpldir)

            check_call(["git", "add", "*"], cwd=tpldir)

            if len(check_output(["git", "diff", "--staged"],
                                cwd=projectdir)) == 0:
                print("No updates. Exiting")
                continue

            check_call(["git", "commit", "-m",
                        "translation templates update for some versioned tag"], #TODO: do we have version in wi?
                       cwd=projectdir)
            check_call(["git", "push", "origin", "master"], cwd=projectdir)

        shutil.rmtree(tmpdir)
        wid.result = True

    def init_gitdir(self, reponame):
        """Initialize local clone of remote Git repository."""

        gitdir = os.path.join(self.gitconf["basedir"], reponame)
        if reponame not in os.listdir(self.gitconf["basedir"]):
            # check if repo exists on git server
            gitserv_auth = (self.gitconf["username"], self.gitconf["password"])
            ghresp = requests.get("%s/user/repos" % self.gitconf["apiurl"],
                                  auth=gitserv_auth)
            if reponame not in [repo['name'] for repo in ghresp.json]:
                payload = {
                    'name': reponame,
                    'has_issues': False,
                    'has_wiki': False,
                    'has_downloads': False,
                    'auto_init': True
                }
                ghresp = requests.post("%s/user/repos" % self.gitconf["apiurl"],
                                       auth=gitserv_auth,
                                       headers={
                                           'content-type': 'application/json'
                                       },
                                       data=json.dumps(payload))
                assert ghresp.status_code == 201

            check_call(["git", "clone",
                        "git@%s:%s/%s.git" % (self.gitconf["server"],
                                              self.gitconf["username"],
                                              reponame)],
                       cwd=self.gitconf["basedir"])
        else:
            check_call(["git", "fetch"], cwd=gitdir)
            check_call(["git", "rebase", "origin/master"], cwd=gitdir)
        return gitdir
