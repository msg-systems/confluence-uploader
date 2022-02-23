"""This module encapsulates access to the Confluence API. It provides functions to retrieve and modify articles."""

import json
import time
import copy
import requests
from requests.exceptions import SSLError
from requests.auth import HTTPBasicAuth
from requests.structures import CaseInsensitiveDict

from . import config
from . import errors
from .logger import main_logger


class ConfluenceAPI:
    """
    A class encapsulating the access to the Confluence API.

    The API usage is based on https://developer.atlassian.com/server/confluence/confluence-rest-api-examples/.
    """

    def __init__(self, configuration: config.Config):
        """Assign the configuration object."""
        self._config = configuration

    def _get_response_message(self, response: requests.Response) -> str:
        """Try to extract a message/an error message from a HTTP response."""
        # Content is binary, decode as UTF-8 string
        response_string = response.content.decode("UTF-8")

        # First try to parse it as a Confluence API response
        try:
            return str(json.loads(response_string)["message"])
        except (TypeError, KeyError, ValueError):
            # No JSON or in a format we don't understand, so just return the whole response as a string
            return response_string

    def _confluence_request(self, request_function, url_to_access: str, *error_args, success_message: str | None = None, error: errors.ErrorWrapper | None = None) -> requests.Response | None:
        """
        Handle a response from Confluence - either display a success or error message.

        Params:
         * request_function: A no-arg function executing the HTTP request, returning the HTTP response
         * url_to_access: The URL the request function tries to access
         * error_args: Arguments sent to the supplied error message in case it it print
         * success_message: A message to print on success, either a str or None (in that case nothing is printed)
         * error: An error wrapper whose message should be printed with the supplied error_args if an error does occur.
                  Can be None.

        Return the HTTP response on success, else None.
        """
        try:
            response = request_function()
        except SSLError as ssl_error:
            raise RuntimeError(errors.SSL_ERROR, url_to_access) from ssl_error

        # Wait a bit, so the API is not spammed for subsequent requests
        time.sleep(self._config.get_api_interaction_delay_seconds())

        if response.status_code != 200:  # The API calls used here return 200 on success, nothing else

            main_logger.error("Got a response '%s' with status code %d",
                              self._get_response_message(response), response.status_code)

            if error is not None:
                error.print_message(url_to_access, *error_args)

            return None
        else:  # Success message

            if success_message is not None:
                main_logger.info(success_message)

            return response

    def _delete_keys_except(self, entries: dict, *key_whitelist):
        """Delete all keys from the supplied dict except the ones in the whitelist."""
        keys_to_delete = [
            key for key in entries.keys() if key not in key_whitelist]

        for key in keys_to_delete:
            entries.pop(key)

    def _process_template(self, template_url: str, template: dict):
        """
        Modifiy the JSON structure of the supplied template, so unnecessary stuff is removed, and custom content is added.

        This function acs on a copy of the supplied template, and returns the processed one.
        """
        # Don't modify the original template object
        processed_template = copy.deepcopy(template)

        try:
            # Remove everything but the entries we really need
            # This fails with a key error if the structure is different than expected
            self._delete_keys_except(processed_template, "title",
                                     "body", "type", "space")
            self._delete_keys_except(processed_template["space"], "key")
            self._delete_keys_except(processed_template["body"], "storage")
            self._delete_keys_except(
                processed_template["body"]["storage"], "value", "representation")

            # Assign a parent article, if present in the configs
            if self._config.get_upload_parent_page() is not None:
                processed_template["ancestors"] = [
                    {"id": self._config.get_upload_parent_page()}]
        except KeyError as key_error:
            raise RuntimeError(errors.CONFLUENCE_TEMPLATE_PROCESSING_FAILED,
                               self._config.get_template_id(), template_url) from key_error

        return processed_template

    def _create_auth(self):
        return HTTPBasicAuth(self._config.get_username(), self._config.get_token())

    def retrieve_template(self) -> dict:
        """
        Download the configured template from Confluence and processes it, so it can be used as a base for the articles.

        Return the downloaded and processed template as JSON object on success, otherwise an error is raised.
        """
        # Expand so we get the actual site content and space information
        rest_request_url = self._config.get_base_url() + \
            self._config.get_template_id() + "?expand=body.storage,space"

        # Use HTTP GET with basic auth for accessing existing page
        def request_function():
            return requests.get(
                rest_request_url, auth=self._create_auth())

        response = self._confluence_request(request_function, rest_request_url)

        if response is not None:
            return self._process_template(rest_request_url, response.json())
        else:
            # Raise an error, as failing to download the template means the whole program cannot proceed
            raise RuntimeError(errors.CONFLUENCE_DOWNLOAD_FAILED,
                               rest_request_url, self._config.get_template_id())

    def exists(self, page_title: str) -> tuple | None:
        """
        Check whether a page with the supplied title exists in the configured upload space.

        Returns None if not, otherwise a tuple consisting of the page ID and the current version number is returned.
        """
        if page_title is None:
            raise TypeError("page_title most not be None")

        # Search by title, space and limit to one result, as we're checking existence
        rest_request_url = self._config.get_base_url() + "?title="+page_title + \
            "&spaceKey="+self._config.get_upload_space() + "&limit=1&expand=version"

        # Use HTTP GET for searching/retrieving
        def request_function():
            return requests.get(rest_request_url, auth=self._create_auth())

        response = self._confluence_request(request_function, rest_request_url, page_title,
                                            error=errors.CONFLUENCE_EXISTENCE_CHECK_FAILED)

        try:
            # Assuming the response is in the format as documented
            response_json = response.json()

            size = response_json["size"]

            if int(size) > 0:  # One or more results are returned
                # Page ID of first result
                page_id = response_json["results"][0]["id"]

                if page_id is not None:
                    # Return article id and current version number
                    return page_id, int(response_json["results"][0]["version"]["number"])

        except (requests.JSONDecodeError, KeyError, ValueError, AttributeError, IndexError) as exception:
            main_logger.warning(exception, exc_info=True)
            main_logger.warning(
                "WARNING: Could not extract from the API response whether the article with title '%s' exists", page_title)

    def _upload_page(self, page_id: str, json_to_upload: dict) -> bool:
        """Upload a page to Confluence, assuming it doesn't exist. Return whether it was successful."""
        request_url = self._config.get_base_url()

        headers = CaseInsensitiveDict()
        headers["Content-Type"] = "application/json"

        # Use HTTP POST for creating a new page
        def request_function():
            return requests.post(request_url, auth=self._create_auth(),
                                 data=json.dumps(json_to_upload), headers=headers)

        response = self._confluence_request(request_function, request_url, page_id,
                                            success_message=f"Successfully uploaded the article '{page_id}'",
                                            error=errors.CONFLUENCE_UPLOAD_FAILED)

        return response is not None

    def _update_page(self, article_data_id: str, confluence_page_id: str, new_version_number: int, json_to_upload: dict) -> bool:
        """Replace the content of an existing page and increment the version number. Return True upon success."""
        # Some more entries have to be added to request - to not modify the original JSON
        update_page_json = copy.deepcopy(json_to_upload)

        # The base URL ends with a slash
        request_url = self._config.get_base_url() + confluence_page_id

        # Add the ID of the page to update, and an incremented version number (required by the Confluence API)
        update_page_json["id"] = confluence_page_id
        update_page_json["version"] = {"number": str(new_version_number)}

        headers = CaseInsensitiveDict()
        headers["Content-Type"] = "application/json"

        # Use HTTP PUT for updating
        def request_function():
            return requests.put(request_url, auth=self._create_auth(),
                                data=json.dumps(update_page_json), headers=headers)

        response = self._confluence_request(request_function, request_url, article_data_id, confluence_page_id,
                                            success_message=f"Successfully uploaded the article generated from the article data '{article_data_id}'",
                                            error=errors.CONFLUENCE_UPDATE_FAILED)

        return response is not None

    def upload_article(self, article_data_id: str, json_to_upload: dict) -> bool:
        """
        Upload article data to Confluence, this possibly replaces existing articles, depending on the configuration.

        INPUT:
            id: The internal data entry ID to track uploaded articles. It must not be None.
            json_to_upload: The article JSON to upload. It must not be None.

        RETURNS: True upon success, otherwise False
        """
        if article_data_id is None or json_to_upload is None:
            raise TypeError(
                "article_data_id and json_to_upload must not be None")

        page_title = json_to_upload["title"]

        if self._config.get_overwrite_existing_articles():
            exists_result = self.exists(page_title)

            if exists_result is not None:
                main_logger.info(
                    "A site with the title '%s' already exists - it will be overwritten", page_title)

                # Increment the version number
                return self._update_page(article_data_id, exists_result[0], exists_result[1] + 1, json_to_upload)

        return self._upload_page(article_data_id, json_to_upload)
