#!/Library/ManagedFrameworks/Python/Python3.framework/Versions/Current/bin/python3

import os
import subprocess
import sys
import random
import string
import glob
import shutil


def setup():
    if not os.path.exists('/Library/ManagedFrameworks/Python/Python3.framework/Versions/Current/bin/python3'):
        print('Python not installed')
        sys.exit(-1)
    if not len(sys.argv[4]) > 0:
        print('No package URL provided')
        sys.exit(-1)
    else:
        # Generating a random folder, just in case this script is run in parallel
        random_folder = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        temp_dir = '/tmp/' + random_folder
        os.mkdir(temp_dir)
        os.chdir(temp_dir)

        return temp_dir


def clean_up(dir):
    # This is the equivalent of rm -rf
    shutil.rmtree(dir)


def shell_out(args):
    output = None
    try:
        output = subprocess.run(args, check=True, capture_output=True, text=True)
        print(output.stdout)
    except subprocess.CalledProcessError as cpe:
        print(cpe)
        sys.exit(-1)

    return output


def curl(url, manual=False):

    result = None
    manual_name = sys.argv[5]

    if manual:
        curl_cmd = ['curl', '-o', manual_name, url, '-L']
        result = shell_out(curl_cmd)
    else:
        curl_cmd = ['curl', url, '-OL']
        result = shell_out(curl_cmd)

    return result


def find_installer(path):
    # There should only be one thing here, as curl is only downloading one file
    return os.listdir(path)[0]


def check_dmg_installer_type(tmp_dir_path):

    # We have to check this because some dmgs have pkg installers in them
    # Yes it's dumb, thanks Jabra for being the way you are

    # Getting installer path via glob because the wildcard won't be interpreted correctly without passing shell=true to subprocess, which is a security risk
    potential_installers = glob.glob(tmp_dir_path + '/mount/*')

    installer_path = None

    for file in potential_installers:
        if file.endswith('.pkg'):
            installer_path = file
        if file.endswith('.app'):
            installer_path = file

    return installer_path


def copy_app(app_path):

    # Using shell_out w/cp here instead of shutil.move because shutil can't preserve permissions/ACLS like cp can
    app_folder = os.path.expanduser('~/Applications')
    cp_command = ['cp', '-a', app_path, app_folder]
    cp_result = shell_out(cp_command)

    return cp_result


def pkg_install(pkg_path):
    installer_cmd = ['installer', '-pkg', pkg_path, '-target', '/']

    # This fails when run locally as installer needs root permissions
    installer_result = shell_out(installer_cmd)

    return installer_result


def install(tmp_dir_path, package):

    if package.endswith('.dmg'):
        hdi_attach_cmd = ['hdiutil', 'attach', package, '-nobrowse', '-noverify', '-mountpoint', tmp_dir_path + '/mount']
        hdi_attach_result = shell_out(hdi_attach_cmd)

        if hdi_attach_result.returncode == 0:
            installer = check_dmg_installer_type(tmp_dir_path)

            if installer.endswith('.app'):
                copy_app(installer)
                hdi_detach_cmd = ['hdiutil', 'detach', tmp_dir_path + '/mount']
                shell_out(hdi_detach_cmd)
                clean_up(tmp_dir_path)

            elif installer.endswith('.pkg'):
                pkg_install(installer)
                hdi_detach_cmd = ['hdiutil', 'detach', tmp_dir_path + '/mount']
                shell_out(hdi_detach_cmd)
                clean_up(tmp_dir_path)

    elif package.endswith('.pkg'):
        installer_result = pkg_install(package)
        clean_up(tmp_dir_path)

    elif package.endswith('.tar.xz') or package.endswith('.zip'):
        user_app_folder = os.path.expanduser('~/Applications')
        unzip_command = ['unzip', tmp_dir_path + '/' + package, '-d', user_app_folder]
        shell_out(unzip_command)
        clean_up(tmp_dir_path)
    else:
        print('Unsupported package type')
        sys.exit(-3)


if __name__ == "__main__":

    # sys.argv[4] is the first argument provided by JAMF
    download_url = sys.argv[4]
    tmp_dir = setup()

    # If argv[5] is provided, use that as the name for the installer w/curl
    if len(sys.argv[5]) > 0:
        curl_result = curl(download_url, manual=True)
    else:
        curl_result = curl(download_url)

    if curl_result.returncode == 0:
        package = find_installer(tmp_dir)
        install(tmp_dir, package)
    else:
        print('curl is failing')
        sys.exit(-2)
