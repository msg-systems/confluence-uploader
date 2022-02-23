"""The main module of the program."""
import getpass
import os
from . import errors
from . import articles
from . import confluence
from . import config as configuration
from .logger import main_logger, error_logger
from . import constants


def _init_config(config: configuration.Config):
    """Try loading the config file, key errors mean that the file structure is invalid, which terminates the program."""
    try:
        config.load()

        # Read credentials from command prompt, if the program is started without GUI
        if not config.get_user_gui():
            config.set_username(
                input("Enter the Confluence username:"))
            config.set_token(getpass.getpass(
                prompt="Enter the Confluence token:"))

    except (KeyError) as key_error:
        error_logger.error(
            key_error, extra={'error_id': errors.CONFIG_INVALID_STRUCTURE.error_id}, exc_info=True)
        errors.CONFIG_INVALID_STRUCTURE.print_message_and_exit()

    # Validate config file in headless (no GUI) mode, otherwise it'll be validated in the GUI
    if not config.get_user_gui():
        validation_result = config.validate_all()

        if validation_result is not None:
            validation_result[1].print_message_and_exit(validation_result[0])


def _process_and_upload(config: configuration.Config):
    """
    Process the template/data CSV and upload the articles.

    This function can be called from another thread. Don't call it from outside this module.

    Returns a status code from constants.py regarding occurred errors.
    """
    try:
        # Generate JSON dump folder if needed
        if (config.get_dump_template() or config.get_dump_generated_articles()) and not os.path.isdir("dump"):
            os.mkdir("dump")

        #
        # Load article data
        #

        main_logger.info("Loading article data from %s...",
                         config.get_article_data_csv())

        article_processor = articles.ArticleProcessor(config)

        article_data = article_processor.load_article_data()

        main_logger.info("Loaded %d article data entries", len(article_data))

        #
        # Download template
        #

        main_logger.info("Downloading template...")

        confluence_api = confluence.ConfluenceAPI(config)

        template = confluence_api.retrieve_template()

        if config.get_dump_template():
            article_processor.dump_json(template, 'downloaded_template')

        main_logger.info("Successfully downloaded and processed the template")

        #
        # Generate articles from template and article data
        #

        main_logger.info(
            "Generating articles from the article data and the template...")

        generated_articles = article_processor.generate_articles(
            template, article_data)

        main_logger.info("Generated %d articles", len(generated_articles))

        if config.get_dump_generated_articles():
            for _, article in generated_articles:
                article_processor.dump_json(article, article["title"])

        #
        # Upload articles
        #

        main_logger.info("Uploading articles...")

        # Collect data entry ids of articles that couldn't be uploaded
        errored_articles = []

        for article_id, article in generated_articles:
            if not confluence_api.upload_article(article_id, article):
                errored_articles.append(article_id)

        uploaded_articles = len(generated_articles) - len(errored_articles)

        main_logger.info("Uploaded %d of %d articles",
                         uploaded_articles, len(generated_articles))

        #
        # Export data of errored articles
        #

        if len(errored_articles) > 0:

            # Map data entry ids to actual entries
            errored_data_entries = [
                entry for entry in article_data if entry[config.get_csv_id_header()] in errored_articles]

            article_processor.write_errored_articles(errored_data_entries)

            main_logger.error("%d articles couldn't be uploaded, their data entries are saved in the file '%s'",
                              len(errored_articles), config.get_errored_articles_csv())

            return constants.MINOR_ERRORS

        return constants.NO_ERRORS

    except Exception as exception:

        # Assume unexpected error by default
        error_wrapper = errors.UNEXPECTED

        # Try extracting error wrapper, if present
        if isinstance(exception, RuntimeError) and len(exception.args) > 0 and isinstance(exception.args[0], errors.ErrorWrapper):
            error_wrapper = exception.args[0]

        # Print stacktrace for unexpected error and supply error ID, as it's needed for the logger
        if error_wrapper is errors.UNEXPECTED:
            error_logger.error(exception, extra={
                               'error_id': errors.UNEXPECTED.error_id}, exc_info=True)

        # Print error wrapper message and return fatal error code
        error_wrapper.print_message(*exception.args[1:])

        return constants.FATAL_ERRORS


def main():
    """Execute the part of the program. Entrypoint for the launcher."""
    main_logger.info(
        "Confluence Uploader: Written by Florian Haas (florian-f.haas@msg.group) in 2021/22 at msg systems ag.")

    config_instance = configuration.Config()

    _init_config(config_instance)

    if config_instance.get_user_gui():  # pragma: no cover GUI mode
        from . import gui  # Only load the gui module and it's dependencies when really needed
        main_gui = gui.create_gui(config_instance, _process_and_upload)
        main_gui.show()

    else:  # Headless (non GUI) mode
        _process_and_upload(config_instance)
