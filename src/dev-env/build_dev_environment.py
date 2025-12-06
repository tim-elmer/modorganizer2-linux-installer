from pathlib import Path
from shutil import rmtree, copytree
from struct import pack
from subprocess import run
from tempfile import TemporaryDirectory

import vdf
from click import argument, command, confirm, echo, option, Path as click_Path


@command()
@argument('steam_root', type=click_Path(resolve_path=True, path_type=Path))
@option('--delete-existing', 'delete_existing', is_flag=True)
def main(steam_root: Path, delete_existing: bool):
    # Each app to be "installed" is defined as its app_id and the installation directory
    apps = {
        '397540': 'Borderlands 3'
    }

    # We aren't about to start spelunking in an existing environment to update it, so just delete if it already exists.
    if steam_root.exists():
        if not delete_existing:
            confirm(
                f'The directory {steam_root} already exists, do you want to recreate it? This WILL overwrite existing files.',
                abort=True
            )
            if not rmtree.avoids_symlink_attacks:
                confirm('Your operating system is vulnerable to symlink attacks. Continue?', abort=True)
        rmtree(steam_root, ignore_errors=False)

    # Build directory structure
    echo('Creating directory structure...')
    steam_root.mkdir()
    for path in ('appcache', 'config', 'steamapps'):
        (steam_root / path).mkdir()

    with open(steam_root / 'appcache' / 'appinfo.vdf', 'wb') as f:
        # https://github.com/ValvePython/vdf/issues/13#issuecomment-321700244
        # for buffer in [
        #     # Magic number
        #     b')DV\x07',
        #     # Universe
        #     int(1).to_bytes(4, byteorder='little')
        # ]:
        #     f.write(buffer)
        f.write(pack())
    (steam_root / 'config' / 'config.vdf').touch()
    apps_root = steam_root / 'steamapps'
    for path in ('common', 'compatdata'):
        (apps_root / path).mkdir()

    # Build initial structure for library VDF
    library_folders = {
        'libraryfolders': {
            '0': {
                'path': str(steam_root),
                'apps': {}
            }
        }
    }

    # Build apps
    echo('Building apps...')

    with TemporaryDirectory() as prefix_temporary_directory:
        # Create one prefix that can be copied to each app to save time
        echo('\tInitializing wine prefix...')
        run(
            args=['wine', 'hostname'],
            check=True,
            env={
                'WINEDEBUG': '-all',
                'WINEPREFIX': prefix_temporary_directory
            },
            capture_output=True
        )

        for app_id, install_path in apps.items():
            echo(f'\tBuilding app {install_path}...')

            # Add app to library
            library_folders['libraryfolders']['0']['apps'][app_id] = install_path

            # Build app directory structure
            echo('\t\tBuilding directory structure...')
            app_compat_root = apps_root / 'compatdata' / app_id
            app_compat_root.mkdir()
            # (app_compat_root / 'pfx').mkdir()
            (app_compat_root / 'pfx.lock').touch()
            (apps_root / 'common' / install_path).mkdir()

            # Build app's manifest VDF
            echo('\t\tWriting app manifest...')
            app_manifest = {
                'AppState': {
                    'appid': str(app_id),
                    'name': install_path,
                    'installdir': install_path
                }
            }
            with open(apps_root / f'appmanifest_{app_id}.acf', 'w') as f:
                f.write(vdf.dumps(app_manifest))

            # Copy prefix for app
            echo('\t\tCopying prefix...')
            copytree(prefix_temporary_directory, app_compat_root / 'pfx', symlinks=True)

    echo('Writing library...')
    with open(apps_root / 'libraryfolders.vdf', 'w') as f:
        f.write(vdf.dumps(library_folders))

    echo(f'Finished building `{steam_root}`.')


if __name__ == '__main__':
    main()
