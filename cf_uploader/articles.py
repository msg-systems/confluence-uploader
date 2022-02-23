"""
Contains code regarding the handling of articles.

This especially includes the processing of the template and the data CSV to finished articles.
"""
import csv
import re
import copy
import json
from . import config
from . import errors


class ArticleProcessor:
    """This class models an object processing articles."""

    def __init__(self, configuration: config.Config):
        """Assign the configuration object."""
        self._config = configuration

    def load_article_data(self) -> list:
        """
        Return article data loaded from the configured data CSV file.

        The article CSV data are returned as a dictionary.
        """
        data_entries = []  # The dictionary to return
        ids = set()  # Used for validating uniqueness of ids

        with open(self._config.get_article_data_csv(), 'r') as file:

            csv_file = csv.DictReader(
                file, delimiter=self._config.get_csv_delimiter())

            for row in csv_file:

                # Strip all entries
                for key in row.keys():
                    row[key] = str(row[key]).strip()

                # No ID column present
                if self._config.get_csv_id_header() not in row.keys():
                    raise RuntimeError(
                        errors.ARTICLE_DATA_NO_ID_COLUMN, self._config.get_csv_id_header())

                id_value = row[self._config.get_csv_id_header()]

                # Don't throw an error here, as all rows should be validated
                # Just print the error message for the individual error.
                if id_value in ids:
                    errors.ARTICLE_DATA_NO_UNIQUE_ID.print_message(id_value)

                ids.add(id_value)  # Add to set of used IDs

                data_entries.append(row)

        # Throw a general error here, in case IDs are not unique
        if len(ids) != len(data_entries):
            raise RuntimeError(errors.ARTICLE_DATA_NO_UNIQUE_IDS,
                               len(data_entries) - len(ids))

        return data_entries

    def _replace_placeholders(self, article_id: str, string: str, data_entry: dict, placeholder_regex: str,
                              escaped_placeholder: str, unescaped_placeholder_regex: str) -> str:
        """
        Replace placeholders in the supplied string and return the result.

        INPUT:
         * article_id: The ID of the article whose data are used for the placeholders
         * string: The string where the placeholders should be replaced
         * data_entry: The dictionary containing the placeholder names as keys and the value to replace them with as value
         * placeholder_regex: The regex which recognizes placeholders
         * escaped_placeholder: The placeholder character escaped with the configured escape character
         * unescaped_placeholder_regex: The regex which recognizes placeholder characters not escaped 
                                        with the configured escape character
        """
        transformed_string = string  # Initialize with the original string

        for placeholder in re.findall(placeholder_regex, string):

            # Remove placeholder character at beginning and end of placeholder
            trimmed_placeholder = placeholder.replace(
                self._config.get_placeholder_character(), '')

            # Fail if placeholder is not specified in the data entries
            if trimmed_placeholder not in data_entry.keys():
                raise RuntimeError(
                    errors.ARTICLE_UNKNOWN_PLACEHOLDER, article_id, placeholder)

            # Escape placeholder characters which are potentially introduced via data entries from the CSV
            placeholder_data = data_entry[trimmed_placeholder].replace(
                self._config.get_placeholder_character(), escaped_placeholder)

            # Actually replace the placeholder
            transformed_string = transformed_string.replace(
                placeholder, placeholder_data)

        # If the placeholders are valid and the placeholder character was used properly or escaped
        # no single placeholders must remain
        unescaped_placeholders = re.findall(
            unescaped_placeholder_regex, transformed_string)

        if len(unescaped_placeholders) > 0:
            raise RuntimeError(errors.ARTICLE_SINGLE_PLACEHOLDER_CHARACTER, article_id, len(
                unescaped_placeholders), self._config.get_placeholder_character())

        # Transform all escaped placeholders back into normal ones
        transformed_string = transformed_string.replace(
            escaped_placeholder, self._config.get_placeholder_character())

        return transformed_string

    def generate_articles(self, template, data_entries):
        """
        Create the articles to upload from the template and article data.

        This is done by filling the placeholders in the template with the data from one entry.
        Each entry in the returned list corresponds to one article.

        INPUT:
            template: The template for the articles to generate as a JSON object
            data_entries: All data from the CSV file to fill the placeholders in the template

        RETURNS: A list containing a 2-tuple with the article data id and
                 the generated article as a JSON object for each article

        The regular expressions and characters to recognize placeholders are constructed with each method call,
        as the characters can be configured to different values for each one, so caching of those is not an option.
        """
        if template is None or data_entries is None:
            raise ValueError("template or data_entries are None")

        #
        # PREPARE THE PLACEHOLDERS/ESCAPED CHARACTERS
        #

        # Escape, as placeholder/escape chars may be reserved regex chars
        regex_escaped_placeholder = re.escape(
            self._config.get_placeholder_character())
        regex_escaped_escape_character = re.escape(
            self._config.get_escape_character())

        # The way a placeholder can be escaped by the user in the template.
        # For example # can be escaped as ~#.
        escaped_placeholder = self._config.get_escape_character() + \
            self._config.get_placeholder_character()

        # Regex to find placeholders. Assume # is the placeholder character, and ~ the escape prefix.
        #
        # (?<!~)# states that a placeholder has to start/end with an unescaped (not starting with ~) #.
        # [A-Za-z0-9_\-\.+? states that the inner part of the placeholder must be alphanumeric or contain _ or . or -.
        placeholder_regex = rf"(?<!{regex_escaped_escape_character}){regex_escaped_placeholder}[A-Za-z0-9_\-\.]+?(?<!{regex_escaped_escape_character}){regex_escaped_placeholder}"

        # Regex to find unescaped placeholders. Assume # as placeholder and ~ as escape prefix.
        # This regex finds all single #, which are not prefixed with ~. So ~# is not matched by the regex, but # is.
        unescaped_placeholder_regex = f"(?<!{regex_escaped_escape_character}){regex_escaped_placeholder}"

        #
        # GENERATE THE ARTICLES
        #

        articles = []
        titles = set()  # Used to validate uniqueness of article titles

        for data_entry in data_entries:

            # Act on a copy, as we use the same template instance for every article
            article = copy.deepcopy(template)

            # Exists by previous validation
            article_id = data_entry[self._config.get_csv_id_header()]

            # Replace placeholders in title and body
            # The article template structure is based on the JSON format documented in
            # https://developer.atlassian.com/server/confluence/confluence-rest-api-examples/
            article["title"] = self._replace_placeholders(
                article_id, article["title"], data_entry, placeholder_regex, escaped_placeholder,
                unescaped_placeholder_regex)
            article["body"]["storage"]["value"] = self._replace_placeholders(
                article_id, article["body"]["storage"]["value"], data_entry, placeholder_regex,
                escaped_placeholder, unescaped_placeholder_regex)

            # Look for existing titles to validate uniqueness
            title = article["title"]

            # Proceed, so the logs contain information about all non-unique titles
            if title in titles:
                errors.ARTICLE_NO_UNIQUE_TITLE.print_message(article_id, title)

            titles.add(title)

            articles.append((article_id, article))

        # Interrupt here in case titles are not unique
        if len(titles) != len(articles):
            raise RuntimeError(errors.ARTICLE_VALIDATION_ERRORS)

        return articles

    def write_errored_articles(self, errored_articles):
        """
        Write the supplied errored articles list to the configured CSV file.

        INPUT:
            errored_articles: A list of CSV rows as a dictionary containing the data entries of one article per row.
                              Must not be None.
        """
        if errored_articles is None:
            raise ValueError("errored_articles must not be None")

        # The newline param is set according to documentation of the module, so newlines are handled correctly
        with open(self._config.get_errored_articles_csv(), 'w', newline='') as file:  # pragma: no cover (not worth for unit testing IMO)

            writer = csv.DictWriter(
                file, delimiter=self._config.get_csv_delimiter(), fieldnames=errored_articles[0].keys())

            writer.writeheader()

            for entry in errored_articles:
                writer.writerow(entry)

    def dump_json(self, json_object: dict, name: str):
        """
        Write the supplied JSON object to a JSON file with the specified name.

        The ./dump/ directory is required to exist.
        """
        with open('dump/' + name + '.json', 'w') as file:
            json.dump(json_object, file)
