"""Provide methods performing validation on configuration properties."""
from types import FunctionType
from os import path

from . import errors
from .errors import ErrorWrapper


def _create_validator(is_valid_lambda: FunctionType, error: ErrorWrapper) -> FunctionType:
    """
    Return a validator for the specified arguments.

     * is_valid_lambda: A function accepting a value. 
       It returns a bool telling whether it is considered as valid.
     * error The error instance the validator should return

    The function returns a function which accepts a value, applies is_valid_lambda on it
    and returns the supplied error if it is not considered as valid, otherwise None.
    """
    return lambda value: error if not is_valid_lambda(value) else None


def _chain_validators(*args) -> FunctionType:
    """
    Chain multiple validators into a single one.

    The first validation error occuring is returned, if none do occur, None will be returned.
    """
    def chain_validator(value):
        for validator in args:
            error = validator(value)

            if error is not None:
                return error

    return chain_validator


def _create_non_empty_validator(error: ErrorWrapper) -> FunctionType:
    """
    Return a validator checking whether the supplied (str) value is neither None nor empty.

    If not, the supplied error will be returned.
    """
    return _create_validator(lambda value: value is not None and value.strip() != "", error)


def _create_numeric_validator(error: ErrorWrapper) -> FunctionType:
    """
    Return a validator checking whether a supplied value is numeric.

    If not, the supplied error will be returned.
    The supplied value will be stripped before validation. It must not be None.
    """
    return _create_validator(lambda value: value.strip().isnumeric(), error)


def _create_single_character_validator(error: ErrorWrapper) -> FunctionType:
    """
    Return a validator checking whether a supplied value is a single character.

    If not, the supplied error will be returned.
    The supplied value will be stripped before validation. It must not be None.
    """
    return _create_validator(lambda value: len(value.strip()) == 1, error)


def validate_base_url(base_url: str) -> ErrorWrapper:
    """Validate that the supplied string is neither None nor blank and does end with a slash '/'."""
    return _chain_validators(_create_non_empty_validator(errors.CONFIG_BASE_URL_EMPTY),
                             _create_validator(lambda value: value.strip().endswith("/"), errors.CONFIG_BASE_URL_NOT_ENDING_WITH_SLASH))(base_url)


def validate_template_id(template_id: str) -> ErrorWrapper:
    """
    Validate that the supplied string is neither None nor blank and numeric.

    The supplied value will be stripped before validation.
    """
    return _chain_validators(_create_non_empty_validator(errors.CONFIG_TEMPLATE_ID_EMPTY),
                             _create_numeric_validator(errors.CONFIG_TEMPLATE_ID_NOT_NUMERIC))(template_id)


def _create_is_not_extended_alphanumeric_validator(error: ErrorWrapper) -> FunctionType:
    """
    Return a validator checking whether a supplied value is alphanumeric or a dot '.', underscore '_' or hyphen '-'.

    If not, the supplied error will be returned.
    The supplied value will be stripped before validation. It must not be None.
    """
    def validation_function(value):
        stripped_value = value.strip()
        return not (stripped_value.isalnum() or stripped_value == '.' or stripped_value == '_' or stripped_value == '-')
    return _create_validator(validation_function, error)


def validate_placeholder_character(placeholder_character: str, escape_character: str) -> ErrorWrapper:
    """
    Validate that the supplied string is a valid placeholder character.

    This entails:
        * It is neither None nor blank
        * It is a single character
        * It is alphanumeric, a dot '.', underscore '_' or hyphen '-'
        * It is different to the provided escape character

    The supplied value will be stripped before validation.
    """
    return _chain_validators(
        _create_non_empty_validator(errors.CONFIG_PLACEHOLDER_EMPTY),
        _create_single_character_validator(
            errors.CONFIG_PLACEHOLDER_NO_SINGLE_CHAR),
        _create_is_not_extended_alphanumeric_validator(
            errors.CONFIG_PLACEHOLDER_INVALID_CHAR),
        _create_validator(lambda value: value is not escape_character.strip(), errors.CONFIG_ESCAPE_CHAR_EQUALS_PLACEHOLDER))(placeholder_character)


