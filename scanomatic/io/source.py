import json
import os
import tempfile
import zipfile
from io import BytesIO
from subprocess import PIPE, Popen, call
from typing import Any, Optional

import requests

from scanomatic import get_version
from scanomatic.io.logger import get_logger

from .paths import Paths

_logger = get_logger("Source Checker")


def _read_source_version(base_path) -> Optional[str]:
    try:
        with open(os.path.join(base_path, "scanomatic", "__init__.py")) as fh:
            for line in fh:
                if line.startswith("__version__"):
                    return line.split("=")[1].strip()

    except (TypeError, IOError, IndexError):
        pass

    return None


def _load_source_information() -> dict[str, Any]:
    try:
        with open(Paths().source_location_file, 'r') as fh:
            return json.load(fh)
    except ValueError:
        try:
            with open(Paths().source_location_file, 'r') as fh:
                return {'location': fh.read(), 'branch': None}
        except IOError:
            pass
    except IOError:
        pass

    return {'location': None, 'branch': None}


def get_source_information(test_info=False, force_location=None):

    data = _load_source_information()

    if force_location:
        data['location'] = force_location

    data['version'] = _read_source_version(
        data['location'] if force_location is None else force_location
    )

    if test_info:
        if not has_source(data['location']):
            data['location'] = None
        if (
            not data['branch']
            and data['location']
            and is_under_git_control(data['location'])
        ):
            data['branch'] = get_active_branch(data['location'])

    return data


def has_source(path=None) -> bool:
    if path is None:
        path = get_source_information()['location']

    if path:
        return os.path.isdir(path)
    else:
        return False


def _git_root_navigator(f):

    def _wrapped(path):

        directory = os.getcwd()
        os.chdir(path)
        ret = f(path)
        os.chdir(directory)
        return ret

    return _wrapped


def _manual_git_branch_test() -> Optional[str]:
    try:
        with open(os.path.join(".git", "HEAD")) as fh:
            return fh.readline().split("/")[-1]
    except (IOError, IndexError, TypeError):
        return None


@_git_root_navigator
def is_under_git_control(path) -> bool:
    try:
        retcode = call(['git', 'rev-parse'])
    except OSError:
        retcode = -1
    return retcode == 0


@_git_root_navigator
def get_active_branch(path) -> Optional[str]:
    branch = None
    try:
        p = Popen(['git', 'branch', '--list'], stdout=PIPE)
        o, _ = p.communicate()
    except OSError:
        branch = _manual_git_branch_test()
    else:
        branch = "master"
        for line in o.split(b"\n"):
            if line.startswith(b"*"):
                branch = line.strip(b"* ").decode()
                break
    return branch


@_git_root_navigator
def git_pull(path):
    # TODO: Needs smart handling of pull to not lock etc.
    """
    try:
        p = Popen(['git', 'pull'], stdout=PIPE, stderr=PIPE)
        p.wait(3)
        o, e = p.communicate(None, timeout=1)

        retcode = p.poll()
        if retcode != 0:
            p.kill()
    except OSError:
        return False
    return retcode == 0
    """
    return False


def download(
    base_uri="https://github.com/local-minimum/scanomatic/archive",
    branch=None,
    verbose=False,
):
    global _logger
    if branch is None:
        branch = 'master'

    uri = "{0}/{1}.zip".format(base_uri, branch)
    req = requests.get(uri)

    tf = tempfile.mkdtemp(prefix="SoM_source")

    zipdata = BytesIO()
    zipdata.write(req.content)

    with zipfile.ZipFile(zipdata) as zf:
        for name in zf.namelist():
            zf.extract(name, tf)
            if verbose:
                _logger.info(
                    "Extracting: {0} -> {1}".format(
                        name,
                        os.path.join(tf, name),
                    )
                )

    return os.path.join(tf, tuple(os.walk(tf))[0][1][0])


