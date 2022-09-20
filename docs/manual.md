## Short manual for the Confluence Uploader

This manual briefely desribes the usage of the Confluence Uploader.

### Purpose of the program

The program allows the mass-creation of articles in Confluence. You can specify a template article in Confluence which contains placeholders. On your local machine you can create an article data CSV file containing the values for each placeholder per row. The program then downloads the template, generates a new article by filling the placeholders for each row found in the article data CSV file, and then uploads it to Confluence.

### Important hints

1. The program probably cannot upload articles via a proxy or VPN. Ensure you are directly connected to Confluence.
1. If your Confluence instance uses two-factor authentication, make sure the configured user can access the REST-API of Confluence without 2FA, as the tool does not support that.
1. If the program cannot upload an article (because of an error), it still tries to upload the other ones. The data entries of the articles in error are saved in `./errored_articles.csv`. You can use that file as the article data CSV file for a subsequent run, to retry uploading those articles, too.
1. The logs of the last run of the program are saved in `./logs.log`.
1. The file `./docs/error_catalog.md` contains a list of errors and their descriptions. You can find them by their error ID displayed in the logs.
1. Make sure to set the Confluence base URL in `./config/config.ini`.

### Configuration

There are two configuration files (in `./config`): `uploader_config.ini` and `config.ini`.

* `uploader_config.ini`: Contains the main configuration properties.
* `config.ini`: Contains advanced configuration properties.

In `config.ini` you can enable a GUI for the `uploader_config.ini` file, otherwise the program will be console-based.

### Template specification

An article template is just a normal article in Confluence, which contains placeholders. A placeholder is a tag `#placeholder_name#`, with `#` being the starting and ending placeholder character and `placeholder_name` being the name of the placeholder.

The placeholder character can be configured in `uploader_config.ini`.

The placeholder name must be alphanumeric, additionally the dot `.`, minus `-` and underscore `_` characters are allowed.

If you want to use the placeholder character in the template as a regular character - so that it will be shown as a normal text character - it has to be escaped by appending it to the configured escape character (by default `~`). Thus, `~#` in the template will be replaced with `#` in the generated article, and the `~#` will not be considered as part of a placeholder.

Unescaped placeholder characters which are not part of a placeholder will cause an error.

### Article data specification

The article data CSV file contains the data of one generated article per row. The first row has to be the titles of specified values. Each placeholder in the article must have a column in the article data CSV file with the placeholder name as column title. Additionally, the article data CSV file needs an id column with different values for all rows.

This allows the data entries per row to be uniquely identified. The values in the ID column can be used as placeholders in the article template, if needed.

Ensure that the title of the generated articles is unique, as this is required in Confluence.

Leading and trailing whitespaces (like space and tab) in the CSV columns will be ignored.

### Examples

Assume an article in Confluence with the title `Item #id#: #item_name#` and the following content: `Item name: #item_name#. ~# items: Unknown.`.

Also assume the following article data CSV file:

```csv
id; item_name
1; Apple
2; Banana
3; Grapefruit
4; Cherries
```

Assume the placeholder character is `#`, the escape character is '~', and the configured ID column name is `id`.

The values `1`, `2`, `3` and `4` in the ID column are distinct, thus the article data CSV file is valid. The program will generate four articles from the template and the article data CSV file:
* Item name: Apple. # items: Unknown.
* Item name: Banana. # items: Unknown.
* Item name: Grapefruit. # items: Unknown.
* Item name: Cherries. # items: Unknown.

They have the titles `Item 1: Apple`, `Item 2: Banana`, `Item 3: Grapefruit` and `Item 4: Cherries`. The titles are distinct, thus all articles can be uploaded, if no article with those titles exists.

The escaped placeholder `~#` in the template will be replaced with `#` in the final article.
