import unittest
import unittest.mock as mock
import cf_uploader.validation as validation
from parameterized import parameterized
from test_utils import EMPTY_STRINGS_AND_NONE
import cf_uploader.errors as errors


class ValidationTest(unittest.TestCase):

    @parameterized.expand(["https://testsite.atlassian.net/wiki/rest/api/content/", " http://test.com/", "https://test.de/ ", "   http://test.test/api/content/     "])
    def test_validate_base_url_valid(self, valid_base_url):
        self.assertIsNone(validation.validate_base_url(valid_base_url))

    @parameterized.expand(EMPTY_STRINGS_AND_NONE)
    def test_validate_base_url_empty(self, invalid_base_url):
        self.assertEqual(errors.CONFIG_BASE_URL_EMPTY,
                         validation.validate_base_url(invalid_base_url))

    @parameterized.expand(["https://testsite.atlassian.net/wiki/rest/api/content", " http://test.com", "https://test.de ", "   http://test.test/api/content     "])
    def test_validate_base_url_not_ending_with_slash(self, invalid_base_url):
        self.assertEqual(errors.CONFIG_BASE_URL_NOT_ENDING_WITH_SLASH,
                         validation.validate_base_url(invalid_base_url))

    @ parameterized.expand(["123456", "0", " 12", "   12"])
    def test_validate_template_id_valid(self, valid_template_id_string):
        self.assertIsNone(validation.validate_template_id(
            valid_template_id_string))

    @ parameterized.expand(EMPTY_STRINGS_AND_NONE)
    def test_validate_template_id_empty(self, empty_template_id_string):
        self.assertEqual(errors.CONFIG_TEMPLATE_ID_EMPTY, validation.validate_template_id(
            empty_template_id_string))

    @ parameterized.expand(["a", " a ", "123 12", "s2s", "123_"])
    def test_validate_template_id_not_numeric(self, non_numeric_template_id):
        self.assertEqual(errors.CONFIG_TEMPLATE_ID_NOT_NUMERIC,
                         validation.validate_template_id(non_numeric_template_id))

    @ parameterized.expand([";", " ~", "# ", "   $ ", "\\"])
    def test_validate_placeholder_character_valid(self, valid_placeholder_character):
        self.assertIsNone(validation.validate_placeholder_character(
            valid_placeholder_character, "/"))

    @ parameterized.expand(EMPTY_STRINGS_AND_NONE)
    def test_validate_placeholder_character_empty(self, empty_placeholder_character_string):
        self.assertEqual(validation.validate_placeholder_character(
            empty_placeholder_character_string, "~"), errors.CONFIG_PLACEHOLDER_EMPTY)

    @ parameterized.expand([";!", "~%"])
    def test_validate_placeholder_character_not_single_char(self, invalid_placeholder_character):
        self.assertEqual(validation.validate_placeholder_character(
            invalid_placeholder_character, "~"), errors.CONFIG_PLACEHOLDER_NO_SINGLE_CHAR)

    @ parameterized.expand(["a", " a", "a ", "1", "g", "x", ".", "-", "_"])
    def test_validate_placeholder_character_invalid_char(self, invalid_placeholder_character):
        self.assertEqual(validation.validate_placeholder_character(
            invalid_placeholder_character, "~"), errors.CONFIG_PLACEHOLDER_INVALID_CHAR)

    def test_validate_placeholder_character_equal_to_escape_character(self):
        self.assertEqual(validation.validate_placeholder_character(
            "/", "/"), errors.CONFIG_ESCAPE_CHAR_EQUALS_PLACEHOLDER)

    @ parameterized.expand([";", " ~", "/ ", "   $ ", "\\"])
    def test_validate_escape_character_valid(self, valid_escape_character):
        self.assertIsNone(
            validation.validate_escape_character(valid_escape_character, "#"))

    @parameterized.expand(EMPTY_STRINGS_AND_NONE)
    def test_validate_escape_character_empty(self, empty_escape_character_string):
        self.assertEqual(validation.validate_escape_character(
            empty_escape_character_string, "#"), errors.CONFIG_ESCAPE_EMPTY)

    @parameterized.expand([";!", "~%"])
    def test_validate_escape_character_not_single_char(self, invalid_escape_character):
        self.assertEqual(validation.validate_escape_character(
            invalid_escape_character, "#"), errors.CONFIG_ESCAPE_NO_SINGLE_CHAR)

    @parameterized.expand(["a", " a", "a ", "1", "g", "x", ".", "-", "_"])
    def test_validate_escape_character_invalid_char(self, invalid_escape_character):
        self.assertEqual(validation.validate_escape_character(
            invalid_escape_character, "#"), errors.CONFIG_ESCAPE_INVALID_CHAR)

    def test_validate_escape_character_equal_to_escape_character(self):
        self.assertEqual(validation.validate_escape_character(
            "#", "#"), errors.CONFIG_ESCAPE_CHAR_EQUALS_PLACEHOLDER)

    @parameterized.expand(["AUTOSITETE", " AUTOSITETE", "AUTOSITETE ", "us", "u_space"])
    def test_validate_upload_space_valid(self, valid_upload_space):
        self.assertIsNone(
            validation.validate_upload_space(valid_upload_space))

    @parameterized.expand(EMPTY_STRINGS_AND_NONE)
    def test_validate_upload_space_empty(self, empty_upload_space_string):
        self.assertEqual(errors.CONFIG_UPLOAD_SPACE_EMPTY,
                         validation.validate_upload_space(empty_upload_space_string))

    @parameterized.expand([" 123", "123", "123 ", "456786"])
    def test_validate_parent_page_id_valid_non_empty(self, valid_parent_page_id):
        self.assertIsNone(
            validation.validate_parent_page_id(valid_parent_page_id))

    @parameterized.expand(EMPTY_STRINGS_AND_NONE)
    def test_validate_parent_page_id_empty_not_allowed(self, empty_parent_page_id_string):
        self.assertEquals(errors.CONFIG_PARENT_PAGE_ID_EMPTY,
                          validation.validate_parent_page_id(empty_parent_page_id_string, True))

    @parameterized.expand(EMPTY_STRINGS_AND_NONE)
    def test_validate_parent_page_id_empty_allowed(self, empty_parent_page_id_string):
        self.assertIsNone(validation.validate_parent_page_id(
            empty_parent_page_id_string, False))

    @parameterized.expand(["abc", "a", " a", " b", "123 123", "23 a 32"])
    def test_validate_parent_page_id_invalid_non_numeric(self, invalid_parent_page_id):
        self.assertEquals(errors.CONFIG_PARENT_PAGE_ID_NOT_NUMERIC,
                          validation.validate_parent_page_id(invalid_parent_page_id))

    @parameterized.expand(["./file.csv", "   ./file.csv", "./file.csv     "])
    @mock.patch('os.path.isfile')
    def test_validate_article_data_csv_valid(self, valid_path, is_file_mock):
        is_file_mock.return_value = True

        self.assertIsNone(validation.validate_article_data_csv(valid_path))

        is_file_mock.assert_called_once_with("./file.csv")

    @parameterized.expand(EMPTY_STRINGS_AND_NONE)
    def test_validate_article_data_csv_empty(self, empty_path_string):
        self.assertEqual(errors.CONFIG_DATA_CSV_PATH_EMPTY,
                         validation.validate_article_data_csv(empty_path_string))

    @parameterized.expand(["./file.csv"])
    @mock.patch('os.path.isfile')
    def test_validate_article_data_csv_non_existing(self, valid_path, is_file_mock):
        is_file_mock.return_value = False

        self.assertEqual(errors.CONFIG_DATA_CSV_DOES_NOT_EXIST,
                         validation.validate_article_data_csv(valid_path))

        is_file_mock.assert_called_once_with("./file.csv")

    @parameterized.expand([";", " ;", "; ", ",", "3", "b"])
    def test_validate_csv_delimiter_valid(self, valid_csv_delimiter):
        self.assertIsNone(
            validation.validate_csv_delimiter(valid_csv_delimiter))

    @parameterized.expand(EMPTY_STRINGS_AND_NONE)
    def test_validate_csv_delimiter_empty(self, empty_string):
        self.assertEqual(errors.CONFIG_CSV_DELIMITER_EMPTY,
                         validation.validate_csv_delimiter(empty_string))

    @parameterized.expand([";;", "asdasdas"])
    def test_validate_csv_delimiter_non_single_character(self, invalid_csv_delimiter):
        self.assertEqual(errors.CONFIG_CSV_DELIMITER_NO_SINGLE_CHAR,
                         validation.validate_csv_delimiter(invalid_csv_delimiter))

    @parameterized.expand(["1", "id", " id", "id ", "eddfdfdfd"])
    def test_set_csv_id_column_header(self, valid_header):
        self.assertIsNone(
            validation.validate_csv_id_column_header(valid_header))

    @parameterized.expand(EMPTY_STRINGS_AND_NONE)
    def test_set_csv_id_column_header_empty(self, empty_string):
        self.assertEqual(errors.CONFIG_CSV_ID_COLUMN_HEADER_EMPTY,
                         validation.validate_csv_id_column_header(empty_string))

    @parameterized.expand(["test-test.test@test.com", "    test@test.com", " t@test.com   "])
    def test_validate_username_valid(self, valid_username):
        self.assertIsNone(
            validation.validate_username(valid_username))

    @parameterized.expand(EMPTY_STRINGS_AND_NONE)
    def test_validate_username_empty(self, empty_string):
        self.assertEqual(errors.CONFIG_USERNAME_EMPTY,
                         validation.validate_username(empty_string))

    @parameterized.expand(["a7za7zd294hezvb3fnd9377bdee86nv83"])
    def test_validate_token_valid(self, valid_token):
        self.assertIsNone(
            validation.validate_token(valid_token))

    @parameterized.expand(EMPTY_STRINGS_AND_NONE)
    def test_validate_token_empty(self, empty_string):
        self.assertEqual(errors.CONFIG_TOKEN_EMPTY,
                         validation.validate_token(empty_string))
