from collections import defaultdict
import cf_uploader.config as configuration
import unittest
import unittest.mock as mock
from unittest.mock import call
from parameterized import parameterized
from test_utils import EMPTY_STRINGS, NON_BOOL_TYPE_ELEMENTS_AND_NONE, NON_STRING_TYPE_ELEMENTS, NON_STRING_TYPE_ELEMENTS_AND_NONE
import cf_uploader.errors as errors


class ConfigTest(unittest.TestCase):

    def setUp(self):
        self._config = configuration.Config()
        self._loaded_config = configuration.Config()

        self._mock_config_updater = mock.MagicMock()
        self._mock_uploader_config_updater = mock.MagicMock()

        self._config._config = self._mock_config_updater
        self._config._uploader_config = self._mock_uploader_config_updater

        self._loaded_config._loaded = True

        # General assumption in all tests
        self._loaded_config._placeholder_character = "#"
        self._loaded_config._escape_character = "/"

    def test_initial_state(self):
        self.assertFalse(self._config.is_loaded())

    def _back_config_updater_with_dict(self, config_updater: mock.Mock, config_data: dict) -> None:
        """
        Mock the supplied config updater to be backed by the supplied dict.

        The dict has the category as key, and another dict as value, which has the config property
        name as key and the property value (a str) as value.

        The used dicts will use default values for unspecified keys:
         * For an unspecified category, an empty default dict will be returned
         * For an unspecified property, a mock with .value attribute "0" will be returned
           This is because "0" is accepted by all current parsers in the config module as a valid value.
        """

        # A helper function to create a mock with the .value attribute in one call
        def create_config_value_mock(value: str) -> mock.Mock:
            value_mock = mock.Mock()
            value_mock.value = value
            return value_mock

        def create_default_value_mock():
            return create_config_value_mock("0")

        # A dir with a similar structure as config_data, but the config value is wrapped
        # into a mock and accessed via its .value attribute
        processed_dir = {category: defaultdict(
            create_default_value_mock, {property: create_config_value_mock(config_data[category][property])
                                        for property in config_data[category].keys()})
                         for category in config_data.keys()}

        # Use a defaultdict so not all accessed config properties have to be defined here
        # By default forward to an empty default dict with "0" default property values
        config_updater.__getitem__.side_effect = defaultdict(
            lambda: defaultdict(create_default_value_mock, {}), processed_dir).__getitem__

    def test_load_strips_strings(self):
        self._back_config_updater_with_dict(self._config._uploader_config, {
            configuration.CONFLUENCE_CATEGORY: {"upload_space": "   AUTOSITE   "}})

        self._config.load()

        self.assertEqual("AUTOSITE", self._config._upload_space)

    @parameterized.expand([("TRUE", True), ("TrUE", True), ("true", True), ("    TRue    ", True),
                           ("false", False), ("other string unrelated", False), ("", False), (" ", False)])
    def test_load_recognizes_bool(self, bool_string, bool_value):
        self._back_config_updater_with_dict(self._config._config, {
            configuration.CONFLUENCE_CATEGORY: {"user_gui": bool_string}})

        self._config.load()

        self.assertEqual(bool_value, self._config._user_gui)

    @parameterized.expand(["0", " 0.0 ", "     0", "    0.00000 "])
    def test_load_recognizes_floats(self, float_string):
        self._back_config_updater_with_dict(self._config._config, {
            configuration.CONFLUENCE_CATEGORY: {"api_interaction_delay_seconds": float_string}})

        self._config.load()

        self.assertEqual(0.0, self._config._api_interaction_delay_seconds)

    def test_load_caps_negative_api_interaction_delay(self):
        self._back_config_updater_with_dict(self._config._config, {
            configuration.CONFLUENCE_CATEGORY: {"api_interaction_delay_seconds": "-10.23"}})

        self._config.load()

        self.assertEqual(0.0, self._config._api_interaction_delay_seconds)

    @parameterized.expand(EMPTY_STRINGS)
    def test_empty_upload_parent_page_get_parsed_as_none(self, empty_upload_parent_page_string):
        self._back_config_updater_with_dict(self._config._uploader_config, {
            configuration.CONFLUENCE_CATEGORY: {"upload_parent_page_id": empty_upload_parent_page_string}})

        self._config.load()

        self.assertEqual(None, self._config._upload_parent_page)

    def test_load(self):
        """Test loading from a mock file."""

        self._back_config_updater_with_dict(self._config._config, {
            configuration.CONFLUENCE_CATEGORY: {"api_interaction_delay_seconds": "1.32", "dump_template": "True",
                                                "dump_generated_articles": "false", "user_gui": "TRUE"}})

        self._back_config_updater_with_dict(self._config._uploader_config, {
            configuration.CONFLUENCE_CATEGORY: {"base_url": "url/", "template_id": "123", "placeholder_character": "+",
                                                "escape_character": "=", "upload_space": "US", "upload_parent_page_id": "212"},
            configuration.BEHAVIOR_CATEGORY: {"overwrite_existing_articles": "TrUE"},
            configuration.DATA_CATEGORY: {"data_csv": "/data.csv", "csv_delimiter": ".", "id_column_header": "id_column_1"}})

        self._config.load()

        self._config._config.read.assert_called_with(
            configuration.CONFIG_FILENAME)
        self._config._uploader_config.read.assert_called_with(
            configuration.UPLOADER_CONFIG_FILENAME)

        self.assertTrue(self._config._loaded)

        self.assertEqual(1.32, self._config._api_interaction_delay_seconds)
        self.assertTrue(self._config._dump_template)
        self.assertFalse(self._config._dump_generated_articles)
        self.assertTrue(self._config._user_gui)

        self.assertEqual("url/", self._config._base_url)
        self.assertEqual("123", self._config._template_id)
        self.assertEqual("+", self._config._placeholder_character)
        self.assertEqual("=", self._config._escape_character)
        self.assertEqual("US", self._config._upload_space)
        self.assertEqual("212", self._config._upload_parent_page)
        self.assertTrue(self._config._overwrite_existing_articles)
        self.assertEqual("/data.csv", self._config._article_data_csv)
        self.assertEqual(".", self._config._csv_delimiter)
        self.assertEqual("id_column_1", self._config._csv_id_header)

        # Just check those properties are defined after load()
        self.assertIsNotNone(self._config._errored_articles_csv)
        self.assertEqual("", self._config._username)
        self.assertEqual("", self._config._token)

    def _init_loaded_config_mock_with_valid_values(self):
        self._loaded_config._api_interaction_delay_seconds = 0
        self._loaded_config._dump_template = False
        self._loaded_config._dump_generated_articles = False
        self._loaded_config._user_gui = True

        self._loaded_config._base_url = "url/"
        self._loaded_config._template_id = "123"
        self._loaded_config._upload_space = "AUTOSITE"
        self._loaded_config._upload_parent_page = None
        self._loaded_config._overwrite_existing_articles = False
        self._loaded_config._username = "usr"
        self._loaded_config._token = "tkn"
        self._loaded_config._article_data_csv = "/data.csv"
        self._loaded_config._csv_delimiter = ";"
        self._loaded_config._csv_id_header = "id"

    def test_validate_all_unloaded_config(self):
        with self.assertRaises(errors.InvalidStateError):
            self._config.validate_all()

    @mock.patch('os.path.isfile')
    def test_validate_all_everything_valid(self, is_file_mock):
        is_file_mock.return_value = True  # Simulate that the data CSV file exists

        self._init_loaded_config_mock_with_valid_values()

        self.assertIsNone(self._loaded_config.validate_all())

    @parameterized.expand([("_base_url", ""), ("_template_id", ""), ("_upload_space", ""), ("_upload_parent_page", "we"), ("_username", ""),
                           ("_token", ""), ("_article_data_csv", ""), ("_csv_delimiter", ""), ("_csv_id_header", ""), ("_placeholder_character", ""), ("_escape_character", "")])
    @mock.patch('os.path.isfile')
    def test_validate_all_invalid_property(self, attribute_name, invalid_attribute_value, is_file_mock):
        """
        validate_all only checks str attributes. Their names are the parameters of this test.

        Because all but the upload parent page are invalid if empty, it suffices to check that.
        The tests for validate_all do not test the validations themselves, only that they take place, 
        so only one invalid case per property is picked (usually the empty one).
        """
        is_file_mock.return_value = True  # Simulate that the data CSV file exists

        self._init_loaded_config_mock_with_valid_values()

        setattr(self._loaded_config, attribute_name, invalid_attribute_value)

        validation_result = self._loaded_config.validate_all()

        self.assertEquals(validation_result[0], invalid_attribute_value)
        self.assertTrue(isinstance(validation_result[1], errors.ErrorWrapper))

    def test_get_api_interaction_delay_seconds_unloaded_config(self):
        with self.assertRaises(errors.InvalidStateError):
            self._config.get_api_interaction_delay_seconds()

    def test_get_api_interaction_delay_seconds(self):
        self._loaded_config._api_interaction_delay_seconds = 23

        self.assertEqual(
            23, self._loaded_config.get_api_interaction_delay_seconds())

    def test_get_dump_template_unloaded_config(self):
        with self.assertRaises(errors.InvalidStateError):
            self._config.get_dump_template()

    def test_get_dump_template(self):
        self._loaded_config._dump_template = True

        self.assertTrue(self._loaded_config.get_dump_template())

    def test_get_dump_generated_articles_unloaded_config(self):
        with self.assertRaises(errors.InvalidStateError):
            self._config.get_dump_generated_articles()

    def test_get_dump_generated_articles(self):
        self._loaded_config._dump_generated_articles = True

        self.assertTrue(self._loaded_config.get_dump_generated_articles())

    def test_get_user_gui_unloaded_config(self):
        with self.assertRaises(errors.InvalidStateError):
            self._config.get_user_gui()

    def test_get_user_gui(self):
        self._loaded_config._user_gui = False

        self.assertFalse(self._loaded_config.get_user_gui())

    def test_get_base_url_unloaded_config(self):
        with self.assertRaises(errors.InvalidStateError):
            self._config.get_base_url()

    def test_get_base_url(self):
        self._loaded_config._base_url = "http://test.com/"

        self.assertEquals("http://test.com/",
                          self._loaded_config.get_base_url())

    def test_set_base_url_unloaded_config(self):
        with self.assertRaises(errors.InvalidStateError):
            self._config.set_base_url("http://test.com/")

    @parameterized.expand(NON_STRING_TYPE_ELEMENTS_AND_NONE)
    def test_set_base_url_invalid_type(self, invalid_value):
        with self.assertRaises(TypeError):
            self._loaded_config.set_base_url(invalid_value)

    @parameterized.expand(EMPTY_STRINGS)
    def test_set_base_url_invalid_url(self, invalid_value):
        with self.assertRaises(ValueError):
            self._loaded_config.set_base_url(invalid_value)

    @parameterized.expand(["http://test.de/", "   http://test.de/test?var=10/     "])
    def test_set_base_url(self, base_url):
        self._loaded_config.set_base_url(base_url)

        self.assertEqual(base_url.strip(), self._loaded_config._base_url)

    def test_get_template_id_unloaded_config(self):
        with self.assertRaises(errors.InvalidStateError):
            self._config.get_template_id()

    def test_get_template_id(self):
        self._loaded_config._template_id = "314159"

        self.assertEquals("314159",
                          self._loaded_config.get_template_id())

    def test_set_template_id_unloaded_config(self):
        with self.assertRaises(errors.InvalidStateError):
            self._config.set_template_id("31415")

    @parameterized.expand(NON_STRING_TYPE_ELEMENTS_AND_NONE)
    def test_set_template_id_invalid_type(self, invalid_value):
        with self.assertRaises(TypeError):
            self._loaded_config.set_template_id(invalid_value)

    @parameterized.expand(EMPTY_STRINGS + [("wdsd",)])
    def test_set_template_id_invalid_values(self, invalid_value):
        with self.assertRaises(ValueError):
            self._loaded_config.set_template_id(invalid_value)

    @parameterized.expand(["123456", "   123456     "])
    def test_set_template_id(self, template_id):
        self._loaded_config.set_template_id(template_id)

        self.assertEqual(template_id.strip(), self._loaded_config._template_id)

    def test_get_placeholder_character_unloaded_config(self):
        with self.assertRaises(errors.InvalidStateError):
            self._config.get_placeholder_character()

    def test_get_placeholder_character(self):
        self._loaded_config._placeholder_character = "+"

        self.assertEquals("+",
                          self._loaded_config.get_placeholder_character())

    def test_set_placeholder_character_unloaded_config(self):
        with self.assertRaises(errors.InvalidStateError):
            self._config.set_placeholder_character("#")

    @parameterized.expand(NON_STRING_TYPE_ELEMENTS_AND_NONE)
    def test_set_placeholder_character_invalid_type(self, invalid_value):
        with self.assertRaises(TypeError):
            self._loaded_config.set_placeholder_character(invalid_value)

    @parameterized.expand(EMPTY_STRINGS + [("##",), ("a", ), ("1", ), ("/", )])
    def test_set_placeholder_character_invalid_values(self, invalid_value):
        with self.assertRaises(ValueError):
            self._loaded_config.set_placeholder_character(invalid_value)

    @parameterized.expand(["~", "   ~     "])
    def test_set_placeholder_character(self, placeholder_character):
        self._loaded_config.set_placeholder_character(placeholder_character)

        self.assertEqual(placeholder_character.strip(),
                         self._loaded_config._placeholder_character)

    def test_get_escape_character_unloaded_config(self):
        with self.assertRaises(errors.InvalidStateError):
            self._config.get_escape_character()

    def test_get_escape_character(self):
        self._loaded_config._escape_character = "+"

        self.assertEquals("+",
                          self._loaded_config.get_escape_character())

    def test_set_escape_character_unloaded_config(self):
        with self.assertRaises(errors.InvalidStateError):
            self._config.set_escape_character("/")

    @parameterized.expand(NON_STRING_TYPE_ELEMENTS_AND_NONE)
    def test_set_escape_character_invalid_type(self, invalid_value):
        with self.assertRaises(TypeError):
            self._loaded_config.set_escape_character(invalid_value)

    @parameterized.expand(EMPTY_STRINGS + [("##",), ("a", ), ("1", ), ("#", )])
    def test_set_escape_character_invalid_values(self, invalid_value):
        with self.assertRaises(ValueError):
            self._loaded_config.set_escape_character(invalid_value)

    @parameterized.expand(["~", "   ~     "])
    def test_set_escape_character(self, escape_character):
        self._loaded_config.set_escape_character(escape_character)

        self.assertEqual(escape_character.strip(),
                         self._loaded_config._escape_character)

    def test_get_upload_space_unloaded_config(self):
        with self.assertRaises(errors.InvalidStateError):
            self._config.get_upload_space()

    def test_get_upload_space(self):
        self._loaded_config._upload_space = "AUTOSITETE"

        self.assertEquals("AUTOSITETE",
                          self._loaded_config.get_upload_space())

    def test_set_upload_space_unloaded_config(self):
        with self.assertRaises(errors.InvalidStateError):
            self._config.set_upload_space("AUTOSITETE")

    @parameterized.expand(NON_STRING_TYPE_ELEMENTS_AND_NONE)
    def test_set_upload_space_invalid_type(self, invalid_value):
        with self.assertRaises(TypeError):
            self._loaded_config.set_upload_space(invalid_value)

    @parameterized.expand(EMPTY_STRINGS)
    def test_set_upload_space_invalid_values(self, invalid_value):
        with self.assertRaises(ValueError):
            self._loaded_config.set_upload_space(invalid_value)

    @parameterized.expand(["AUTOSITETE", "  AUTOSITETE "])
    def test_set_upload_space(self, upload_space):
        self._loaded_config.set_upload_space(upload_space)

        self.assertEqual(upload_space.strip(),
                         self._loaded_config._upload_space)

    def test_get_upload_parent_page_unloaded_config(self):
        with self.assertRaises(errors.InvalidStateError):
            self._config.get_upload_parent_page()

    @parameterized.expand([("314159",), (None,)])
    def test_get_upload_parent_page(self, value):
        self._loaded_config._upload_parent_page = value

        self.assertEquals(value,
                          self._loaded_config.get_upload_parent_page())

    def test_set_upload_parent_page_unloaded_config(self):
        with self.assertRaises(errors.InvalidStateError):
            self._config.set_upload_parent_page("314165")

    @parameterized.expand(NON_STRING_TYPE_ELEMENTS)
    def test_set_upload_parent_page_invalid_type(self, invalid_value):
        with self.assertRaises(TypeError):
            self._loaded_config.set_upload_parent_page(invalid_value)

    @parameterized.expand(EMPTY_STRINGS + [("abcd",), ("  a  ",), ("123%",)])
    def test_set_upload_parent_page_invalid_values(self, invalid_value):
        with self.assertRaises(ValueError):
            self._loaded_config.set_upload_parent_page(invalid_value)

    @parameterized.expand(["3141592", "  3141567 "])
    def test_set_upload_parent_page(self, parent_page):
        self._loaded_config.set_upload_parent_page(parent_page)

        self.assertEqual(parent_page.strip(),
                         self._loaded_config._upload_parent_page)

    def test_set_upload_parent_page_none(self):
        self._loaded_config.set_upload_parent_page(None)

        self.assertIsNone(self._loaded_config._upload_parent_page)

    def test_get_overwrite_existing_articles_unloaded_config(self):
        with self.assertRaises(errors.InvalidStateError):
            self._config.get_overwrite_existing_articles()

    def test_get_overwrite_existing_articles(self):
        self._loaded_config._overwrite_existing_articles = True

        self.assertTrue(self._loaded_config.get_overwrite_existing_articles())

    def test_set_overwrite_existing_articles_unloaded_config(self):
        with self.assertRaises(errors.InvalidStateError):
            self._config.set_overwrite_existing_articles(True)

    @parameterized.expand(NON_BOOL_TYPE_ELEMENTS_AND_NONE)
    def test_set_overwrite_existing_articles_invalid_type(self, invalid_value):
        with self.assertRaises(TypeError):
            self._loaded_config.set_overwrite_existing_articles(invalid_value)

    @parameterized.expand([(True,), (False,)])
    def test_set_overwrite_existing_articles(self, value):
        self._loaded_config.set_overwrite_existing_articles(value)

        self.assertEqual(value,
                         self._loaded_config._overwrite_existing_articles)

    def test_get_errored_articles_csv_unloaded_config(self):
        with self.assertRaises(errors.InvalidStateError):
            self._config.get_errored_articles_csv()

    def test_get_errored_articles_csv(self):
        self._loaded_config._errored_articles_csv = "./errors.csv"

        self.assertEquals("./errors.csv",
                          self._loaded_config.get_errored_articles_csv())

    def test_get_username_unloaded_config(self):
        with self.assertRaises(errors.InvalidStateError):
            self._config.get_username()

    def test_get_username(self):
        self._loaded_config._username = "testuser@test.com"

        self.assertEquals("testuser@test.com",
                          self._loaded_config.get_username())

    def test_set_username_unloaded_config(self):
        with self.assertRaises(errors.InvalidStateError):
            self._config.set_username("test@test.com")

    @parameterized.expand(NON_STRING_TYPE_ELEMENTS_AND_NONE)
    def test_set_username_invalid_type(self, invalid_value):
        with self.assertRaises(TypeError):
            self._loaded_config.set_username(invalid_value)

    @parameterized.expand(EMPTY_STRINGS)
    def test_set_username_invalid_values(self, invalid_value):
        with self.assertRaises(ValueError):
            self._loaded_config.set_username(invalid_value)

    @parameterized.expand(["test@test.test", "   te1st@test.com "])
    def test_set_username(self, valid_value):
        self._loaded_config.set_username(valid_value)

        # The setter does not trim by API, so don't compare trimmed strings like other tests do
        self.assertEqual(valid_value, self._loaded_config._username)

    def test_get_token_unloaded_config(self):
        with self.assertRaises(errors.InvalidStateError):
            self._config.get_token()

    def test_get_token(self):
        self._loaded_config._token = "ab1b258v8c84"

        self.assertEquals("ab1b258v8c84",
                          self._loaded_config.get_token())

    def test_set_token_unloaded_config(self):
        with self.assertRaises(errors.InvalidStateError):
            self._config.set_token("ab1b25-8v8c84")

    @parameterized.expand(NON_STRING_TYPE_ELEMENTS_AND_NONE)
    def test_set_token_invalid_type(self, invalid_value):
        with self.assertRaises(TypeError):
            self._loaded_config.set_token(invalid_value)

    @parameterized.expand(EMPTY_STRINGS)
    def test_set_token_invalid_values(self, invalid_value):
        with self.assertRaises(ValueError):
            self._loaded_config.set_token(invalid_value)

    @parameterized.expand(["d979t979", "   nz6790n8rt "])
    def test_set_token(self, valid_value):
        self._loaded_config.set_token(valid_value)

        # The setter does not trim by API, so don't compare trimmed strings like other tests do
        self.assertEqual(valid_value, self._loaded_config._token)

    def test_get_article_data_csv_unloaded_config(self):
        with self.assertRaises(errors.InvalidStateError):
            self._config.get_article_data_csv()

    def test_get_article_data_csv(self):
        self._loaded_config._article_data_csv = "./articles.csv"

        self.assertEquals("./articles.csv",
                          self._loaded_config.get_article_data_csv())

    def test_set_article_data_csv_unloaded_config(self):
        with self.assertRaises(errors.InvalidStateError):
            self._config.set_article_data_csv("./art.csv")

    @parameterized.expand(NON_STRING_TYPE_ELEMENTS_AND_NONE)
    def test_set_article_data_csv_invalid_type(self, invalid_value):
        with self.assertRaises(TypeError):
            self._loaded_config.set_article_data_csv(invalid_value)

    @parameterized.expand(EMPTY_STRINGS)
    def test_set_article_data_csv_empty_strings(self, invalid_value):
        with self.assertRaises(ValueError):
            self._loaded_config.set_article_data_csv(invalid_value)

    @mock.patch('os.path.isfile')
    def test_set_article_data_csv_file_not_existing(self, is_file_mock):
        is_file_mock.return_value = False

        with self.assertRaises(ValueError):
            self._loaded_config.set_article_data_csv("./unexisting_file.csv")

    @parameterized.expand(["./file.csv", "   ./file2.csv "])
    @mock.patch('os.path.isfile')
    def test_set_article_data_csv(self, valid_value, is_file_mock):
        is_file_mock.return_value = True

        self._loaded_config.set_article_data_csv(valid_value)

        # The setter does not trim by API, so don't compare trimmed strings like other tests do
        self.assertEqual(valid_value, self._loaded_config._article_data_csv)

    def test_get_csv_delimiter_unloaded_config(self):
        with self.assertRaises(errors.InvalidStateError):
            self._config.get_csv_delimiter()

    def test_get_csv_delimiter(self):
        self._loaded_config._csv_delimiter = ","

        self.assertEquals(",",
                          self._loaded_config.get_csv_delimiter())

    def test_set_csv_delimiter_unloaded_config(self):
        with self.assertRaises(errors.InvalidStateError):
            self._config.set_csv_delimiter(";")

    @parameterized.expand(NON_STRING_TYPE_ELEMENTS_AND_NONE)
    def test_set_csv_delimiter_invalid_type(self, invalid_value):
        with self.assertRaises(TypeError):
            self._loaded_config.set_csv_delimiter(invalid_value)

    @parameterized.expand(EMPTY_STRINGS + [(";;",)])
    def test_set_csv_delimiter_invalid_values(self, invalid_value):
        with self.assertRaises(ValueError):
            self._loaded_config.set_csv_delimiter(invalid_value)

    @parameterized.expand([",", "   - "])
    def test_set_csv_delimiter(self, valid_value):
        self._loaded_config.set_csv_delimiter(valid_value)

        self.assertEqual(valid_value.strip(),
                         self._loaded_config._csv_delimiter)

    def test_get_csv_id_header_unloaded_config(self):
        with self.assertRaises(errors.InvalidStateError):
            self._config.get_csv_id_header()

    def test_get_csv_id_header(self):
        self._loaded_config._csv_id_header = "id2"

        self.assertEquals("id2",
                          self._loaded_config.get_csv_id_header())

    def test_set_csv_id_header_unloaded_config(self):
        with self.assertRaises(errors.InvalidStateError):
            self._config.set_csv_id_header("id2")

    @parameterized.expand(NON_STRING_TYPE_ELEMENTS_AND_NONE)
    def test_set_csv_id_header_invalid_type(self, invalid_value):
        with self.assertRaises(TypeError):
            self._loaded_config.set_csv_id_header(invalid_value)

    @parameterized.expand(EMPTY_STRINGS)
    def test_set_csv_id_header_invalid_values(self, invalid_value):
        with self.assertRaises(ValueError):
            self._loaded_config.set_csv_id_header(invalid_value)

    @parameterized.expand(["id2", "   header "])
    def test_set_csv_id_header(self, valid_value):
        self._loaded_config.set_csv_id_header(valid_value)

        self.assertEqual(valid_value.strip(),
                         self._loaded_config._csv_id_header)

    def test_save_uploader_config_unloaded(self):
        with self.assertRaises(errors.InvalidStateError):
            self._config.save_uploader_config()

    @mock.patch('builtins.open')
    def test_save_uploader_config(self, open_mock):
        self._init_loaded_config_mock_with_valid_values()

        self._loaded_config._uploader_config = self._mock_uploader_config_updater

        self._loaded_config.save_uploader_config()

        set_calls = [call(
            configuration.DATA_CATEGORY, "id_column_header", "id"), call(
            configuration.DATA_CATEGORY, "csv_delimiter", ";"), call(
            configuration.DATA_CATEGORY, "data_csv", "/data.csv"), call(
            configuration.BEHAVIOR_CATEGORY, "overwrite_existing_articles", False), call(
            configuration.CONFLUENCE_CATEGORY, "upload_parent_page_id", ""), call(
            configuration.CONFLUENCE_CATEGORY, "upload_space", "AUTOSITE"), call(
            configuration.CONFLUENCE_CATEGORY, "escape_character", "/"), call(
            configuration.CONFLUENCE_CATEGORY, "placeholder_character", "#"), call(
            configuration.CONFLUENCE_CATEGORY, "template_id", "123"), call(
            configuration.CONFLUENCE_CATEGORY, "base_url", "url/")]

        self._loaded_config._uploader_config.set.assert_has_calls(
            set_calls, any_order=True)

        self._loaded_config._uploader_config.write.assert_called()
