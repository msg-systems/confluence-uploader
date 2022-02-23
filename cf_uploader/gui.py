"""This module provides the GUI components for the program."""
import tkinter as tk
import tkinter.tix as tix
from tkinter import filedialog
from tkinter import ttk
from tkinter import messagebox
import sys
import os
import threading
import logging
from logging import Formatter, StreamHandler
from . import config as configuration
from . import logger
from . import constants
from . import validation


class GuiLogHandler(StreamHandler):
    """A log handler which logs into a tkinter.Text component. Uses a supplied formatter."""

    def __init__(self, console_component: tk.Text, formatter: Formatter):
        """Initialize the handler with the supplied GUI component and logger formatter."""
        StreamHandler.__init__(self)  # Parent constructor

        self.console_component = console_component
        self.setFormatter(formatter)

    def emit(self, record):
        """Redirect the logged record to the console component."""
        message = self.format(record) + "\n"  # One message per line

        # Make text component writeable
        self.console_component['state'] = 'normal'

        self.console_component.insert('end', message)  # Add message
        self.console_component.see('end')  # Scroll down to message

        # Color error or warning messages
        if record.levelno in (logging.ERROR, logging.WARNING):

            # Retrieve line index of current message.
            #
            #   1.) 'end' is the index of the character after the currently logged message
            #   2.) Extract the line index of it (the part in front of the dot)
            #   3.) Shift by -2, as 'end' indexes the line after the new line after this message.

            end_index_string = str(
                float(self.console_component.index('end'))-2).split(".", maxsplit=1)[0]

            # Make format tag name unique per message
            format_tag_name = "line" + end_index_string

            # Apply tag to whole logged message (from first to last char)
            self.console_component.tag_add(
                format_tag_name, end_index_string+".0", end_index_string+".end")

            # The tag colors the message
            self.console_component.tag_config(
                format_tag_name, foreground="red" if record.levelno == logging.ERROR else "orange")

        self.console_component['state'] = 'disabled'  # Make read-only again


class ConsoleDialog:
    """This class models the dialog where the console output is redirected into."""

    def __init__(self, parent, task_thread: threading.Thread):
        """
        Initialize the console dialog with the specified constructor arguments.

         * parent: Parent window
         * task_thread: The thread which runs a task whose output is relayed into this window.
           While the task runs, the window cannot be closed.
        """
        self.parent = tk.Toplevel(parent)
        self.task_thread = task_thread

        self.parent.resizable(True, True)  # Resizable in both dimensions
        self.parent.grab_set()  # Make the dialog application modal

        self.vertical_scroll_bar = tk.Scrollbar(self.parent)
        self.horizontal_scroll_bar = tk.Scrollbar(
            self.parent, orient=tk.HORIZONTAL)

        self.console_text_area = tk.Text(
            self.parent, height=25, width=100, wrap=tk.NONE, yscrollcommand=self.vertical_scroll_bar.set,
            xscrollcommand=self.horizontal_scroll_bar.set)
        # Make console component read-only
        self.console_text_area['state'] = 'disabled'

        self.vertical_scroll_bar['command'] = self.console_text_area.yview
        self.horizontal_scroll_bar['command'] = self.console_text_area.xview

        self.vertical_scroll_bar.pack(side=tk.RIGHT, fill=tk.Y)
        self.horizontal_scroll_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.console_text_area.pack(fill=tk.BOTH, expand=True)

        # Create handlers which write logs into the log window
        main_gui_log_handler = GuiLogHandler(
            self.console_text_area, logger.main_logger_formatter)

        error_gui_log_handler = GuiLogHandler(
            self.console_text_area, logger.error_logger_formatter)

        logger.main_logger.addHandler(main_gui_log_handler)
        logger.error_logger.addHandler(error_gui_log_handler)

        # Remove handlers when closing the log window
        def onclose():

            # Only close when task is finished
            if not self.task_thread.is_alive():
                logger.main_logger.removeHandler(main_gui_log_handler)
                logger.error_logger.removeHandler(error_gui_log_handler)
                self.parent.destroy()

        self.parent.protocol("WM_DELETE_WINDOW", onclose)


