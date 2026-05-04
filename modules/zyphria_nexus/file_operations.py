# modules/zyphria_nexus/file_operations.py
import os
import shutil
import stat
import datetime
import platform
import subprocess
import getpass
import logging

fo_logger = logging.getLogger(__name__)


def get_current_username():
    """Returns the current user's login name."""
    try:
        return getpass.getuser()
    except Exception:
        fo_logger.warning("getpass.getuser() failed. Falling back to environment variable.")
        return os.environ.get('USERNAME', 'UNKNOWN_USER')


def get_save_files_in_directory(directory):
    """
    Scans the given directory for .sav and .dat files.
    Returns a list of dictionaries, each containing filename, full path,
    and its read-only status (determined by ACL deny write).
    """
    save_files = []
    if not directory or not os.path.isdir(directory):
        fo_logger.warning(f"Invalid or non-existent directory provided: {directory}")
        return []

    for filename in os.listdir(directory):
        if filename.lower().endswith(('.sav', '.dat')):
            file_path = os.path.join(directory, filename)
            if os.path.isfile(file_path):
                is_readonly = is_acl_write_denied(file_path)
                save_files.append({
                    'filename': filename,
                    'full_path': file_path,
                    'is_readonly': is_readonly
                })
    fo_logger.debug(f"Found {len(save_files)} save files in '{directory}'.")
    return save_files


def set_read_only_status(file_path, make_readonly: bool):
    """
    Adds or removes explicit write deny ACLs for the current user,
    Administrators, and SYSTEM.
    This function requires the application to be run as Administrator on Windows.
    Will raise NotImplementedError if not on Windows.
    """
    if platform.system() != "Windows":
        raise NotImplementedError("ACL write deny is only supported on Windows.")
    
    set_acl_write_deny(file_path, make_readonly)


