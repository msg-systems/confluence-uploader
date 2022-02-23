"""This module provides configured loggers for the program."""
import logging

# This logger should be used in most cases
main_logger = logging.getLogger('main_logger')
main_logger.setLevel(logging.INFO)

main_logger_file_handler = logging.FileHandler('logs.log', mode='w')
main_logger_file_handler.setLevel(logging.DEBUG)

main_logger_console_handler = logging.StreamHandler()
main_logger_console_handler.setLevel(logging.INFO)

main_logger_formatter = logging.Formatter(
    '[{asctime}] [{levelname}]: {message}', style='{', datefmt='%Y-%m-%d %H:%M:%S')
main_logger_console_handler.setFormatter(main_logger_formatter)
main_logger_file_handler.setFormatter(main_logger_formatter)

main_logger.addHandler(main_logger_file_handler)
main_logger.addHandler(main_logger_console_handler)

# This logger should be used for logging error messages from the errors module, as it has native support for logging the error id
error_logger = logging.getLogger('error_logger')
error_logger.setLevel(logging.ERROR)

error_logger_file_handler = logging.FileHandler('logs.log')
error_logger_file_handler.setLevel(logging.DEBUG)

error_logger_console_handler = logging.StreamHandler()
error_logger_console_handler.setLevel(logging.INFO)

# error_id has to be supplied via the extra kwargs
error_logger_formatter = logging.Formatter(
    '[{asctime}] [{levelname} {error_id}]: {message}', style='{', datefmt='%Y-%m-%d %H:%M:%S')
error_logger_console_handler.setFormatter(error_logger_formatter)
error_logger_file_handler.setFormatter(error_logger_formatter)

error_logger.addHandler(error_logger_file_handler)
error_logger.addHandler(error_logger_console_handler)
