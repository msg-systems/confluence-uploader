import unittest
import unittest.mock as mock
from parameterized import parameterized
from test_utils import NON_STRING_TYPE_ELEMENTS_AND_NONE
from cf_uploader.errors import ErrorWrapper


class ErrorsUnitTest(unittest.TestCase):

    UNUSED_ERROR_ID = 1000000  # Set to a value not used for the defined errors

    def tearDown(self):
        # Remove the ID so subsequent tests don't fail when using it again
        ErrorWrapper._used_ids.remove(self.UNUSED_ERROR_ID)

    @parameterized.expand(NON_STRING_TYPE_ELEMENTS_AND_NONE)
    def test_error_wrapper_constructor_invalid_message_type(self, non_string_type_element):
        with self.assertRaises(TypeError):
            ErrorWrapper(self.UNUSED_ERROR_ID, non_string_type_element)

    def test_error_wrapper_used_id(self):
        ErrorWrapper(self.UNUSED_ERROR_ID, "message")  # Now the ID is used

        with self.assertRaises(ValueError):
            ErrorWrapper(self.UNUSED_ERROR_ID, "message2")

    def test_get_message(self):
        """Do not test more, as this only delegates to .format()"""
        wrapper = ErrorWrapper(self.UNUSED_ERROR_ID, "Message: {0}, {1}.")

        self.assertEqual("Message: 23.5, cderfv.",
                         wrapper.get_message(23.5, "cderfv"))

    @mock.patch('cf_uploader.logger.error_logger.error')
    def test_print_message(self, mock_error_logger):
        """Only test the delegation to the error logger, not .format()"""
        wrapper = ErrorWrapper(self.UNUSED_ERROR_ID, "Error Message: {0}-")

        wrapper.print_message("arg")

        mock_error_logger.assert_called_with(
            "Error Message: arg-", extra={'error_id': self.UNUSED_ERROR_ID})

    @mock.patch('sys.exit')
    @mock.patch('cf_uploader.logger.error_logger.error')
    def test_print_message_and_exit(self, mock_error_logger, mock_sys_exit):

        wrapper = ErrorWrapper(self.UNUSED_ERROR_ID, "MSG: {0}")

        wrapper.print_message_and_exit("msg")

        mock_error_logger.assert_called_with(
            "MSG: msg", extra={'error_id': self.UNUSED_ERROR_ID})
        mock_sys_exit.assert_called_with(1)
