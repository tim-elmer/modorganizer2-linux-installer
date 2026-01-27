import sys
from pathlib import Path
from shutil import rmtree, copytree, which
from subprocess import run, CalledProcessError
from tempfile import TemporaryDirectory
from typing import Final

import vdf
from click import (
    argument,
    command,
    confirm,
    option,
    Path as click_Path,
    Choice,
    Abort,
)
from loguru import logger
from pydantic import ValidationError
from vdf import VDFDict

from appinfo import AppInfo, BinaryVdf
from config import Config, Proton

# Value hardcoded in protontricks.
_STEAM_PLAY_MANIFESTS_ID: Final[int] = 891390


def _build_appinfo(apps: dict[str, int], protons: list[Proton]) -> AppInfo:
    """
    Build appinfo
    :param apps: Apps to be "installed"; { name: id }
    :param protons: List of proton versions to be "installed"
    :return: appinfo
    """

    appinfo = AppInfo()

    # Steam Play Manifest
    appinfo.apps = [
        BinaryVdf(
            app_id=_STEAM_PLAY_MANIFESTS_ID,
            keys=appinfo.keys,
            fields=VDFDict(
                {
                    "appinfo": VDFDict(
                        {
                            "appid": _STEAM_PLAY_MANIFESTS_ID,
                            "extended": VDFDict(
                                {
                                    # Checked for by protontricks, but not read
                                    "app_mappings": VDFDict(),
                                    "compat_tools": VDFDict(
                                        {
                                            proton.key: VDFDict(
                                                {
                                                    "appid": proton.id,
                                                    # Aliases is expected to be
                                                    #   a comma-separated list
                                                    #   for some reason.
                                                    "aliases": ",".join(proton.aliases),
                                                }
                                            )
                                            for proton in protons
                                        }
                                    ),
                                }
                            ),
                        }
                    )
                }
            ),
        )
    ]

    # Proton(s)
    appinfo.apps += [
        BinaryVdf(
            app_id=proton.id,
            keys=appinfo.keys,
            fields=VDFDict(
                {
                    "appinfo": VDFDict(
                        {
                            "appid": proton.id,
                            "common": VDFDict({"name": proton.aliases[0]}),
                        }
                    )
                }
            ),
        )
        for proton in protons
    ]

    # Apps
    appinfo.apps += [
        BinaryVdf(
            app_id=id,
            keys=appinfo.keys,
            fields=VDFDict({"appinfo": VDFDict({"appid": id})}),
        )
        for _, id in apps.items()
    ]

    return appinfo


def _build_app_manifest(install_dir: str, id: int, root: Path) -> None:
    """
    Create an app's manifest file
    :param install_dir: Directory the app is installed in, relative to
    `steamapps/common`
    :param id: The app's ID
    :param root: Path to `steamapps`
    :return:
    """

    with open(root / f"appmanifest_{id}.acf", "w") as f:
        f.write(
            vdf.dumps(
                {
                    "AppState": {
                        "appid": str(id),
                        "name": install_dir,
                        "installdir": install_dir,
                    }
                }
            )
        )


def _build_apps(apps: dict[str, int], root: Path) -> None:
    """
    Build app directories and manifest
    :param apps: Dictionary of apps; {path: id}
    :param root: Path to `steamapps` directory
    :return:
    :exception CalledProcessError: Encountered error while initializing Wine
    prefix
    """

    with TemporaryDirectory() as temp:
        # Create one prefix that can be copied to each app to save time, since
        #   prefix creation takes a while.
        logger.info("Initializing wine prefix...")
        run(
            # Wine will create a prefix on any command if one doesn't exist, so
            #   we can call a command that takes the minimal amount of time to
            #   execute to make a new prefix.
            args=["wine", "hostname"],
            check=True,
            env={"WINEDEBUG": "-all", "WINEPREFIX": temp},
            capture_output=True,
        )

        for path, id in apps.items():
            logger.info(f"Building app {path}...")

            # Build app directory structure
            compat_dir = root / "compatdata" / str(id)
            prefix_lock = compat_dir / "pfx.lock"
            install_dir = root / "common" / path

            logger.trace(f"Making compatability directory {compat_dir}")
            compat_dir.mkdir()

            logger.trace(f"Touching prefix lock {prefix_lock}")
            prefix_lock.touch()

            logger.trace(f"Making installation directory {install_dir}")
            install_dir.mkdir()

            # Build app's manifest VDF
            logger.trace("Writing app manifest")
            _build_app_manifest(install_dir, id, root)

            # Copy prefix for app
            logger.trace("Copying prefix...")
            copytree(temp, compat_dir / "pfx", symlinks=True)


