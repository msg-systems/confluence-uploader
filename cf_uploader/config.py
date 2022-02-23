"""Provide components for managing the configuration file of the application."""
from configupdater import ConfigUpdater
from . import validation
from .errors import InvalidStateError

CONFIG_FILENAME = 'config/config.ini'
UPLOADER_CONFIG_FILENAME = 'config/uploader_config.ini'

CONFLUENCE_CATEGORY = "confluence"
BEHAVIOR_CATEGORY = "behavior"
DATA_CATEGORY = "data"


class Config:
    """
    This class encapsulates the configuration properties of the program.

    The properties can be accessed via their getters, and set via the defined setters.
    Note that the setters only accept values seen as valid
    (regarding the specified validation functions for the configuration properties).
    The getters may return invalid values.
    """

    def __init__(self):
        """Initialize the configuration instance with default values."""
        self._config = ConfigUpdater()
        self._uploader_config = ConfigUpdater()

        self._loaded = False

        self._api_interaction_delay_seconds = 0
        self._dump_template = False
        self._dump_generated_articles = False
        self._user_gui = True

        self._base_url = ""
        self._template_id = ""
        self._placeholder_character = ""
        self._escape_character = ""
        self._upload_space = ""
        self._upload_parent_page = None
        self._overwrite_existing_articles = False
        self._username = ""
        self._token = ""
        self._article_data_csv = ""
        self._csv_delimiter = ";"
        self._csv_id_header = "id"

        self._errored_articles_csv = "errored_articles.csv"

    def is_loaded(self) -> bool:
        """Return whether the configuration file was loaded."""
        return self._loaded

    def _require_loaded(self):
        if not self._loaded:
            raise InvalidStateError(
                "The configuration properties were not loaded yet")

    def _get_property(self, config, category, property_name):
        return config[category][property_name].value.strip()

    def _get_bool(self, config, category, property_name):
        """
        Parse a bool from a string, by checking whether the string is 'true' (case-insensitive).

        Otherwise the string is interpreted as false
        (this includes the case that the string is None).

        The built-in method bool(...) in python would always return true for a non-empty string.
        """
        string = self._get_property(config, category, property_name)

        if string is not None:
            return string.lower() == "true"

        return False  # pragma: no cover (as this condition cannot happen due to the config property parsing, but it is here for robustness)

    def _get_float(self, config, category, property_name):
        return float(self._get_property(config, category, property_name))

    def load(self):
        """
        Load the configuration files.

        This overwrites the values currently set at this configuration instance.
        """
        self._config.read(CONFIG_FILENAME)

        self._api_interaction_delay_seconds = self._get_float(
            self._config, CONFLUENCE_CATEGORY, "api_interaction_delay_seconds")
        self._dump_template = self._get_bool(
            self._config, CONFLUENCE_CATEGORY, "dump_template")
        self._dump_generated_articles = self._get_bool(
            self._config, CONFLUENCE_CATEGORY, "dump_generated_articles")
        self._user_gui = self._get_bool(
            self._config, CONFLUENCE_CATEGORY, "user_gui")

        # Negative values are mapped to zero
        if self._api_interaction_delay_seconds < 0:
            self._api_interaction_delay_seconds = 0

        self._uploader_config.read(UPLOADER_CONFIG_FILENAME)

        self._base_url = self._get_property(
            self._uploader_config, CONFLUENCE_CATEGORY, "base_url")
        self._template_id = self._get_property(
            self._uploader_config, CONFLUENCE_CATEGORY, "template_id")
        self._placeholder_character = self._get_property(
            self._uploader_config, CONFLUENCE_CATEGORY, "placeholder_character")
        self._escape_character = self._get_property(
            self._uploader_config, CONFLUENCE_CATEGORY, "escape_character")

        self._upload_space = self._get_property(
            self._uploader_config, CONFLUENCE_CATEGORY, "upload_space")
        self._upload_parent_page = self._get_property(
            self._uploader_config, CONFLUENCE_CATEGORY, "upload_parent_page_id")

        # If let empty, set to None, as that means internally that no parent page is used
        if self._upload_parent_page.strip() == "":
            self._upload_parent_page = None

        self._overwrite_existing_articles = self._get_bool(
            self._uploader_config, BEHAVIOR_CATEGORY, "overwrite_existing_articles")

        # Currently not configurable, but store it here in case it will be
        self._errored_articles_csv = "errored_articles.csv"

        # Also not configurable via the file, but this object holds the values for the properties
        self._username = ""
        self._token = ""

        self._article_data_csv = self._get_property(
            self._uploader_config, DATA_CATEGORY, "data_csv")
        self._csv_delimiter = self._get_property(
            self._uploader_config, DATA_CATEGORY, "csv_delimiter")
        self._csv_id_header = self._get_property(
            self._uploader_config, DATA_CATEGORY, "id_column_header")

        self._loaded = True

    def validate_all(self):
        """
        Validate all validatable properties in this configuration instance.

        If no validation errors do occur, None is returned.
        Otherwise return the following upon the first validation error:
        A tuple of two elements, with the first being the invalid property value
        and the second being the validation error from the errors module.

        The configuration instance is required to be loaded.
        """
        self._require_loaded()

        # Collect the value to validate and the validation function for that value in a tuple
        def collect_validation_result(validation_entry, validation_function):
            return (validation_entry, lambda: validation_function(validation_entry))

        validation_functions = []

        validation_functions.append(collect_validation_result(
            self._base_url, validation.validate_base_url))

        validation_functions.append(collect_validation_result(
            self._template_id, validation.validate_template_id))
        validation_functions.append(collect_validation_result(
            self._placeholder_character, lambda placeholder: validation.validate_placeholder_character(placeholder, self._escape_character)))
        validation_functions.append(collect_validation_result(
            self._escape_character, lambda escape: validation.validate_escape_character(escape, self._placeholder_character)))

        validation_functions.append(collect_validation_result(
            self._upload_space, validation.validate_upload_space))
        validation_functions.append(collect_validation_result(
            self._upload_parent_page, lambda validation_entry:
            validation.validate_parent_page_id(validation_entry, validate_empty=False)))

        validation_functions.append(collect_validation_result(
            self._csv_delimiter, validation.validate_csv_delimiter))
        validation_functions.append(collect_validation_result(
            self._article_data_csv, validation.validate_article_data_csv))
        validation_functions.append(collect_validation_result(
            self._csv_id_header, validation.validate_csv_id_column_header))

        validation_functions.append(
            collect_validation_result(self._username, validation.validate_username))
        validation_functions.append(
            collect_validation_result(self._token, validation.validate_token))

        for validation_data in validation_functions:
            # Perform the validation
            validation_error = validation_data[1]()

            # Return the tuple as described above if a validation error occured
            if validation_error is not None:
                return validation_data[0], validation_error

    def _require_type(self, prop, property_type, accept_none=False):
        if not isinstance(prop, property_type) and (prop is not None if accept_none else True):
            raise TypeError("The type of " + str(prop) +
                            " is not " + str(property_type))

    def _require_string(self, prop, accept_none=False):
        self._require_type(prop, str, accept_none)

    def _require_bool(self, prop):
        self._require_type(prop, bool)

    def _require_valid(self, prop, validation_function):
        validation_result = validation_function(prop)

        if validation_result is not None:
            raise ValueError("The specified property value " +
                             ("None" if prop is None else str(prop)) + " is not valid", validation_result)

    def _require_loaded_valid_str(self, prop, validation_function):
        self._require_loaded()
        self._require_string(prop)
        self._require_valid(prop, validation_function)

    def get_api_interaction_delay_seconds(self) -> float:
        """
        Return the configured API interaction delay as a not-None float.

        Do not call this method before the configuration gets loaded.
        """
        self._require_loaded()

        return self._api_interaction_delay_seconds

    def get_dump_template(self) -> bool:
        """
        Return a not-None bool about whether the downloaded template should be dumped.

        Do not call this method before the configuration gets loaded.
        """
        self._require_loaded()

        return self._dump_template

    def get_dump_generated_articles(self) -> bool:
        """
        Return a not-None bool about whether the generated articles should be dumped.

        Do not call this method before the configuration gets loaded.
        """
        self._require_loaded()

        return self._dump_generated_articles

    def get_user_gui(self) -> bool:
        """
        Return a not-None bool about whether the GUI should be used.

        Do not call this method before the configuration gets loaded.
        """
        self._require_loaded()

        return self._user_gui

    def get_base_url(self) -> str:
        """
        Return a not-None str containing the Confluence base URL.

        Do not call this method before the configuration gets loaded.
        """
        self._require_loaded()

        return self._base_url

    def set_base_url(self, base_url: str):
        """
        Set the Confluence base URL to the specified value.

        The base URL has to be a str, and valid according to its validation function.
        It is not required to be stripped, as that operation is performed before assigning it.

        Do not call this method before the configuration gets loaded.
        """
        self._require_loaded_valid_str(base_url, validation.validate_base_url)

        self._base_url = base_url.strip()

    def get_template_id(self) -> str:
        """
        Return a not-None str containing the template ID.

        Do not call this method before the configuration gets loaded.
        """
        self._require_loaded()

        return self._template_id

    def set_template_id(self, template_id: str):
        """
        Set the template ID to the specified value.

        The ID has to be a str, and valid according to its validation function.
        It is not required to be stripped, as that operation is performed before assigning it.

        Do not call this method before the configuration gets loaded.
        """
        self._require_loaded_valid_str(
            template_id, validation.validate_template_id)

        self._template_id = template_id.strip()

    def get_placeholder_character(self) -> str:
        """
        Return a not-None str containing the placeholder character.

        Do not call this method before the configuration gets loaded.
        """
        self._require_loaded()

        return self._placeholder_character

    def set_placeholder_character(self, placeholder_character: str):
        """
        Set the placeholder character to the specified value.

        The character has to be a str, and valid according to its validation function.
        It is not required to be stripped, as that operation is performed before assigning it.

        Do not call this method before the configuration gets loaded.
        """
        self._require_loaded_valid_str(placeholder_character,
                                       lambda placeholder: validation.validate_placeholder_character(placeholder, self._escape_character))

        self._placeholder_character = placeholder_character.strip()

    def get_escape_character(self) -> str:
        """
        Return a not-None str containing the escape character.

        Do not call this method before the configuration gets loaded.
        """
        self._require_loaded()

        return self._escape_character

    def set_escape_character(self, escape_character: str):
        """
        Set the escape character to the specified value.

        The character has to be a str, and valid according to its validation function.
        It is not required to be stripped, as that operation is performed before assigning it.

        Do not call this method before the configuration gets loaded.
        """
        self._require_loaded_valid_str(escape_character, lambda escape:
                                       validation.validate_escape_character(escape, self._placeholder_character))

        self._escape_character = escape_character.strip()

    def get_upload_space(self) -> str:
        """
        Return a not-None str containing the upload space.

        Do not call this method before the configuration gets loaded.
        """
        self._require_loaded()

        return self._upload_space

    def set_upload_space(self, upload_space: str):
        """
        Set the upload space to the specified value.

        The space has to be a str, and valid according to its validation function.
        It is not required to be stripped, as that operation is performed before assigning it.

        Do not call this method before the configuration gets loaded.
        """
        self._require_loaded_valid_str(upload_space,
                                       validation.validate_upload_space)

        self._upload_space = upload_space.strip()

    def get_upload_parent_page(self) -> str:
        """
        Return a str containing the upload space. It can be None.

        Do not call this method before the configuration gets loaded.
        """
        self._require_loaded()

        return self._upload_parent_page

    def set_upload_parent_page(self, upload_parent_page: str):
        """
        Set the ID of the upload parent page to the specified value.

        The ID has to be a str, and valid according to its validation function.
        Especially it can be None.
        It is not required to be stripped, as that operation is performed before assigning it.

        Do not call this method before the configuration gets loaded.
        """
        self._require_loaded()
        self._require_string(upload_parent_page, True)

        if upload_parent_page is not None:
            self._require_valid(upload_parent_page,
                                validation.validate_parent_page_id)

            self._upload_parent_page = upload_parent_page.strip()
        else:
            self._upload_parent_page = None

    def get_overwrite_existing_articles(self) -> bool:
        """
        Return a not-None bool about whether existing articles should be overwritten.

        Do not call this method before the configuration gets loaded.
        """
        self._require_loaded()

        return self._overwrite_existing_articles

    def set_overwrite_existing_articles(self, overwrite_existing_articles: bool):
        """
        Set whether existing Confluence articles should be ovverwritten to the specified value.

        The property has to be a bool, and must not be None.

        Do not call this method before the configuration gets loaded.
        """
        self._require_loaded()
        self._require_bool(overwrite_existing_articles)

        self._overwrite_existing_articles = overwrite_existing_articles

    def get_errored_articles_csv(self) -> str:
        """
        Return a not-None str containing the filename of the errored articles CSV file.

        Do not call this method before the configuration gets loaded.
        """
        self._require_loaded()

        return self._errored_articles_csv

    def get_username(self) -> str:
        """
        Return a not-None str containing the Confluence username.

        Do not call this method before the configuration gets loaded.
        """
        self._require_loaded()

        return self._username

    def set_username(self, username: str):
        """
        Set the Confluence username to the specified value.

        The username has to be a str, and valid according to its validation function.
        Contrary to other properties, it will not be stripped.

        Do not call this method before the configuration gets loaded.
        """
        self._require_loaded_valid_str(username, validation.validate_username)

        self._username = username

    def get_token(self) -> str:
        """
        Return a not-None str containing the Confluence token.

        Do not call this method before the configuration gets loaded.
        """
        self._require_loaded()

        return self._token

    def set_token(self, token: str):
        """
        Set the Confluence token to the specified value.

        The token has to be a str, and valid according to its validation function.
        Contrary to other properties, it will not be stripped.

        Do not call this method before the configuration gets loaded.
        """
        self._require_loaded_valid_str(token, validation.validate_token)

        self._token = token

    def get_article_data_csv(self) -> str:
        """
        Return a not-None str containing the filename of the article data CSV file.

        Do not call this method before the configuration gets loaded.
        """
        self._require_loaded()

        return self._article_data_csv

    def set_article_data_csv(self, article_data_csv: str):
        """
        Set the filename of the article data CSV file to the specified value.

        The filename has to be a str, and valid according to its validation function.
        Contrary to other properties, it will not be stripped.

        Do not call this method before the configuration gets loaded.
        """
        self._require_loaded_valid_str(
            article_data_csv, validation.validate_article_data_csv)

        self._article_data_csv = article_data_csv

    def get_csv_delimiter(self) -> str:
        """
        Return a not-None str containing the CSV delimiter to use for the article data.

        Do not call this method before the configuration gets loaded.
        """
        self._require_loaded()

        return self._csv_delimiter

    def set_csv_delimiter(self, csv_delimiter: str):
        """
        Set the CSV delimiter of the article data CSV file to the specified value.

        The delimiter has to be a str, and valid according to its validation function.
        It is not required to be stripped, as that operation is performed before assigning it.

        Do not call this method before the configuration gets loaded.
        """
        self._require_loaded_valid_str(
            csv_delimiter, validation.validate_csv_delimiter)

        self._csv_delimiter = csv_delimiter.strip()

    def get_csv_id_header(self) -> str:
        """
        Return a not-None str containing the name of the ID column header in the article data.

        Do not call this method before the configuration gets loaded.
        """
        self._require_loaded()

        return self._csv_id_header

    def set_csv_id_header(self, csv_id_header: str):
        """
        Set the ID column header name of the article data CSV file to the specified value.

        The header has to be a str, and valid according to its validation function.
        It is not required to be stripped, as that operation is performed before assigning it.

        Do not call this method before the configuration gets loaded.
        """
        self._require_loaded_valid_str(
            csv_id_header, validation.validate_csv_id_column_header)

        self._csv_id_header = csv_id_header.strip()

    def save_uploader_config(self):
        """
        Save the properties assigned to the user configuration file.

        This overwrites the current configuration file with the values
        currently set for this configuration object.

        Do not call this method before the configuration gets loaded.
        """
        self._require_loaded()

        self._uploader_config.set(CONFLUENCE_CATEGORY,
                                  "base_url", self._base_url)
        self._uploader_config.set(CONFLUENCE_CATEGORY,
                                  "template_id", self._template_id)
        self._uploader_config.set(CONFLUENCE_CATEGORY, "placeholder_character",
                                  self._placeholder_character)
        self._uploader_config.set(CONFLUENCE_CATEGORY,
                                  "escape_character", self._escape_character)
        self._uploader_config.set(CONFLUENCE_CATEGORY,
                                  "upload_space", self._upload_space)
        self._uploader_config.set(CONFLUENCE_CATEGORY, "upload_parent_page_id",
                                  "" if self._upload_parent_page is None else self._upload_parent_page)

        self._uploader_config.set(BEHAVIOR_CATEGORY, "overwrite_existing_articles",
                                  self._overwrite_existing_articles)

        self._uploader_config.set(DATA_CATEGORY, "data_csv",
                                  self._article_data_csv)
        self._uploader_config.set(
            DATA_CATEGORY, "csv_delimiter", self._csv_delimiter)
        self._uploader_config.set(
            DATA_CATEGORY, "id_column_header", self._csv_id_header)

        with open(UPLOADER_CONFIG_FILENAME, 'w') as uploader_config_file:
            self._uploader_config.write(uploader_config_file)
