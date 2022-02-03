#!/usr/bin/env python3.9
import os
import sys
import glob
import stat
import re
from io import BytesIO
from hashlib import sha256
from subprocess import PIPE, call
from itertools import chain
import importlib

get_version = importlib.import_module("scanomatic", package=".").get_version
source = importlib.import_module("scanomatic.io.source", package=".")


class MiniLogger:

    @staticmethod
    def info(txt):
        print(f"INFO: {txt}")

    @staticmethod
    def warning(txt):
        print(f"WARNING: {txt}")

    @staticmethod
    def error(txt):
        print(f"ERROR: {txt}")


_logger = MiniLogger()

home_dir = os.path.expanduser("~")

_launcher_text = """[Desktop Entry]
Type=Application
Terminal=false
Icon={user_home}/.scan-o-matic/images/scan-o-matic_icon_256_256.png
Name=Scan-o-Matic
Comment=Large-scale high-quality phenomics platform
Exec={executable_path}
Categories=Science;
"""


def get_package_hash(packages, pattern="*.py", **kwargs):
    return get_hash(
        (p.replace(".", os.sep) for p in packages),
        pattern=pattern,
        **kwargs,
    )


def get_hash_all_files(root, depth=4, **kwargs):
    pattern = ["**"] * depth
    return get_hash(
        (
            "{0}{1}{2}{1}*".format(
                root,
                os.sep,
                os.sep.join(pattern[:d]),
            ) for d in range(depth)
        ),
        **kwargs,
    )


def get_hash(paths, pattern=None, hasher=None, buffsize=65536):
    if hasher is None:
        hasher = sha256()

    files = chain(
        *(
            sorted(
                glob.iglob(os.path.join(path, pattern))
                if pattern else path
            ) for path in paths)
    )
    for file in files:
        try:
            with open(file, 'rb') as f:
                buff = f.read(buffsize)
                while buff:
                    hasher.update(buff)
                    buff = f.read(buffsize)

        except IOError:
            pass

    return hasher


def update_init_file(do_version=True, do_branch=True, release=False):
    cur_dir = os.path.dirname(sys.argv[1])
    if not cur_dir:
        cur_dir = os.path.curdir
    data = source.get_source_information(True, force_location=cur_dir)

    if do_version:
        try:
            data['version'] = source.next_subversion(
                str(data['branch']) if data['branch'] else None,
                get_version(),
            )
        except Exception:
            _logger.warning("Can reach GitHub to verify version")
            data['version'] = source.increase_version(
                source.parse_version(data['version']),
            )

        if release == "minor":
            data['version'] = source.get_minor_release_version(
                data['version'],
            )

        elif release == "major":
            data['version'] = source.get_major_release_version(
                data['version'],
            )

    if do_branch:
        if data['branch'] is None:
            data['branch'] = "++NONE/Probably a release++"

    lines = []
    with open(os.path.join("scanomatic", "__init__.py")) as fh:
        for line in fh:
            if do_version and line.startswith("__version__ = "):
                lines.append("__version__ = \"v{0}\"\n".format(
                    ".".join((str(v) for v in data['version']))
                ))
            elif do_branch and line.startswith("__branch = "):
                lines.append("__branch = \"{0}\"\n".format(data['branch']))
            else:
                lines.append(line)

    with open(os.path.join("scanomatic", "__init__.py"), 'w') as fh:
        fh.writelines(lines)


def _clone_all_files_in(path):
    for child in glob.glob(os.path.join(path, "*")):
        local_child = child[
            len(path) + (not path.endswith(os.sep) and 1 or 0):
        ]
        if os.path.isdir(child):
            for grandchild, _ in _clone_all_files_in(child):
                yield os.path.join(local_child, grandchild), True
        else:
            yield local_child, True


def linux_launcher_install():

    user_home = os.path.expanduser("~")
    exec_path = os.path.join(user_home, '.local', 'bin', 'scan-o-matic')
    if not os.path.isfile(exec_path):
        exec_path = os.path.join(os.sep, 'usr', 'local', 'bin', 'scan-o-matic')
    text = _launcher_text.format(
        user_home=user_home,
        executable_path=exec_path,
    )
    target = os.path.join(
        user_home,
        '.local',
        'share',
        'applications',
        'scan-o-matic.desktop',
    )

    try:
        with open(target, 'w') as fh:
            fh.write(text)
    except IOError:
        _logger.error(
            "Could not install desktop launcher automatically,"
            " you have an odd linux system.",
        )
        _logger.info(
            "You may want to make a manual 'scan-o-matic.desktop' launcher"
            " and place it somewhere nice."
            f"\nIf so, this is what should be its contents:\n\n{text}\n",
        )
    else:
        os.chmod(target, os.stat(target)[stat.ST_MODE] | stat.S_IXUSR)
    _logger.info("Installed desktop launcher for linux menu/dash etc.")


