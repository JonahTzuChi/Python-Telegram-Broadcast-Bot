def is_valid_folderName(folder_name: str) -> bool:
    if len(folder_name) == 0 or len(folder_name) > 32:
        return False

    invalid_characters = '<>:"/\\|?*.'
    invalid_characters = list(filter(lambda char: char in invalid_characters, folder_name))
    return len(invalid_characters) == 0


def is_valid_fileName(file_name: str) -> bool:
    if len(file_name) == 0 or len(file_name) > 120:
        return False

    invalid_characters = '<>:"/\\|?*'
    invalid_characters = list(filter(lambda char: char in invalid_characters, file_name))
    return len(invalid_characters) == 0


def isURL(value_string: str) -> bool:
    return "://" in value_string


def addPhoto_validation_fn(filename, photo):
    """
    Validates the photo and filename provided by the user.

    This function checks if a filename is provided and if it meets the criteria for a valid file name.
    Additionally, it validates the presence of a photo. It returns a validation code along with a
    corresponding message. The validation codes are as follows:
    - 0: Validation passed.
    - 1: Filename is missing.
    - 2: Filename does not meet the file name criteria.
    - 3: Photo is missing.

    Parameters:
    - photo: The photo object provided by the user. This is expected to be a telegram photo object
             or similar, depending on the bot framework being used.
    - filename: The filename for the photo as a string. This is used for validating the file name and
               ensuring it's provided.

    Returns:
    - tuple: A 2-tuple containing an integer validation code and a string message indicating the
             result of the validation. The message is meant to be human-readable and suitable for
             direct presentation to the user.

    Note:
    This function assumes that the validation criteria for a file name are implemented in a
    separate function called `is_valid_fileName`. This external function should return a Boolean
    indicating whether the filename meets the necessary criteria for a file name.
    """
    if filename is None:
        return 1, "Please try again. Filename is missing."
    if not is_valid_fileName(filename):
        return 2, "Please try again. Filename is missing."
    if photo is None:
        return 3, "Please try again. Only accept photo."
    return 0, "None"


def addDocument_validation_fn(filename, document, mimetype: str) -> tuple[int, str]:
    if filename is None:
        return 1, "Please try again. Filename is missing."
    if not is_valid_fileName(filename):
        return 2, "Please try again. Filename is missing."
    if document is None:
        return 3, "Please try again. Only accept document."
    if mimetype not in [
        "application/pdf",
        "text/plain",
        "text/csv",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.ms-powerpoint"
    ]:
        return 4, "Only limited file format are accepted."
    return 0, "None"


def addVideo_validation_fn(filename, document, mimetype: str) -> tuple[int, str]:
    if filename is None:
        return 1, "Please try again. Filename is missing."
    if not is_valid_fileName(filename):
        return 2, "Please try again. Filename is invalid."
    if document is None:
        return 3, "Please try again. Only accept document."
    if mimetype not in ["video/mp4", "video/x-matroska"]:
        return 4, "Only limited file format are accepted."
    return 0, "None"


def addText_validation_fn(filename, document, mimetype: str) -> tuple[int, str]:
    if filename is None:
        return 1, "Please try again. Filename is missing."
    if not is_valid_fileName(filename):
        return 2, "Please try again. Filename is missing."
    if document is None:
        return 3, "Please try again. Only accept document."
    if mimetype not in ["text/plain"]:
        return 4, "Only txt file is acceptable."
    return 0, "None"


def is_ext_align_w_dtype(file_extension: str, dtype: str) -> bool:
    if dtype == "DOCUMENT":
        allowed_extension = ["pdf", "txt", "csv"]
    elif dtype == "VIDEO":
        allowed_extension = ["mp4", "mkv"]
    else:
        # Photo
        allowed_extension = ["jpg", "jpeg", "png"]
    return file_extension in allowed_extension
