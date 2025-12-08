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
                confirm(
                    'Your operating system is vulnerable to symlink attacks. Continue?',
                    abort=True)
        rmtree(steam_root, ignore_errors=False)

    # Build directory structure
    echo('Creating directory structure...')
    steam_root.mkdir()
    for path in ('appcache', 'config', 'steamapps'):
        (steam_root / path).mkdir()

    # Construct the binary monstrosity that is appinfo.vdf
    appinfo_header = bytes(
        # Version magic number
        [0x29, 0x44, 0x56, 0x07]
        # Universe
    ) + pack('<I', 1)

    appinfo_vdf = pack(
        '<BiB',
        # Type
        0,
        # Index
        0,
        # End
        0x08
    )

    sha_hash = b'\x00' * 20

    appinfo_app = pack(
        '<IIIIQ20sI20s',
        # App ID
        0,
        # VDF size in bytes
        len(appinfo_vdf),
        # Info state
        0,
        # Last updated
        0,
        # Access token
        0,
        # SHA hash
        sha_hash,
        # Change number
        0,
        # VDF SHA hash
        sha_hash
    )

    # Add 8 for the length of this field.
    appinfo_key_table_offset = pack(
        '<Q', len(appinfo_header) + 8 + len(appinfo_app) + len(appinfo_vdf)
    )

    appinfo_keys = ['appinfo']
    appinfo_key_table = pack(
        # Need to add one byte for the null terminator.
        f'<{''.join([f'{len(key) + 1}s' for key in appinfo_keys])}',
        *[bytes(key, 'UTF-8') for key in appinfo_keys]
    )

    with open(steam_root / 'appcache' / 'appinfo.vdf', 'wb') as f:
        f.write(appinfo_header)
        f.write(appinfo_key_table_offset)
        f.write(appinfo_app)
        f.write(appinfo_vdf)
        f.write(pack('<I', len(appinfo_keys)))
        f.write(appinfo_key_table)

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
            library_folders['libraryfolders']['0']['apps'][
                app_id] = install_path

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
            copytree(prefix_temporary_directory, app_compat_root / 'pfx',
                     symlinks=True)

        echo('Writing library...')
        with open(apps_root / 'libraryfolders.vdf', 'w') as f:
            f.write(vdf.dumps(library_folders))

        echo(f'Finished building `{steam_root}`.')


if __name__ == '__main__':
    main()