def install_launcher():
    if sys.platform.startswith('linux'):
        linux_launcher_install()
    else:
        _logger.warning(
            "Don't know how to install launchers for this os...",
        )


def uninstall():
    _logger.info("Uninstalling")
    uninstall_lib(_logger)
    uninstall_executables(_logger)
    uninstall_launcher(_logger)


def uninstall_lib(logger: MiniLogger):
    current_location = os.path.abspath(os.curdir)
    os.chdir(os.pardir)
    import shutil

    try:
        import scanomatic as som
        logger.info("Found installation at {0}".format(som.__file__))
        if (
            os.path.abspath(som.__file__) != som.__file__
            or current_location in som.__file__
        ):
            logger.error(
                "Trying to uninstall the local folder, "
                "just remove it instead if this was intended",
            )
        else:

            try:
                shutil.rmtree(os.path.dirname(som.__file__))
            except OSError:
                logger.error(
                    "Not enough permissions to remove {0}".format(
                        os.path.dirname(som.__file__),
                    ),
                )

            parent_dir = os.path.dirname(os.path.dirname(som.__file__))
            for egg in glob.glob(
                os.path.join(parent_dir, "Scan_o_Matic*.egg-info"),
            ):
                try:
                    os.remove(egg)
                except OSError:
                    logger.error(
                        "Not enough permissions to remove {0}".format(egg),
                    )

            logger.info("Removed installation at {0}".format(som.__file__))
    except (ImportError, OSError):
        logger.info("All install location removed")

    logger.info("Uninstall complete")
    os.chdir(current_location)


def uninstall_executables(logger: MiniLogger):
    for path in os.environ['PATH'].split(":"):
        for file_path in glob.glob(os.path.join(path, "scan-o-matic*")):
            logger.info("Removing {0}".format(file_path))
            try:
                os.remove(file_path)
            except OSError:
                logger.warning(
                    f"Not enough permission to remove {file_path}",
                )


def uninstall_launcher(logger: MiniLogger):
    user_home = os.path.expanduser("~")
    if sys.platform.startswith('linux'):
        target = os.path.join(
            user_home,
            '.local',
            'share',
            'applications',
            'scan-o-matic.desktop',
        )
        logger.info(
            f"Removing desktop-launcher/menu integration at {target}",
        )
        try:
            os.remove(target)
        except OSError:
            logger.info(
                "No desktop-launcher/menu integration was found"
                " or no permission to remove it.",
            )

    else:
        logger.info("Not on linux, no launcher should have been installed.")


def purge():
    uninstall()

    import shutil
    settings = os.path.join(home_dir, ".scan-o-matic")

    try:
        shutil.rmtree(os.path.join(home_dir, settings))
        _logger.info("Setting have been purged")
    except IOError:
        _logger.info("No settings found")


def test_executable_is_reachable(path='scan-o-matic'):
    try:
        ret = call([path, '--help'], stdout=PIPE)
    except (IOError, OSError):
        return False

    return ret == 0


def patch_bashrc_if_not_reachable(silent=False):
    if not test_executable_is_reachable():
        for path in [('~', '.local', 'bin')]:
            path = os.path.expanduser(os.path.join(*path))
            if (
                test_executable_is_reachable(path)
                and 'PATH' in os.environ
                and path not in os.environ['PATH']
            ):
                if silent or 'y' in input(
                    "The installation path is not in your environmental variable PATH."  # noqa: E501
                    "\nDo you wish me to append it in your `.bashrc` file? (Y/n)"  # noqa: E501
                ).lower():
                    with open(
                        os.path.expanduser(os.path.join("~", ".bashrc")),
                        'a',
                    ) as fh:
                        fh.write(f"\nexport PATH=$PATH:{path}\n")

                    _logger.info(
                        "You will need to open a new terminal before you can launch `scan-o-matic`."  # noqa: E501
                    )
                else:
                    _logger.info("Skipping PATH patching")


if __name__ == "__main__":

    if len(sys.argv) > 1:
        action = sys.argv[1].lower()

        if action == 'uninstall':
            uninstall()
        elif action == 'purge':
            purge()
        elif action == 'install-launcher':
            install_launcher()
    else:
        _logger.info(
            "Valid options are 'install-launcher', 'uninstall', 'purge'",  # noqa: E501
        )
