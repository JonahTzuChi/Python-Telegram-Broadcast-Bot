import os


def getSubFiles(path: str):
    return list(filter(lambda x: "." in x, os.listdir(path)))


def getSubDirectory(directory: str):
    return list(filter(lambda x: "." not in x, os.listdir(directory)))


def createSubDirectory(dirPath: str):
    if os.path.exists(dirPath):
        print(f"Exception: {dirPath} already exists!")
        return False
    os.mkdir(dirPath)
    # hexidecimal: 0-9, a-f
    for i in range(0, 10):
        os.mkdir(f"{dirPath}/{i}")
    for c in ["a", "b", "c", "d", "e", "f"]:
        os.mkdir(f"{dirPath}/{c}")
    return True


def find_file(filename: str, home_directory: str, deep_search: bool = False) -> tuple:
    """
    Searches for a file by name within a specified directory, optionally performing a deep search.
    ------------------------------------------------------------------------
    Attempts to locate a file named `filename` within `home_directory`. If `deep_search` is enabled, the
    function recursively searches through all subdirectories. It returns (True, file_path) if the file is
    found. If the file is not found or an error occurs, it returns (False, error_message).

    Parameters:
    ------------------------------------------------------------------------
    - filename (str): The name of the file to search for.
    - home_directory (str): The directory within which to start the search.
    - deep_search (bool): If True, includes all subdirectories in the search. If False, searches only
                          the immediate contents of `home_directory`.

    Returns:
    ------------------------------------------------------------------------
    - tuple[bool, str]: A tuple where the first element indicates whether the file was found, and the
                        second element is the path to the file (if found) or an error message.

    Raises:
    ------------------------------------------------------------------------
    - Prints and returns error messages for encountered exceptions but does not raise them to the caller.

    Notes:
    ------------------------------------------------------------------------
    If more than one file with the same name exists, only the path to the first file encountered is returned.
    """
    try:
        child_items = os.listdir(home_directory)
        for item in child_items:
            child_path = os.path.join(home_directory, item)
            if filename == item:
                return True, child_path
            if deep_search:
                if os.path.isdir(child_path):
                    islocal, filepath = find_file(filename, child_path, True)
                    if islocal:
                        return True, filepath
        return False, "FileNotFoundError"
    except PermissionError as permission_err:
        print(f"[isLocalFile]:\tFileNotFoundError:{str(permission_err)}", flush=True)
        return False, str(permission_err)
    except FileNotFoundError as file_not_found_err:
        print(
            f"[isLocalFile]:\tFileNotFoundError:{str(file_not_found_err)}", flush=True
        )
        return False, str(file_not_found_err)
    except Exception as e:
        print(f"[isLocalFile]:\tException:{str(e)}", flush=True)
        return False, str(e)


def isLocalFile(
    filename: str, home_directory: str = "/online", deepSearch: bool = False
) -> bool:
    islocal, _ = find_file(filename, home_directory, deepSearch)
    return islocal