def install(source_path, branch=None) -> bool:
    try:
        if branch:
            retcode = call(
                [
                    'python',
                    os.path.join(source_path, "setup.py"),
                    "install", "--user",
                    "--default",
                    "--branch",
                    branch,
                ],
                stderr=PIPE,
                stdout=PIPE,
            )
        else:
            retcode = call(
                [
                    'python',
                    os.path.join(source_path, "setup.py"),
                    "install",
                    "--user",
                    "--default",
                ],
                stderr=PIPE,
                stdout=PIPE,
            )

    except OSError:
        return False

    return retcode == 0


def upgrade(branch=None):
    global _logger
    source_info = get_source_information()
    path = source_info['location']
    if branch is None:
        branch = source_info['branch']

    if has_source(path) and is_under_git_control(path):

        if branch is None:
            branch = get_active_branch(path)

        if installed_is_newest_version(branch=branch):

            if git_pull():
                return install(path, branch)

    if not installed_is_newest_version():

        _logger.info("Downloading fresh into temp")
        path = download(branch=branch)
        return install(path, branch)

    else:

        _logger.info("Already newest version")
        return True


def git_version(
    git_repo='https://raw.githubusercontent.com/local-minimum/scanomatic',
    branch='master',
    suffix='scanomatic/__init__.py',
) -> str:
    global _logger
    uri = "/".join((git_repo, branch, suffix))
    for line in requests.get(uri).text.split("\n"):
        if line.startswith("__version__"):
            return line.split("=")[-1].strip('" ')

    _logger.warning(
        f"Could not access any valid version information from uri {uri}",
    )
    return ""


def parse_version(version: Optional[str] = get_version()) -> tuple[int, ...]:
    if version is None:
        return 0, 0

    return tuple(
        int("".join(c for c in v if c in "0123456789"))
        for v in version.split(".")
        if any((c in "0123456789" and c) for c in v)
    )


def highest_version(v1, v2):
    global _logger
    comparable = min(len(v) for v in (v1, v2))
    for i in range(comparable):
        if v1[i] == v2[i]:
            continue
        elif v1[i] > v2[i]:
            return v1
        else:
            return v2

    if len(v1) >= len(v2):
        return v1
    elif len(v2) > len(v1):
        return v2

    _logger.warning("None of the versions is a version!")
    return None


def installed_is_newest_version(branch=None):
    global _logger
    if branch is None:
        branch = get_source_information(True)['branch']
        if branch is None:
            _logger.warning("No branch version so comparing with master")
            branch = 'master'
    current = parse_version()
    online_version = git_version(branch=branch)
    if current == highest_version(current, parse_version(online_version)):
        _logger.info(
            "Already using most recent version {0} (Branch {1})".format(
                get_version(),
                branch,
            ),
        )
        return True
    else:
        _logger.info(
            "There's a new version ({1}) on the branch {0} available (you have installed {2}).".format(  # noqa: E501
                branch,
                get_version(),
                online_version,
            ),
        )
        return False


def next_subversion(branch, current=None) -> tuple[int, ...]:
    online_version = git_version(branch=branch)
    version = parse_version(
        highest_version(
            online_version,
            current if current is not None else get_version(),
        ),
    )
    return increase_version(version)


def increase_version(version: tuple[int, ...]) -> tuple[int, ...]:
    new_version = list(version)
    if len(new_version) == 2:
        new_version += [1]
    elif len(version) == 1:
        new_version += [0, 11]
    else:
        new_version[-1] += 1

    return tuple(new_version)


def get_minor_release_version(
    current_version: tuple[int, ...],
) -> tuple[int, ...]:
    version = list(current_version[:2])
    if len(version) == 0:
        return (0, 1)
    elif len(version) == 1:
        return tuple(version + [1])
    else:
        version[-1] += 1
        return tuple(version)


def get_major_release_version(
    current_version: tuple[int, ...],
) -> tuple[int]:
    version = current_version[:1]
    if len(version) > 0:
        return (version[0] + 1,)
    else:
        return (1,)