def _validate(tooltip_component: tix.Balloon, validation_function, text, validation_component: tk.Widget) -> bool:
    """
    Perform validation of the supplied component.

     * tooltip_component: A tix.Balloon component displaying a validation error message
     * validation_function: A function accepting a string, which returns an error wrapper object
                            for validation errorS occurred. Performs the actual validation.
     * text: The value to be validated
     * validation_component: The widget whose content (probably the 'text' variable) will be validated

    Return true if 'text' is seen as valid, otherwise false.
    """
    validation_result = validation_function(text)  # Perform validation

    if validation_result is None or validation_component['state'] == 'disabled':
        # No validation error occurred

        validation_component.config(
            highlightthickness=0)  # Remove highlight order
        tooltip_component.unbind_widget(validation_component)  # Remove tooltip
        return True
    else:
        # A validation error was found

        # Add red border around component
        validation_component.config(highlightthickness=2,
                                    highlightbackground="red", highlightcolor="red")

        # Set tooltip for component to error message
        tooltip_component.bind_widget(
            validation_component, balloonmsg=validation_result.get_message(text))
        return False


def _validatecommand(parent_component, tooltip_component: tix.Balloon, validation_component_lambda, validation_function, validation_function_list):
    """
    Transform the supplied arguments into a format which the 'validatecommand' config option of tkinter widgets accepts.

     * parent_component: The parent component, for example the enclosing window.
     * tooltip_component: See _validate
     * validation_component_lambda: A function without arguments which returns the validation component.
                                    See _validate for it's meaning.
     * validation_function: See _validate.
     * validation_function_list: A list collecting a 2-tuple with the first entry being
                                 a function accepting a string to be validated, which returns true or false,
                                 depending on whether it's valid or not. The function can also perform actions on the GUI.
                                 The second entry is 'validation_component_lambda'.
                                 This function adds one such tuple per call to that list.

    Returns: A tuple with the first entry being a tkinter-registered validation function name and the second being '%P'.
    """

    def full_validation_function(text):
        return _validate(tooltip_component, validation_function, text, validation_component_lambda())

    validation_function_list.append(
        (full_validation_function, validation_component_lambda))

    return (parent_component.register(full_validation_function), '%P')


def _validate_form(form_components) -> bool:
    """
    Iterate through the supplied list and perform a validation for each entry.

     * form_components: A list containing tuples in the format as described in
                        '_validatecommand' for 'validation_function_list'.

    If validation errors are found, return false and show an error message dialog.
    """
    validation_errors = 0

    for validation_function, validation_component_lambda in form_components:
        # Perform validation
        if not validation_function(validation_component_lambda().get()):
            validation_errors += 1

    if validation_errors > 0:
        messagebox.showerror(
            'Error:', f'{validation_errors} validation errors were found. Cannot proceed until those are fixed.')
        return False

    return True


