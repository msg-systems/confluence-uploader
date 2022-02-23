"""Contains definitions of errors deliberately thrown by the application, so they can be referred elsewhere."""

import sys
from .logger import error_logger


class ErrorWrapper:
    """
    Contains additional information about runtime errors raised by the application, including a unique ID.

    The program enforces the uniqueness of the IDs. This type is not an error itself
    """

    _used_ids = set()

    def __init__(self, error_id: int, message: str):
        """
        Validate the uniqueness of the supplied ID in the constructor.

        The error message is required to be of type str and not None.
        """
        # Validate the uniqueness of the ID
        if error_id in ErrorWrapper._used_ids:
            raise ValueError("The id " + str(error_id) +
                             " is already used by an error wrapper")

        # If this line was reached, the ID is unique
        ErrorWrapper._used_ids.add(error_id)

        if not isinstance(message, str):
            raise TypeError(
                "The error message has to be a str")

        self.error_id = error_id
        self._message = message

    def get_message(self, *args):
        """
        Return the error message with the supplied arguments inserted.

        Internally, this calls .format(*args) on the message string.
        """
        return self._message.format(*args)

    def print_message(self, *args):
        """
        Log the error message with the configured error logger.

        This is the recommended way to print error wrapper messages.
        """
        error_logger.error(self.get_message(*args),
                           extra={'error_id': self.error_id})

    # Return type annotation because of https://github.com/microsoft/pylance-release/issues/1174
    # If missing, parts test code using the function may be displayed as unreachable, even if
    # sys.exit is mocked out
    def print_message_and_exit(self, *args) -> None:
        """Log the error message and exit the program with exit code 1."""
        self.print_message(*args)
        sys.exit(1)


class InvalidStateError(ValueError):
    """Raised when an invalid state is detected."""

    def __repr__(self):  # pragma: no cover
        """Return a general message for this error as a representation."""
        return "The current state is not valid"


# Do not set the IDs below automatically, as that may mess up the error documentation,
# which relies on the specific ID assignments.
# Instead set them manually, and do not change existing assignments.
# The program validates whether an assigned ID is already in use.

UNEXPECTED = ErrorWrapper(0, "An unexpected error occurred")

ARTICLE_DATA_NO_ID_COLUMN = ErrorWrapper(
    1, "The article data don't contain an ID column with header '{}'")
ARTICLE_DATA_NO_UNIQUE_ID = ErrorWrapper(
    2, "The article data already contain an entry with the ID '{}'")
ARTICLE_DATA_NO_UNIQUE_IDS = ErrorWrapper(
    3, "The article data contain {} entries with non-unique ID values")

SSL_ERROR = ErrorWrapper(4, "Accessing '{}' failed due to an SSL error")

CONFLUENCE_DOWNLOAD_FAILED = ErrorWrapper(
    5, "Downloading the template '{1}' via '{0}' failed")
CONFLUENCE_EXISTENCE_CHECK_FAILED = ErrorWrapper(
    6, "Checking for existing articles with title '{1}' via '{0}' failed")
CONFLUENCE_UPLOAD_FAILED = ErrorWrapper(
    7, "Uploading the article generated from article data entry '{1}' via '{0}' failed")
CONFLUENCE_UPDATE_FAILED = ErrorWrapper(
    8, "Updating the article '{2}' with the article generated from article data entry '{1}' via '{0}' failed")

ARTICLE_NO_UNIQUE_TITLE = ErrorWrapper(
    9, "The article generated from the article data entry '{}' has a title '{}' which already exists for another article")
ARTICLE_UNKNOWN_PLACEHOLDER = ErrorWrapper(
    10, "The article generated from the article data entry '{}' has an unknown placeholder {}")
ARTICLE_SINGLE_PLACEHOLDER_CHARACTER = ErrorWrapper(
    11, "The article generated from the article data entry '{}' has {} placeholder characters '{}' not belonging to a valid placeholder")
ARTICLE_VALIDATION_ERRORS = ErrorWrapper(
    12, "Validation errors occurred for articles generated from the template and the article data")

CONFIG_INVALID_STRUCTURE = ErrorWrapper(
    13, "The config file has an invalid structure")

CONFIG_TEMPLATE_ID_EMPTY = ErrorWrapper(
    14, "The configured template ID is empty")
CONFIG_TEMPLATE_ID_NOT_NUMERIC = ErrorWrapper(
    15, "The configured template ID '{}' is not numeric")

CONFIG_PLACEHOLDER_EMPTY = ErrorWrapper(
    16, "The configured placeholder is empty")
CONFIG_PLACEHOLDER_NO_SINGLE_CHAR = ErrorWrapper(
    17, "The configured placeholder '{}' is no single character")
CONFIG_PLACEHOLDER_INVALID_CHAR = ErrorWrapper(
    18, "The configured placeholder '{}' must not be alphanumeric, ., - or _")
CONFIG_ESCAPE_CHAR_EQUALS_PLACEHOLDER = ErrorWrapper(
    19, "The configured placeholder character is the same one as the escape character")

CONFIG_ESCAPE_EMPTY = ErrorWrapper(
    20, "The configured escape character is empty")
CONFIG_ESCAPE_NO_SINGLE_CHAR = ErrorWrapper(
    21, "The configured escape character '{}' is no single character")
CONFIG_ESCAPE_INVALID_CHAR = ErrorWrapper(
    22, "The configured escape character '{}' must not be alphanumeric, ., - or _")

CONFIG_UPLOAD_SPACE_EMPTY = ErrorWrapper(
    23, "The configured upload space is empty")

CONFIG_PARENT_PAGE_ID_EMPTY = ErrorWrapper(
    24, "The configured upload parent page ID is empty")
CONFIG_PARENT_PAGE_ID_NOT_NUMERIC = ErrorWrapper(
    25, "The configured upload parent page ID '{}' is not numeric")

CONFIG_DATA_CSV_PATH_EMPTY = ErrorWrapper(
    26, "The configured data CSV path is empty")
CONFIG_DATA_CSV_DOES_NOT_EXIST = ErrorWrapper(
    27, "The configured data CSV file '{}' does not exist")

CONFIG_CSV_DELIMITER_EMPTY = ErrorWrapper(
    28, "The configured CSV delimiter is empty")
CONFIG_CSV_DELIMITER_NO_SINGLE_CHAR = ErrorWrapper(
    29, "The configured CSV delimiter '{}' is no single character")

CONFIG_CSV_ID_COLUMN_HEADER_EMPTY = ErrorWrapper(
    30, "The configured CSV ID column header is empty")

CONFIG_USERNAME_EMPTY = ErrorWrapper(32, "The configured username is empty")
CONFIG_TOKEN_EMPTY = ErrorWrapper(33, "The configured token is empty")

CONFIG_BASE_URL_EMPTY = ErrorWrapper(
    34, "The configured base URL is empty")

CONFIG_BASE_URL_NOT_ENDING_WITH_SLASH = ErrorWrapper(
    35, "The configured base URL does not end with a slash '/'")

CONFLUENCE_TEMPLATE_PROCESSING_FAILED = ErrorWrapper(
    36, "Processing the template '{0}' downloaded from '{1}' failed")
