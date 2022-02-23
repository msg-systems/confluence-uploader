import sys
import unittest
import unittest.mock as mock
import cf_uploader.application as application


class ApplicationTest(unittest.TestCase):

    def setUp(self):
        self._config = mock.Mock()
        self._config.load = mock.Mock()

    @mock.patch("cf_uploader.config.Config")
    @mock.patch("cf_uploader.errors.CONFIG_INVALID_STRUCTURE.print_message_and_exit")
    def test_invalid_config_structure(self, program_exit_hook, config_constructor_mock):
        config_constructor_mock.return_value = self._config

        self._config.load.side_effect = KeyError(
            "Invalid config file structure")
        program_exit_hook.side_effect = lambda: sys.exit(
            0)  # Still exit the method

        with self.assertRaises(SystemExit):
            application.main()

        self._config.load.assert_called()
        program_exit_hook.assert_called()

    @mock.patch("cf_uploader.config.Config")
    @mock.patch("builtins.input")
    @mock.patch("getpass.getpass")
    def test_validate_all_called_in_headless_mode(self, getpass_mock, input_mock, config_constructor_mock):
        self._config.get_user_gui.return_value = False  # headless mode

        config_constructor_mock.return_value = self._config

        # Stop here, as the thing we wanted to test did happen
        self._config.validate_all.side_effect = lambda: sys.exit(0)

        # Catch the SystemExit we did throw in the test
        with self.assertRaises(SystemExit):
            application.main()

        self._config.validate_all.assert_called()