class CredentialsDialog:
    """A dialog for setting the confluence login credentials."""

    OPEN_LOCK_CHARACTER = '\U0001F513'
    CLOSED_LOCK_CHARACTER = '\U0001F512'

    def _validatecommand(self, validation_function, validation_component_lambda):
        """A version of the module function '_validatecommand' with the tooltip, parent component and validation functions list already inserted."""
        return _validatecommand(self.parent, self.tooltip, validation_component_lambda, validation_function, self._validation_functions)

    def __init__(self, parent, config: configuration.Config):
        """Initialize the credentials dialog."""
        self._validation_functions = []

        self.parent = tk.Toplevel(parent)
        self._config = config

        # Make resizable in both dimensions
        self.parent.resizable(False, False)
        self.parent.grab_set()  # Make application modal

        # Used for displaying all the validation tooltips
        self.tooltip = tix.Balloon(self.parent)

        self.username_label = tk.Label(
            self.parent, text="Confluence username:")
        self.username_var = tk.StringVar()
        self.username_textfield = tk.Entry(
            self.parent, textvariable=self.username_var, validate="focus", validatecommand=self._validatecommand(
                validation.validate_username, lambda: self.username_textfield))

        self.token_label = tk.Label(self.parent, text="Confluence API token:")
        self.token_var = tk.StringVar()
        self.token_textfield = tk.Entry(
            self.parent, textvariable=self.token_var, show="*", validate="focus", validatecommand=self._validatecommand(
                validation.validate_token, lambda: self.token_textfield))
        self.show_token_button = tk.Button(
            self.parent, text=self.CLOSED_LOCK_CHARACTER, relief='raised', command=self.show_token_button_listener)

        self.save_button = tk.Button(
            self.parent, text="Save", command=self.save)
        self.cancel_button = tk.Button(
            self.parent, text="Cancel", command=self.cancel)

        # Layout
        self.username_label.grid(column=0, row=0, padx=5, pady=2, sticky="W")
        self.username_textfield.grid(
            column=1, row=0, padx=5, pady=2, sticky="W")

        self.token_label.grid(column=0, row=1, padx=5, pady=2, sticky="W")
        self.token_textfield.grid(column=1, row=1, padx=5, pady=2, sticky="W")
        self.show_token_button.grid(
            column=2, row=1, padx=5, pady=2, sticky="W")

        self.save_button.grid(
            column=0, row=2, padx=5, pady=2, sticky="WE", columnspan=1)
        self.cancel_button.grid(
            column=1, row=2, padx=5, pady=2, sticky="WE", columnspan=1)

        # Initialize components with config values
        self.username_var.set(config.get_username())
        self.token_var.set(config.get_token())

    def show_token_button_listener(self):
        """Toggle between showing the token or stars in the token textfield."""
        # Emulate a toggle button component
        # When in pressed state
        if self.show_token_button.config('relief')[-1] == 'sunken':

            # Don't show token
            self.show_token_button.config(
                text=self.CLOSED_LOCK_CHARACTER)  # Show closed lock icon
            self.show_token_button.config(relief="raised")
            self.token_textfield.config(show='*')  # Obscure token
        else:

            # Show token
            self.show_token_button.config(
                text=self.OPEN_LOCK_CHARACTER)  # Show open lock icon
            self.show_token_button.config(relief="sunken")
            self.token_textfield.config(show='')  # Show token

    def save(self):
        """Synchronize the dialog properties (if valid) with the configuration."""
        # Only save when everything is valid
        if not _validate_form(self._validation_functions):
            return

        # Set config to values in GUI and save
        self._config.set_username(self.username_var.get())
        self._config.set_token(self.token_var.get())

        self.parent.destroy()  # Close dialog

    def cancel(self):
        """Close without saving."""
        self.parent.destroy()


