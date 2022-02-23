## Error Catalog of the Confluence Uploader
This table contains the errors thrown by the Confluence Uploader, and a short description of their cause.

Error-ID:|Name:|Description:
---|---|---
0|Unexpected Error|An unexpected error did occur. This could be a bug, or something more obscure, which the developer did not take into account. You can probably not do much about that, unless you’re proficient with Python. Please contact the developer (florian-f.haas@msg.group) or another knowledgeable person.
1|No ID column in article data|The article data CSV file does not contain a column with the specified ID header. Also check whether the CSV separator is correct, as that can also lead to a correct ID column not being recognized properly.
2, 3|No unique IDs in the article data|The article data contain one or more entries which have the same value in the ID column. Fix this by ensuring the IDs are unique.
4|SSL Error|There was an error regarding the encrypted SSL connection to Confluence. Make sure that you’re contacting Confluence directly. **Using the program via a VPN and possibly proxy can cause this error.**
5|Template download failed|The specified template couldn’t be downloaded from Confluence. Reasons can be that the template doesn’t exist, the user has not the required permissions, the supplied login credentials were not accepted, or no connection to Confluence/the configured wiki could be opened. This is usually accompanied by a response message from Confluence.
6|Existence check for article failed|The program failed to check whether an article with the specified title already exists on Confluence. The reasons can be the ones specified for 5.
7|Article upload failed|The specified article couldn’t be uploaded to Confluence. Reasons can be the ones for error 5, or that an article with the same title already exists.
8|Article update failed|Like 7, but instead of uploading, the content of an existing article was changed.
9|No unique article title|There are multiple articles generated from the article data which have the same title. Fix this by ensuring in the article template and the article data that the article title is different for each generated article.
10|Unknown placeholder in article|There are placeholders in the article template which have no correspondence in the article data csv file. Assume # is the placeholder character, and the article contains a placeholder #pl1#. If the article data csv file has no column with the header pl1, the error is thrown.
11|Single placeholder character was found|Placeholder characters that are not escaped and don’t belong to a valid placeholder were found in the template. Fix this by checking the placeholder characters in the template – make sure they are either escaped or part of a valid placeholder.
12|Validation errors in articles|This is shown if one or more errors 9, 10, 11 do occur. Fix those, then this error will also disappear.
13|Invalid config file structure|The configuration files have missing properties/sections. Ensure that the configuration file structure is the same one as originally provided with the program.
14, 16, 20, 23, 24, 26, 28, 30, 32, 33, 34|Empty configuration property|The displayed configuration property is empty/not specified.
15, 25|Non-numeric configuration property|The displayed configuration property has to be numeric, but it isn’t.
17, 21, 29|Configuration property is no single character|The displayed configuration property is required to be a single character, but it is longer or empty.
18, 22|Configuration property is not valid|The specified configuration property must not to be alphanumeric, a dot ‘.’, a minus ‘-’ or an underscore ‘_’.
19|Escape character equals template placeholder|The configured escape character and template placeholder are equal. Fix this by assigning distinct characters to those.
27|The specified file doesn’t exist|A file as specified in that configuration property does not exist. The property either contains the absolute or relative path of that file. Ensure that it exists and that it is a file.