# 🏡 Corretor Virtual

This basic script will go through major real state websites* in Brazil and check for new properties that match your criteria.
New properties are added to a Google Sheet with their details listed.

## How to use
Just load your python environment and run the zap.py script. New properties will be added to the defined Google Sheet along with the log for each run.

Make sure that the spreadsheet selected has two worksheets. The properties will be stored on the first one and the log on the second one.

Add the spreadsheet key to the `gsheets_main_key` variable on the YAML file, along with the desired URL on the same file. The URL should be the one that you would use to search for properties on the website with the characteristics you want.
You will also need a *gsheet_credential.json* file on the main repository. Check the [Google Sheets API documentation](https://developers.google.com/sheets/api/quickstart/python) for more information.
## Warnings

In 2022, the website did not seem to have any significant deterrence for automated scripts. However, the URLs collected are "clean" versions, unlike they would be in an authentic interaction. If many of the URLs collected are opened in a short time span, the website may temporarily block your IP address. Using VPNs is recommended if there is an intent to open many of the URLs listed. Also, keep in mind that this could change in the future, so using a search URL with more filters (and fewer results) is good advice.

This code has been not replicated elsewhere, so many errors could occur. Feel free to open an issue if you find any.

<hr>

* [Zap](https://www.zapimoveis.com.br/) and [Viva Real](https://www.vivareal.com.br/) turned out to be the exact same database, just different layouts. Hence, only the script for Zap is finished. A script for OLX may be added in the future.