class Gui:
    """This class models the main window of the application."""

    def _validatecommand(self, validation_function, validation_component_lambda):
        """A version of the module function '_validatecommand' with the tooltip, parent component and validation functions list already inserted."""
        return _validatecommand(self.frame, self.tooltip, validation_component_lambda, validation_function, self._validation_functions)

    def __init__(self, config: configuration.Config, process_function):
        """
        Construct the main window.

         * process_function: A function with no arguments, returning one of the status codes defined in the constants module. Performs the main functionality of the program.
        """
        self._validation_functions = []

        self._config = config
        self.process_function = process_function

        # Configure main frame
        self.frame = tix.Tk()
        self.frame.title("Confluence Uploader")
        self.frame.protocol('WM_DELETE_WINDOW', self.close)  # Close-listener
        self.frame.resizable(False, False)

        # Menu bar
        self.menubar = tk.Menu(self.frame)
        self.file_menu = tk.Menu(self.menubar, tearoff=0)
        self.help_menu = tk.Menu(self.menubar, tearoff=0)

        self.file_menu.add_command(label="Exit", command=self.close)

        self.help_menu.add_command(label="Help", command=self.help_menu_action)
        self.help_menu.add_separator()
        self.help_menu.add_command(
            label="About", command=self.about_menu_action)

        self.menubar.add_cascade(label="File", menu=self.file_menu)
        self.menubar.add_cascade(label="Help", menu=self.help_menu)

        self.frame.config(menu=self.menubar)

        #
        # UI components
        #

        # Used for displaying all the validation tooltips
        self.tooltip = tix.Balloon(self.frame)

        self.base_url_label = tk.Label(self.frame, text="Base URL:")
        self.base_url_textfield_var = tk.StringVar()
        self.base_url_textfield = tk.Entry(
            self.frame, textvariable=self.base_url_textfield_var, validate="focus", validatecommand=self._validatecommand(
                validation.validate_base_url, lambda: self.base_url_textfield))

        self.template_id_label = tk.Label(self.frame, text="Template ID:")
        self.template_id_textfield_var = tk.StringVar()
        self.template_id_textfield = tk.Entry(
            self.frame, textvariable=self.template_id_textfield_var, validate="focus", validatecommand=self._validatecommand(
                validation.validate_template_id, lambda: self.template_id_textfield))

        self.template_placeholder_character_label = tk.Label(
            self.frame, text="Placeholder character:")
        self.template_placeholder_character_var = tk.StringVar()
        self.template_placeholder_character_textfield = tk.Entry(
            self.frame, textvariable=self.template_placeholder_character_var, validate="focus", validatecommand=self._validatecommand(
                lambda placeholder: validation.validate_placeholder_character(placeholder, self._config.get_escape_character()), lambda: self.template_placeholder_character_textfield))

        self.template_escape_character_label = tk.Label(
            self.frame, text="Escape character:")
        self.template_escape_character_var = tk.StringVar()
        self.template_escape_character_textfield = tk.Entry(
            self.frame, textvariable=self.template_escape_character_var, validate="focus", validatecommand=self._validatecommand(
                lambda escape: validation.validate_escape_character(escape, self._config.get_placeholder_character()), lambda: self.template_escape_character_textfield))

        self.upload_space_label = tk.Label(self.frame, text="Upload space:")
        self.upload_space_var = tk.StringVar()
        self.upload_space_textfield = tk.Entry(
            self.frame, textvariable=self.upload_space_var, validate="focus", validatecommand=self._validatecommand(validation.validate_upload_space, lambda: self.upload_space_textfield))

        self.upload_parent_page_id_checkbox_var = tk.BooleanVar()
        self.upload_parent_page_id_checkbox = tk.Checkbutton(
            self.frame, text="Upload pages as children of a parent page", command=self.upload_parent_page_id_checkbox_listener, var=self.upload_parent_page_id_checkbox_var)

        self.upload_parent_page_id_label = tk.Label(
            self.frame, text="Parent page ID:")
        self.upload_parent_page_id_var = tk.StringVar()
        self.upload_parent_page_id_textfield = tk.Entry(
            self.frame, state='disabled', textvariable=self.upload_parent_page_id_var, validate="focus", validatecommand=self._validatecommand(validation.validate_parent_page_id, lambda: self.upload_parent_page_id_textfield))

        self.overwrite_existing_articles_checkbox_var = tk.BooleanVar()
        self.overwrite_existing_articles_checkbox = tk.Checkbutton(
            self.frame, text="Overwrite existing articles", var=self.overwrite_existing_articles_checkbox_var)

        self.data_csv_path_label = tk.Label(self.frame, text="Data CSV path:")
        self.data_csv_path_var = tk.StringVar()
        self.data_csv_path_textfield = tk.Entry(
            self.frame, textvariable=self.data_csv_path_var, validate="focus", validatecommand=self._validatecommand(validation.validate_article_data_csv, lambda: self.data_csv_path_textfield))
        self.data_csv_path_browse_button = tk.Button(
            self.frame, text="Browse", command=self.choose_data_file)

        self.data_csv_delimiter_label = tk.Label(
            self.frame, text="CSV delimiter:")
        self.data_csv_delimiter_var = tk.StringVar()
        self.data_csv_delimiter_textfield = tk.Entry(
            self.frame, textvariable=self.data_csv_delimiter_var, validate="focus", validatecommand=self._validatecommand(validation.validate_csv_delimiter, lambda: self.data_csv_delimiter_textfield))

        self.data_csv_id_column_header_label = tk.Label(
            self.frame, text="ID column header:")
        self.data_csv_id_column_header_var = tk.StringVar()
        self.data_csv_id_column_header_textfield = tk.Entry(
            self.frame, textvariable=self.data_csv_id_column_header_var, validate="focus", validatecommand=self._validatecommand(validation.validate_csv_id_column_header, lambda: self.data_csv_id_column_header_textfield))

        self.credentials_label = tk.Label(
            self.frame, text="Confluence credentials:")
        self.credentials_button = tk.Button(
            self.frame, text="Manage", command=self.manage_credentials_button_listener)

        self.process_and_upload_button = tk.Button(
            self.frame, text="Create and upload pages", command=self.process_and_upload_button_action)

        #
        # Initialize component values from config
        #

        self.base_url_textfield_var.set(config.get_base_url())
        self.template_id_textfield_var.set(config.get_template_id())
        self.template_placeholder_character_var.set(
            config.get_placeholder_character())
        self.template_escape_character_var.set(config.get_escape_character())
        self.upload_space_var.set(config.get_upload_space())

        self.upload_parent_page_id_checkbox_var.set(
            config.get_upload_parent_page() is not None)

        if config.get_upload_parent_page() is not None:
            self.upload_parent_page_id_textfield.configure(
                state=tk.NORMAL)  # Make textfield writeable
            self.upload_parent_page_id_var.set(config.get_upload_parent_page())

        self.overwrite_existing_articles_checkbox_var.set(
            config.get_overwrite_existing_articles())

        self.data_csv_path_var.set(config.get_article_data_csv())
        self.data_csv_delimiter_var.set(config.get_csv_delimiter())
        self.data_csv_id_column_header_var.set(config.get_csv_id_header())

        #
        # Layout components
        #

        row_counter = 0

        # Adds a horizintal line and increments the row counter
        def add_separator():
            nonlocal row_counter

            row_counter += 1

            ttk.Separator(self.frame).grid(
                column=0, row=row_counter, sticky="WE", columnspan=3, pady=7)

            row_counter += 1

        add_separator()

        self.base_url_label.grid(
            column=0, row=row_counter, padx=5, pady=2, sticky="W")
        self.base_url_textfield.grid(
            column=1, row=row_counter, padx=5, pady=2, sticky="W")

        row_counter += 1

        add_separator()

        self.template_id_label.grid(
            column=0, row=row_counter, padx=5, pady=2, sticky="W")
        self.template_id_textfield.grid(
            column=1, row=row_counter, padx=5, pady=2, sticky="W")

        row_counter += 1

        self.template_placeholder_character_label.grid(
            column=0, row=row_counter, padx=5, pady=2, sticky="W")
        self.template_placeholder_character_textfield.grid(
            column=1, row=row_counter, padx=5, pady=2, sticky="W")

        row_counter += 1

        self.template_escape_character_label.grid(
            column=0, row=row_counter, padx=5, pady=2, sticky="W")
        self.template_escape_character_textfield.grid(
            column=1, row=row_counter, padx=5, pady=2, sticky="W")

        add_separator()

        self.upload_space_label.grid(
            column=0, row=row_counter, padx=5, pady=2, sticky="W")
        self.upload_space_textfield.grid(
            column=1, row=row_counter, padx=5, pady=2, sticky="W")

        row_counter += 1

        self.upload_parent_page_id_checkbox.grid(
            column=0, row=row_counter, padx=5, pady=2, sticky="W", columnspan=3)

        row_counter += 1

        self.upload_parent_page_id_label.grid(
            column=0, row=row_counter, padx=5, pady=2, sticky="W")
        self.upload_parent_page_id_textfield.grid(
            column=1, row=row_counter, padx=5, pady=2, sticky="W")

        add_separator()

        self.overwrite_existing_articles_checkbox.grid(
            column=0, row=row_counter, padx=5, pady=2, sticky="W", columnspan=3)

        add_separator()

        self.data_csv_path_label.grid(
            column=0, row=row_counter, padx=5, pady=2, sticky="W")
        self.data_csv_path_textfield.grid(
            column=1, row=row_counter, padx=5, pady=2, sticky="W")
        self.data_csv_path_browse_button.grid(
            column=2, row=row_counter, padx=5, pady=2, sticky="W")

        row_counter += 1

        self.data_csv_delimiter_label.grid(
            column=0, row=row_counter, padx=5, pady=2, sticky="W")
        self.data_csv_delimiter_textfield.grid(
            column=1, row=row_counter, padx=5, pady=2, sticky="W")

        row_counter += 1

        self.data_csv_id_column_header_label.grid(
            column=0, row=row_counter, padx=5, pady=2, sticky="W")
        self.data_csv_id_column_header_textfield.grid(
            column=1, row=row_counter, padx=5, pady=2, sticky="W")

        add_separator()

        self.credentials_label.grid(
            column=0, row=row_counter, padx=5, pady=2, sticky="W")
        self.credentials_button.grid(
            column=1, row=row_counter, padx=5, pady=2, sticky="WE")

        row_counter += 1

        add_separator()

        self.process_and_upload_button.grid(
            column=0, row=row_counter, padx=5, pady=8, sticky="WE", columnspan=3)

    def upload_parent_page_id_checkbox_listener(self):
        """
        Make the associated textfield writeable or read-only, according to the checkbox state.

        Delete content of the textfield, when unchecked.
        """
        if self.upload_parent_page_id_checkbox_var.get():
            self.upload_parent_page_id_textfield.configure(
                state=tk.NORMAL)  # Make textfield writeable
        else:
            self.upload_parent_page_id_textfield.delete(
                first=0, last="end")  # Delete content
            self.upload_parent_page_id_textfield.configure(
                state='disabled')  # Make textfield read-only again

    def choose_data_file(self):
        """Open a filechooser when the user clicks the browse button."""
        chosen_file = filedialog.askopenfilename(title="Select the data file:", filetypes=[
            ("CSV files:", [".csv"]), ("All files", ["*.*"])])  # Open file chooser

        try:

            # Try to make the path relative for better readability
            processed_path = os.path.relpath(chosen_file)
        except ValueError:

            # Under Windows this error is raised if working dir and file are on different drives
            processed_path = os.path.abspath(chosen_file)

        # Set new dir
        if chosen_file is not None and chosen_file.strip() != "":
            self.data_csv_path_var.set(processed_path)

    def help_menu_action(self):
        """Display the help dialog."""
        messagebox.showinfo(
            'Help:', 'You can find help documents in README.md and ./docs/. Additionally,\
                      you can contact the author of the program via florian-f.haas@msg.group.')

    def about_menu_action(self):
        """Display the about dialog."""
        messagebox.showinfo('About the Confluence Uploader:',
                            'Author: Florian Haas\nE-Mail: florian-f.haas@msg.group\nWritten in 2021/22 at msg systems ag.')

    def manage_credentials_button_listener(self):
        """Display the credentials dialog and wait until it is closed."""
        dialog = CredentialsDialog(self.frame, self._config)
        self.frame.wait_window(dialog.parent)

    def validate_and_save(self) -> bool:
        """
        Validate components in wthe main window, and assign their values to the config module and saves them, if valid.

        Returns true when valid, otherwise false.
        """
        # Only save if valid
        if not _validate_form(self._validation_functions):
            return False

        self._config.set_base_url(self.base_url_textfield_var.get())
        self._config.set_template_id(self.template_id_textfield_var.get())
        self._config.set_placeholder_character(
            self.template_placeholder_character_var.get())
        self._config.set_escape_character(
            self.template_escape_character_var.get())
        self._config.set_upload_space(self.upload_space_var.get())
        self._config.set_upload_parent_page(None if not self.upload_parent_page_id_checkbox_var.get(
        ) else self.upload_parent_page_id_var.get())
        self._config.set_overwrite_existing_articles(
            self.overwrite_existing_articles_checkbox_var.get())
        self._config.set_article_data_csv(self.data_csv_path_var.get())
        self._config.set_csv_delimiter(self.data_csv_delimiter_textfield.get())
        self._config.set_csv_id_header(
            self.data_csv_id_column_header_var.get())

        self._config.save_uploader_config()

        return True

    def process_and_upload_button_action(self):
        """Run the main part of the program."""
        # First check whether configured values are valid
        if not self.validate_and_save():
            return

        # If credentials are not valid, open the dialog, so the user can input valid ones
        if validation.validate_username(self._config.get_username()) is not None or validation.validate_token(self._config.get_token()) is not None:
            dialog = CredentialsDialog(self.frame, self._config)
            self.frame.wait_window(dialog.parent)
            return

        # Helper function for the task to be executed
        def task():
            status = self.process_function(
                self._config)  # Run main part of program

            # After that, display a result to the user, according to the status code
            if status == constants.NO_ERRORS:
                messagebox.showinfo(
                    'Information:', 'Successfully generated and uploaded the articles to confluence.')
            elif status == constants.MINOR_ERRORS:
                messagebox.showwarning(
                    'Warning:', 'Some errors occurred when generating and uploading articles to confluence.')
            elif status == constants.FATAL_ERRORS:
                messagebox.showerror(
                    'Error:', 'A fatal error occurred when generating and uploading articles to confluence.')

        # Run task in thread, so UI is not blocked
        th = threading.Thread(target=task)
        th.daemon = True  # Stop task thread if main thread is stopped

        ConsoleDialog(self.frame, th)  # Open console window

        th.start()

    def close(self):
        """Terminate the application after asking for configuration."""
        result = messagebox.askyesnocancel(
            'Confirmation:', 'Do you want to save unsaved configuration changes?')

        if result is not None:  # No cancel

            if result and not self.validate_and_save():  # Result is true, thus save
                return

            self.frame.destroy()
            sys.exit(0)

    def show(self):
        """Block until the window is closed."""
        self.frame.mainloop()


def create_gui(config, process_function):
    """Return a new instance of the GUI. Currently only a wrapper for a constructor call."""
    return Gui(config, process_function)
