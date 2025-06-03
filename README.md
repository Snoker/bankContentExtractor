# bankContentExtractor

A toolset for extracting World of Warcraft bank contents from saved variables and exporting them to MariaDB, CSV, or JSON.

## Usage

1. **Extract Bank Data In-Game**
    - Install the `bankContentExtractor` addon in your WoW AddOns folder.
    - In-game, open your bank and type `/bagscan` in chat to save your bank contents.

2. **Configure Extraction**
    - Copy `conf_template.json` to `conf.json`.
    - Edit `conf.json` to set your WoW account path, realm, accounts, and output options.

3. **Run the Extractor**
    - Install Python dependencies:
      ```sh
      pip install mariadb slpp
      ```
    - Run the script from the `pyScripts` folder:
      ```sh
      python3 main.py
      ```
    - Data will be exported to your chosen sink (MariaDB, CSV, or JSON) as configured.

## Notes

- Make sure you have access to your WoW SavedVariables folder.
- For MariaDB export, ensure the database and credentials are set up.
- For CSV/JSON, output files will be created at the specified location.