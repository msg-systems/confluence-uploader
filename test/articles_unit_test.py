import unittest
import unittest.mock as mock
from parameterized import parameterized
from cf_uploader.articles import ArticleProcessor
import cf_uploader.errors as errors


class ArticlesUnitTest(unittest.TestCase):

    def setUp(self):
        self._config = mock.Mock()
        self._article_processor = ArticleProcessor(self._config)

        self._test_data_entries_1 = [{"id": "1", "value_1": "val"}]

        # Set default config values
        self._config.get_csv_delimiter.return_value = ";"
        self._config.get_csv_id_header.return_value = "id"
        self._config.get_escape_character.return_value = "~"
        self._config.get_placeholder_character.return_value = "#"

    @mock.patch('csv.DictReader')
    @mock.patch('builtins.open')
    def test_load_article_data_entries_are_trimmed(self, open_mock, dict_reader_mock):
        dict_reader_mock.return_value = [
            {"id": "    value 1", "value": "     val     "}]

        loaded_articles = self._article_processor.load_article_data()

        self.assertEqual("value 1", loaded_articles[0]['id'])
        self.assertEqual("val", loaded_articles[0]['value'])

    @parameterized.expand([
        ([{"id2": "    value 1", "value": "     val     "}], ),
        ([{"id": "val"}, {"id2": "val2"}], )])
    @mock.patch('csv.DictReader')
    @mock.patch('builtins.open')
    def test_load_article_data_no_id_column_present(self, raw_articles, open_mock, dict_reader_mock):
        dict_reader_mock.return_value = raw_articles

        with self.assertRaises(RuntimeError) as cm:
            self._article_processor.load_article_data()

        exception_args = cm.exception.args

        self.assertEqual(errors.ARTICLE_DATA_NO_ID_COLUMN, exception_args[0])
        self.assertEqual("id", exception_args[1])

    @parameterized.expand([
        ([{"id": "1"}, {"id": "1"}, {"id": "2"}, {"id": "3"}, {"id": "3"}], 2),
        ([{"id": "1"}, {"id": "1"}], 1)])
    @mock.patch('csv.DictReader')
    @mock.patch('builtins.open')
    def test_load_article_data_not_unique_ids(self, raw_articles, duplicated_articles_count, open_mock, dict_reader_mock):
        dict_reader_mock.return_value = raw_articles

        with self.assertRaises(RuntimeError) as cm:
            self._article_processor.load_article_data()

        exception_args = cm.exception.args
        self.assertEqual(errors.ARTICLE_DATA_NO_UNIQUE_IDS, exception_args[0])
        self.assertEqual(duplicated_articles_count, exception_args[1])

    @mock.patch('csv.DictReader')
    @mock.patch('builtins.open')
    def test_load_article_data(self, open_mock, dict_reader_mock):
        dict_reader_mock.return_value = [{"id": "1 ", "p1": "v1"}, {
            "id": "2", "p1": "v2"}, {"id": "4", "p1": "v3", "p2": "v2"}]

        loaded_articles = self._article_processor.load_article_data()

        self.assertEqual([{"id": "1", "p1": "v1"}, {
            "id": "2", "p1": "v2"}, {"id": "4", "p1": "v3", "p2": "v2"}], loaded_articles)

    def test_generate_articles_none_template(self):
        with self.assertRaises(ValueError):
            self._article_processor.generate_articles(
                None, self._test_data_entries_1)

    def _create_template(self, title, body):
        return {"title": title, "body": {"storage": {"value": body}}}

    def test_generate_articles_none_data(self):
        with self.assertRaises(ValueError):
            self._article_processor.generate_articles(
                self._create_template("T", "B"), None)

    def _generate_articles_test_helper(self, title, body, data_entries, processed_title, processed_body):
        template = self._create_template(title, body)

        processed_article = self._create_template(
            processed_title, processed_body)

        self.assertSequenceEqual([("1", processed_article)], self._article_processor.generate_articles(
            template, data_entries))

    def test_generate_articles_no_placeholders(self):
        self._generate_articles_test_helper(
            "Title", "Body", self._test_data_entries_1, "Title", "Body")

    def test_generate_articles_single_placeholder(self):
        self._generate_articles_test_helper(
            "Title #value_1#", "Body #value_1#", self._test_data_entries_1, "Title val", "Body val")

    def test_generate_articles_escaped_placeholder_character(self):
        self._generate_articles_test_helper(
            "Title~#", "Body ~##id#", self._test_data_entries_1, "Title#", "Body #1")

    def test_generate_articles_single_escape_character(self):
        self._generate_articles_test_helper(
            "Title~", "~~~B~o~d~y ~", self._test_data_entries_1, "Title~", "~~~B~o~d~y ~")

    def test_generate_articles_placeholder_characters_in_csv(self):
        self._generate_articles_test_helper(
            "Title", "Body #value#", [{"id": "1", "value": "#val"}], "Title", "Body #val")

    def test_generate_articles_valid_placeholder_in_csv(self):
        self._generate_articles_test_helper(
            "Title", "Body #value#", [{"id": "1", "value": "#id#"}], "Title", "Body #id#")

    def test_generate_articles_invalid_placeholder_in_csv(self):
        self._generate_articles_test_helper(
            "Title", "Body #value#", [{"id": "1", "value": "#id23#"}], "Title", "Body #id23#")

    def test_generate_articles_escape_characters_in_csv(self):
        self._generate_articles_test_helper(
            "Title", "Body #value#", [{"id": "1", "value": "~"}], "Title", "Body ~")

    def test_generate_articles_escaped_placeholder_characters_in_csv(self):
        self._generate_articles_test_helper(
            "Title", "Body #value#", [{"id": "1", "value": "~#"}], "Title", "Body ~#")

    def test_generate_articles_duplicated_titles(self):
        template = self._create_template("Title #value#", "")
        data_entries = [{"id": "1", "value": "v1"}, {"id": "2", "value": "v1"}]

        with self.assertRaises(RuntimeError) as cm:
            self._article_processor.generate_articles(template, data_entries)

        exception_args = cm.exception.args
        self.assertEqual(errors.ARTICLE_VALIDATION_ERRORS, exception_args[0])

    def test_generate_articles_unknown_placeholder(self):
        template = self._create_template("Title", "#sdg#")
        data_entries = self._test_data_entries_1

        with self.assertRaises(RuntimeError) as cm:
            self._article_processor.generate_articles(template, data_entries)

        exception_args = cm.exception.args
        self.assertEqual(errors.ARTICLE_UNKNOWN_PLACEHOLDER, exception_args[0])
        self.assertEqual("1", exception_args[1])
        self.assertEqual("#sdg#", exception_args[2])

    @parameterized.expand(["#", "##", "#asd", "d#", "#placeholder placeholder#", "#placeholder:1#", "#placeholder~1#"])
    def test_generate_articles_invalid_placeholders(self, invalid_placeholder):
        template = self._create_template("Title", invalid_placeholder)
        data_entries = self._test_data_entries_1

        with self.assertRaises(RuntimeError) as cm:
            self._article_processor.generate_articles(template, data_entries)

        exception_args = cm.exception.args
        self.assertEqual(
            errors.ARTICLE_SINGLE_PLACEHOLDER_CHARACTER, exception_args[0])
        self.assertEqual("1", exception_args[1])

    def test_write_errored_articles_none_articles(self):
        with self.assertRaises(ValueError):
            self._article_processor.write_errored_articles(None)