def set_acl_write_deny(filepath, deny_write: bool):
    """
    Adds or removes explicit write deny ACLs for the current user, Administrators, and SYSTEM.
    This function requires the application to be run as Administrator.
    """
    if platform.system() != "Windows":
        raise NotImplementedError("ACL write deny is only supported on Windows.")
    
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    current_user = get_current_username()
    computer_name = os.environ.get('COMPUTERNAME', '.').upper()
    targets = [
        f"{computer_name}\\{current_user.upper()}",
        "BUILTIN\\ADMINISTRATORS",
        "NT AUTHORITY\\SYSTEM"
    ]
    
    try:
        if deny_write:
            deny_args = [f"{target}:W" for target in targets]
            full_command = ["icacls", filepath, "/deny"] + deny_args
            
            fo_logger.debug(f"Executing DENY command: {' '.join(full_command)}")
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            fo_logger.debug(f"DENY stdout: {result.stdout.strip()}")
            fo_logger.debug(f"DENY stderr: {result.stderr.strip()}")

            if result.stderr and ("Access is denied" in result.stderr or "Access Denied" in result.stderr):
                raise PermissionError(f"Operation failed: Access Denied. Run as Administrator.")
            fo_logger.info(f"Successfully denied write ACL for '{filepath}' for targets: {', '.join(targets)}")

        else:
            for target in targets:
                remove_deny_command = ["icacls", filepath, "/remove:d", target]
                fo_logger.debug(f"Executing REMOVE DENY command for {target}: {' '.join(remove_deny_command)}")
                result_remove = subprocess.run(
                    remove_deny_command,
                    capture_output=True,
                    text=True,
                    check=False,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                if result_remove.returncode != 0 and result_remove.stderr and ("Access is denied" in result_remove.stderr or "Access Denied" in result_remove.stderr):
                    raise PermissionError(f"Operation failed to remove deny for {target}: Access Denied. Run as Administrator.")
                fo_logger.debug(f"REMOVE DENY stdout for {target}: {result_remove.stdout.strip()}")
                fo_logger.debug(f"REMOVE DENY stderr for {target}: {result_remove.stderr.strip()}")

                grant_command = ["icacls", filepath, "/grant", f"{target}:W"]
                
                fo_logger.debug(f"Executing GRANT command for {target}: {' '.join(grant_command)}")
                result_grant = subprocess.run(
                    grant_command,
                    capture_output=True,
                    text=True,
                    check=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                fo_logger.debug(f"GRANT stdout for {target}: {result_grant.stdout.strip()}")
                fo_logger.debug(f"GRANT stderr for {target}: {result_grant.stderr.strip()}")

            fo_logger.info(f"Successfully removed deny and ensured write ACL for '{filepath}' for targets: {', '.join(targets)}")

    except subprocess.CalledProcessError as e:
        fo_logger.error(f"ACL operation failed for '{filepath}' with CalledProcessError. Return Code: {e.returncode}. Stderr: {e.stderr.strip()}")
        if "Access is denied" in e.stderr or "Access Denied" in e.stderr:
            raise PermissionError(f"ACL operation failed for '{filepath}': Access Denied. "
                                  f"Ensure the application is run as Administrator. Details: {e.stderr.strip()}") from e
        raise Exception(f"ACL operation failed for '{filepath}': {e.stderr.strip()}") from e
    except FileNotFoundError:
        fo_logger.critical("icacls.exe not found. Is your system PATH configured correctly?")
        raise Exception("icacls.exe not found. Is your system PATH configured correctly?")
    except Exception as e:
        fo_logger.error(f"An unexpected error occurred during ACL operation for '{filepath}': {e}")
        raise Exception(f"An unexpected error occurred during ACL operation for '{filepath}': {e}")

def is_acl_write_denied(filepath) -> bool:
    """
    Checks if an explicit write deny ACL is set for the current user, Administrators, or SYSTEM.
    Returns True if *any* of the target users/groups have an explicit DENY (W) permission.
    """
    if platform.system() != "Windows":
        return False

    if not os.path.exists(filepath):
        return False

    current_user = get_current_username()
    computer_name = os.environ.get('COMPUTERNAME', '').upper()
    expected_principals_upper = [
        "NT AUTHORITY\\SYSTEM",
        "BUILTIN\\ADMINISTRATORS",
        f"{computer_name}\\{current_user.upper()}",
        current_user.upper()
    ]
    expected_principals_upper = [p for p in expected_principals_upper if p]
    
    fo_logger.debug(f"--- is_acl_write_denied Log for '{filepath}' ---")
    fo_logger.debug(f"Expected principals for checking: {expected_principals_upper}")

    try:
        result = subprocess.run(
            ["icacls", filepath],
            capture_output=True,
            text=True,
            check=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        fo_logger.debug(f"ICACLS check stdout: {result.stdout.strip()}")
        fo_logger.debug(f"ICACLS check stderr: {result.stderr.strip()}")
        
        output_lines = result.stdout.upper().splitlines()
        
        for line in output_lines:
            if "(DENY)" in line and "(W)" in line:
                for principal in expected_principals_upper:
                    if principal and principal in line:
                        fo_logger.debug(f"Found explicit Deny Write for {principal} in line: {line}")
                        return True
        fo_logger.debug(f"No explicit Deny Write found for target principals.")
        return False
        
    except subprocess.CalledProcessError as e:
        if "ACCESS IS DENIED" in e.stderr.upper():
            fo_logger.warning(f"ACL check for '{filepath}' failed (Access Denied). Run as Administrator.")
        else:
            fo_logger.warning(f"ACL check for '{filepath}' failed with unexpected error. Command: {e.cmd}, Stderr: {e.stderr.strip()}")
        return False
    except Exception as e:
        fo_logger.error(f"Error checking ACL status for '{filepath}': {e}")
        return False
    finally:
        fo_logger.debug(f"--- End is_acl_write_denied Log for '{filepath}' ---")


def backup_save_file(source_file_path: str, backup_root_folder: str, game_profile_name: str) -> str:
    """
    Backs up a save file to a game-specific subfolder within the backup root.
    It overwrites any existing backup for that specific save file.
    Returns the path to the created backup file.
    """
    if not os.path.exists(source_file_path):
        raise FileNotFoundError(f"Source save file not found: {source_file_path}")
    if not os.path.isdir(backup_root_folder):
        raise ValueError(f"Backup destination is not a valid directory: {backup_root_folder}")

    source_filename = os.path.basename(source_file_path)

    game_backup_folder = os.path.join(backup_root_folder, game_profile_name)
    os.makedirs(game_backup_folder, exist_ok=True)

    destination_file_path = os.path.join(game_backup_folder, source_filename)

    shutil.copy2(source_file_path, destination_file_path)
    fo_logger.info(f"Backed up '{source_filename}' to '{destination_file_path}' (overwriting previous).")
    return destination_file_path


def restore_save_file(backup_source_path: str, game_saves_folder: str, original_filename: str):
    """
    Restores a backup save file to the original game saves location.
    The backup_source_path must point directly to the specific backup file.
    """
    if not os.path.exists(backup_source_path):
        raise FileNotFoundError(f"Backup file to restore not found: {backup_source_path}")
    if not os.path.isdir(game_saves_folder):
        raise ValueError(f"Game saves folder is not a valid directory: {game_saves_folder}")

    destination_file_path = os.path.join(game_saves_folder, original_filename)

    shutil.copy2(backup_source_path, destination_file_path)
    fo_logger.info(f"Restored '{backup_source_path}' to '{destination_file_path}'.")