def validate_escape_character(escape_character: str, placeholder_character: str) -> ErrorWrapper:
    """
    Validate that the supplied string is a valid escape character.

    This entails:
    * It is neither None nor blank
    * It is a single character
    * It is alphanumeric, a dot '.', underscore '_' or hyphen '-'
    * It is different to the provided placeholder character

    The supplied value will be stripped before validation.
    """
    return _chain_validators(
        _create_non_empty_validator(errors.CONFIG_ESCAPE_EMPTY),
        _create_single_character_validator(
            errors.CONFIG_ESCAPE_NO_SINGLE_CHAR),
        _create_is_not_extended_alphanumeric_validator(
            errors.CONFIG_ESCAPE_INVALID_CHAR),
        _create_validator(lambda value: placeholder_character is not value.strip(), errors.CONFIG_ESCAPE_CHAR_EQUALS_PLACEHOLDER))(escape_character)


def validate_upload_space(upload_space: str) -> ErrorWrapper:
    """Validate that the supplied string is neither None nor blank."""
    return _create_non_empty_validator(errors.CONFIG_UPLOAD_SPACE_EMPTY)(upload_space)


def validate_parent_page_id(parent_page_id: str, validate_empty: bool = True) -> ErrorWrapper:
    """
    Validate that the supplied value is a valid parent page ID.

    This means that the value is not None nor empty, and numeric.
    If validate_empty is False, None or an empty string are seen as valid.

    The supplied value will be stripped before validation.
    """
    empty_validation_error = _create_non_empty_validator(
        errors.CONFIG_PARENT_PAGE_ID_EMPTY)(parent_page_id)

    if empty_validation_error is not None:
        return empty_validation_error if validate_empty else None
    else:
        return _create_numeric_validator(errors.CONFIG_PARENT_PAGE_ID_NOT_NUMERIC)(parent_page_id)


def validate_article_data_csv(article_data_csv: str) -> ErrorWrapper:
    """
    Validate that the supplied value is a valid article data CSV file path.

    This means:
        * It is neither None nor blank
        * It links to an already existing file

    The supplied value will be stripped before validation.
    """
    return _chain_validators(
        _create_non_empty_validator(
            errors.CONFIG_DATA_CSV_PATH_EMPTY),
        _create_validator(lambda value: path.isfile(value.strip()), errors.CONFIG_DATA_CSV_DOES_NOT_EXIST))(article_data_csv)


def validate_csv_delimiter(csv_delimiter: str) -> ErrorWrapper:
    """
    Validate that the supplied value is a valid CSV delimiter.

    This means:
        * It is neither None nor blank
        * It is a single character

    The supplied value will be stripped before validation.
    """
    return _chain_validators(
        _create_non_empty_validator(
            errors.CONFIG_CSV_DELIMITER_EMPTY),
        _create_single_character_validator(errors.CONFIG_CSV_DELIMITER_NO_SINGLE_CHAR))(csv_delimiter)


def validate_csv_id_column_header(csv_id_column_header: str) -> ErrorWrapper:
    """Validate that the supplied string is neither None nor blank."""
    return _create_non_empty_validator(errors.CONFIG_CSV_ID_COLUMN_HEADER_EMPTY)(csv_id_column_header)


def validate_username(username: str) -> ErrorWrapper:
    """Validate that the supplied string is neither None nor blank."""
    return _create_non_empty_validator(errors.CONFIG_USERNAME_EMPTY)(username)


def validate_token(token: str) -> ErrorWrapper:
    """Validate that the supplied string is neither None nor blank."""
    return _create_non_empty_validator(errors.CONFIG_TOKEN_EMPTY)(token)