def _build_protons(protons: list[Proton], root: Path) -> None:
    """
    Build proton installations
    :param protons: List of proton versions to install
    :param root: Path to `steamapps` directory
    :return:
    """

    for proton in protons:
        logger.info(f"Building proton {proton.aliases[0]}...")

        install_dir = root / "common" / proton.path
        executable = install_dir / "proton"
        files = install_dir / "files"
        bin = files / "bin"

        logger.trace(f"Making installation directory {install_dir}")
        install_dir.mkdir()

        logger.trace(f"Touching executable {executable}")
        executable.touch()

        logger.trace(f"Making files directory {files}")
        files.mkdir()

        logger.trace(f"Making bin directory {bin}")
        bin.mkdir()

        logger.trace("Writing app manifest")
        _build_app_manifest(proton.path, proton.id, root)


def _check_env() -> None:
    """
    Check if environment is suitable.
    :return:
    :exception FileNotFoundError: Couldn't find wine.
    """

    # noinspection PyDeprecation
    # Misuse of deprecation decorator for platform x version problem.
    wine = which("wine")
    if not wine:
        raise FileNotFoundError("Wine not found on path.")
    else:
        logger.debug(f"Found wine: {wine}")

    # * Note: As far as I can tell, protontricks doesn't actually check if it's
    #   running on Windows, so I haven't bothered to here. This would be the
    #   ideal place to check the platform if that turns out to be an issue. :)
    #
    #   That said, it seems unlikely that one would have Wine installed on
    #   Windows. WSL maybe, but IIRC that presents as *nix to Python anyway.


def _clean_root(root: Path, force: bool) -> None:
    """
    Removes existing root, as we aren't about to start spelunking in an
    existing environment to update it.
    :param root: Path to environment root
    :param force: Delete without prompting user
    :return:
    :exception Abort: User canceled prompt
    :exception PermissionError: Permission denied
    """
    if root.exists():
        logger.debug(f"Root {root} found.")
        if not root.is_dir():
            logger.warning(f"The path {root} is not a directory.")
        else:
            logger.debug(f"{root} is a directory.")

        if not force:
            confirm(
                f"The directory {root} already exists, do you want to recreate it? This WILL overwrite existing files.",
                abort=True,
            )
            if not rmtree.avoids_symlink_attacks:
                confirm(
                    f"Your operating system is vulnerable to symlink attacks. Symlinks in the directory {root} may be followed. Continue?",
                    abort=True,
                    err=True,
                )
        else:
            logger.trace("Force set, deleting root without prompt.")
        logger.trace(f"Deleting {root}.")
        rmtree(root, ignore_errors=False)


@command()
@argument("steam_root", type=click_Path(resolve_path=True, path_type=Path))
@option(
    "--delete-existing",
    "delete_existing",
    is_flag=True,
    help="Delete existing steam_root.",
)
@option(
    "--log-level",
    "-l",
    type=Choice(
        [
            "TRACE",
            "DEBUG",
            "INFO",
        ],
        case_sensitive=False,
    ),
    default="INFO",
    help="Set the logging level.",
    show_default=True,
)
def main(steam_root: Path, delete_existing: bool, log_level: str):
    logger.remove()
    logger.add(sys.stderr, level=log_level)
    logger.info("Building mo2-lint development environment...")

    try:
        _check_env()
        config = Config.model_validate_json(
            (Path(__file__).parent.resolve() / "config.json").read_text()
        )

        # Cleaning the root isn't really a prerequisite to successful execution,
        #   so this could probably be an error. However, failure to delete files
        #   in the root means it's highly likely that we'll also fail to create
        #   new ones or overwrite existing ones.
        _clean_root(steam_root, delete_existing)
    except (FileNotFoundError, ValidationError, PermissionError) as e:
        logger.critical(e)
        exit(1)
    except Abort:
        exit(1)

    # TODO: Need to add proton, and create the file 'proton' and dir 'files' in its install dir

    # region Build directory structure
    logger.info("Building directory structure...")
    steam_root.mkdir()
    for path in ("appcache", "config", "steamapps"):
        (steam_root / path).mkdir()

    apps_root = steam_root / "steamapps"
    for path in ("common", "compatdata"):
        (apps_root / path).mkdir()
    # endregion Build directory structure

    # region Fill required files
    with open(steam_root / "appcache" / "appinfo.vdf", "wb") as f:
        f.write(_build_appinfo(config.apps, config.protons).as_bytes())

    (steam_root / "config" / "config.vdf").touch()
    with open(apps_root / "libraryfolders.vdf", "w") as f:
        f.write(
            vdf.dumps(
                {
                    "libraryfolders": {
                        "0": {
                            "path": str(steam_root),
                            "apps": {id: path for path, id in config.apps.items()},
                        }
                    }
                }
            )
        )
    # endregion Fill required files

    logger.info("Building protons...")
    _build_protons(config.protons, apps_root)

    # region Build apps
    logger.info("Building apps...")
    try:
        _build_apps(config.apps, apps_root)
    except CalledProcessError as e:
        logger.critical(e)
        exit(1)
    # endregion Build apps

    logger.success("Done")


if __name__ == "__main__":
    main()
