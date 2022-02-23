from requests.exceptions import SSLError
import json
import unittest
import unittest.mock as mock
from parameterized import parameterized
import cf_uploader.errors as errors
import cf_uploader.confluence as confluence


class ConfluenceTest(unittest.TestCase):

    def setUp(self):
        self._config = mock.Mock()
        self._confluence = confluence.ConfluenceAPI(self._config)

        # Set default config values
        self._config.get_api_interaction_delay_seconds.return_value = 0
        self._config.get_base_url.return_value = "https://test.com/rest/api/content/"
        self._config.get_template_id.return_value = "123456"
        self._config.get_username.return_value = "username"
        self._config.get_token.return_value = "password"
        self._config.get_upload_parent_page.return_value = "31415"
        self._config.get_upload_space.return_value = "AUTOSITE"

    @mock.patch("requests.get")
    def test_retrieve_template_error_returned_from_rest(self, requests_get_mock):

        response_mock = mock.Mock()
        response_mock.status_code = 403
        response_mock.content = bytearray("Error message test", "utf-8")

        requests_get_mock.return_value = response_mock

        with self.assertRaises(RuntimeError) as cm:
            self._confluence.retrieve_template()

        self.assertEqual(errors.CONFLUENCE_DOWNLOAD_FAILED,
                         cm.exception.args[0])
        self.assertEqual("123456",
                         cm.exception.args[2])

    @mock.patch("requests.get")
    def test_retrieve_template_ssl_error(self, requests_get_mock):
        requests_get_mock.side_effect = SSLError("SSL Error Test")

        with self.assertRaises(RuntimeError) as cm:
            self._confluence.retrieve_template()

        self.assertEqual(errors.SSL_ERROR, cm.exception.args[0])

    @mock.patch("requests.get")
    def test_retrieve_template_key_error_upon_processing(self, requests_get_mock):
        response_mock = mock.Mock()
        response_mock.status_code = 200
        response_mock.json.return_value = {"title": "Title"}

        requests_get_mock.return_value = response_mock

        with self.assertRaises(RuntimeError) as cm:
            self._confluence.retrieve_template()

        self.assertEqual(errors.CONFLUENCE_TEMPLATE_PROCESSING_FAILED,
                         cm.exception.args[0])
        self.assertEqual("123456",
                         cm.exception.args[1])

    @mock.patch("requests.get")
    @mock.patch("time.sleep")
    def test_retrieve_template(self, time_sleep_mock, requests_get_mock):
        self._config.get_api_interaction_delay_seconds.return_value = 1.43

        response_mock = mock.Mock()
        response_mock.status_code = 200
        response_mock.json.return_value = {"type": "page", "trim": "remove", "title": "Title", "space": {"key": "AUTOSITE", "trim": "val"}, "body": {
            "storage": {"value": "CONTENT", "representation": "storage", "trim": "s"}, "trim": "2"}}

        requests_get_mock.return_value = response_mock

        # Test that the unnecessary properties are trimmed
        processed_template = {"type": "page", "title": "Title", "space": {"key": "AUTOSITE"}, "body": {
            "storage": {"value": "CONTENT", "representation": "storage"}}, "ancestors": [{"id": "31415"}]}

        self.assertEqual(processed_template,
                         self._confluence.retrieve_template())

        # Test that the pause delay is taken into account
        time_sleep_mock.assert_called_with(1.43)

    @mock.patch("requests.get")
    def test_retrieve_template_no_parent_page(self, requests_get_mock):
        self._config.get_upload_parent_page.return_value = None

        response_mock = mock.Mock()
        response_mock.status_code = 200
        response_mock.json.return_value = {"type": "page", "title": "Title", "space": {"key": "AUTOSITE"}, "body": {
            "storage": {"value": "CONTENT", "representation": "storage"}}}

        requests_get_mock.return_value = response_mock

        self.assertEqual(response_mock.json.return_value,
                         self._confluence.retrieve_template())

    def test_exists_none_page_title(self):
        with self.assertRaises(TypeError):
            self._confluence.exists(None)

    @mock.patch("requests.get")
    @mock.patch("cf_uploader.errors.CONFLUENCE_EXISTENCE_CHECK_FAILED.print_message")
    def test_exists_error_returned_from_rest(self, error_print_msg_mock, requests_get_mock):
        response_mock = mock.Mock()
        response_mock.status_code = 403
        response_mock.content = bytearray("Error message test", "utf-8")

        requests_get_mock.return_value = response_mock

        self.assertIsNone(self._confluence.exists("article"))

        # Check that the error message is logged
        error_print_msg_mock.assert_called()

    @parameterized.expand([({},), ({"arg": "1"},), ({"size": "df"},), ({"size": "4"},), ({"size": "4", "results": {"id": "1"}},),
                           ({"size": "4", "results": []},), ({"size": "4", "results": [
                               {"value": "value"}]},), ({"size": "4", "results": [{"id": "4"}]},),
                           ({"size": "4", "results": [
                            {"id": "4", "version": {"arg": "3"}}]},),
                           ({"size": "4", "results": [{"id": "4", "version": {"number": "df"}}]},)])
    @mock.patch("requests.get")
    def test_exists_invalid_responses(self, invalid_response_json, requests_get_mock):
        response_mock = mock.Mock()
        response_mock.status_code = 200
        response_mock.content = bytearray("Success", "utf-8")
        response_mock.json.return_value = invalid_response_json

        requests_get_mock.return_value = response_mock

        self.assertIsNone(self._confluence.exists("article"))

    @mock.patch("requests.get")
    def test_exists_not_existing(self, requests_get_mock):
        response_mock = mock.Mock()
        response_mock.status_code = 200
        response_mock.content = bytearray("Success", "utf-8")
        response_mock.json.return_value = {"size": "0"}

        requests_get_mock.return_value = response_mock

        self.assertIsNone(self._confluence.exists("article"))

    @mock.patch("requests.get")
    def test_exists_existing(self, requests_get_mock):
        response_mock = mock.Mock()
        response_mock.status_code = 200
        response_mock.content = bytearray("Success", "utf-8")
        response_mock.json.return_value = {"size": "1", "results": [
            {"id": "314", "version": {"number": "12"}}]}

        requests_get_mock.return_value = response_mock

        self.assertEqual(("314", 12), self._confluence.exists("article"))

    def test_upload_article_none_id(self):
        with self.assertRaises(TypeError):
            self._confluence.upload_article(None, {})

    def test_upload_article_none_json(self):
        with self.assertRaises(TypeError):
            self._confluence.upload_article("3", None)

    @ mock.patch("requests.post")
    @ mock.patch("cf_uploader.errors.CONFLUENCE_UPLOAD_FAILED.print_message")
    def test_upload_article_no_existing_override_error_returned_from_rest(self, error_print_msg_mock, requests_post_mock):
        self._config.get_overwrite_existing_articles.return_value = False

        response_mock = mock.Mock()
        response_mock.status_code = 403
        response_mock.content = bytearray("Error message test", "utf-8")

        requests_post_mock.return_value = response_mock

        self.assertFalse(self._confluence.upload_article("article", {"type": "page", "title": "Title", "space": {"key": "AUTOSITE"}, "body": {
            "storage": {"value": "CONTENT", "representation": "storage"}}, "ancestors": [{"id": "31415"}]}))

        # Check that the error message is logged
        error_print_msg_mock.assert_called()

    @ mock.patch("requests.post")
    def test_upload_article_no_existing_override_ssl_error(self, requests_post_mock):
        self._config.get_overwrite_existing_articles.return_value = False

        requests_post_mock.side_effect = SSLError("SSL Error Test")

        with self.assertRaises(RuntimeError) as cm:
            self._confluence.upload_article("article", {"type": "page", "title": "Title", "space": {"key": "AUTOSITE"}, "body": {
                "storage": {"value": "CONTENT", "representation": "storage"}}, "ancestors": [{"id": "31415"}]})

        self.assertEqual(errors.SSL_ERROR, cm.exception.args[0])

    @ mock.patch("requests.post")
    @ mock.patch("cf_uploader.logger.main_logger.info")
    def test_upload_article_no_existing_override(self, success_print_msg_mock, requests_post_mock):
        self._config.get_overwrite_existing_articles.return_value = False

        response_mock = mock.Mock()
        response_mock.status_code = 200
        response_mock.content = bytearray("Success message", "utf-8")

        requests_post_mock.return_value = response_mock

        self.assertTrue(self._confluence.upload_article("article", {"type": "page", "title": "Title", "space": {"key": "AUTOSITE"}, "body": {
            "storage": {"value": "CONTENT", "representation": "storage"}}, "ancestors": [{"id": "31415"}]}))

        # Check that the success message is logged
        success_print_msg_mock.assert_called()

    @ mock.patch("requests.put")
    @ mock.patch("cf_uploader.errors.CONFLUENCE_UPDATE_FAILED.print_message")
    def test_upload_article_existing_override_error_returned_from_rest(self, error_print_msg_mock, requests_post_mock):
        self._config.get_overwrite_existing_articles.return_value = True

        self._confluence.exists = mock.Mock(return_value=("123454", 23))

        response_mock = mock.Mock()
        response_mock.status_code = 403
        response_mock.content = bytearray("Error message test", "utf-8")

        requests_post_mock.return_value = response_mock

        self.assertFalse(self._confluence.upload_article("article", {"type": "page", "title": "Title", "space": {"key": "AUTOSITE"}, "body": {
            "storage": {"value": "CONTENT", "representation": "storage"}}, "ancestors": [{"id": "31415"}]}))

        # Check that the error message is logged
        error_print_msg_mock.assert_called()

    @ mock.patch("requests.put")
    def test_upload_article_existing_override_ssl_error(self, requests_post_mock):
        self._config.get_overwrite_existing_articles.return_value = True

        self._confluence.exists = mock.Mock(return_value=("123454", 23))

        requests_post_mock.side_effect = SSLError("SSL Error Test")

        with self.assertRaises(RuntimeError) as cm:
            self._confluence.upload_article("article", {"type": "page", "title": "Title", "space": {"key": "AUTOSITE"}, "body": {
                "storage": {"value": "CONTENT", "representation": "storage"}}, "ancestors": [{"id": "31415"}]})

        self.assertEqual(errors.SSL_ERROR, cm.exception.args[0])

    @ mock.patch("requests.put")
    @ mock.patch("cf_uploader.logger.main_logger.info")
    @ mock.patch("time.sleep")
    def test_upload_article_existing_override(self, time_sleep_mock, info_print_msg_mock, requests_put_mock):
        self._config.get_api_interaction_delay_seconds.return_value = 1.43
        self._config.get_overwrite_existing_articles.return_value = True

        self._confluence.exists = mock.Mock(return_value=("123454", 23))

        response_mock = mock.Mock()
        response_mock.status_code = 200
        response_mock.content = bytearray("Success", "utf-8")

        requests_put_mock.return_value = response_mock

        self.assertTrue(self._confluence.upload_article("article", {"type": "page", "title": "Title", "space": {"key": "AUTOSITE"}, "body": {
            "storage": {"value": "CONTENT", "representation": "storage"}}}))

        # Check that a success message is logged
        info_print_msg_mock.assert_called()

        # The JSON to send when an existing article should be replaced
        update_article_data = {"id": "123454", "type": "page", "title": "Title", "space": {"key": "AUTOSITE"}, "body": {
            "storage": {"value": "CONTENT", "representation": "storage"}}, "version": {"number": "24"}}

        requests_put_mock.assert_called()

        # Check that the JSON put into requests.put(data=...) is the same as update_article_data
        self.assertEqual(update_article_data, json.loads(
            requests_put_mock.call_args.kwargs["data"]))

        # Test that the pause delay is taken into account
        time_sleep_mock.assert_called_with(1.43)
