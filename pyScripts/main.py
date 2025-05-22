import json
import re
from pathlib import Path
from typing import Optional, Tuple, List, Dict
from slpp import slpp as lua
from collections import defaultdict
import logging
import mariadb
import csv

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

class WowBankExtractor:
    def __init__(self, configPath: str):
        self.configPath = Path(configPath)
        self.config = self.loadConfig()

        wowInfo = self.config.get("wowInfo", {})
        self.basePath = Path(wowInfo.get("wowAccountAddonVariablePath", ""))
        self.realmName = wowInfo.get("realmName", "")
        self.accountsToCheck = wowInfo.get("wowAccountsToCheck", {})

        self.savedVariableFilename = "bankContentExtractor.lua"
        self.savedVariableName = "MyBankData"
        self.keyMap = {1: "charName", 2: "bagId", 3: "itemLink", 4: "itemCount"}

        self.validateConfig()

    def validateConfig(self):
        if not self.basePath.exists():
            raise FileNotFoundError(f"WoW addon variable path does not exist: {self.basePath}")
        if not self.realmName:
            raise ValueError("Realm name is missing in the configuration.")
        if not self.accountsToCheck:
            raise ValueError("No WoW accounts specified in the configuration.")

    def loadConfig(self) -> dict:
        logging.info(f"Loading config from {self.configPath}")
        try:
            with self.configPath.open("r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logging.error(f"Config file '{self.configPath}' not found.")
            raise
        except json.JSONDecodeError as e:
            logging.error(f"Failed to decode JSON from config file '{self.configPath}': {e}")
            raise

    @staticmethod
    def parseItemLink(itemLink: str) -> Tuple[Optional[int], Optional[str]]:
        pattern = r"\|Hitem:(\d+):.*?\|h\[([^\]]+)\]\|h"
        match = re.search(pattern, itemLink)
        if match:
            return int(match.group(1)), match.group(2)
        return None, None

    def getCharactersForAccount(self, accountPath: Path) -> List[str]:
        if not accountPath.is_dir():
            logging.warning(f"Account path does not exist or is not a directory: {accountPath}")
            return []
        characters = [p.name for p in accountPath.iterdir() if p.is_dir()]
        logging.info(f"Found characters at {accountPath}: {characters}")
        return characters

    def loadSavedVariables(self, filePath: Path) -> dict:
        logging.info(f"Loading saved variables from {filePath}")
        with filePath.open("r", encoding="utf-8") as f:
            content = f.read()

        pattern = rf'{self.savedVariableName}\s*=\s*(\{{.*?\n\}})'
        match = re.search(pattern, content, re.DOTALL)
        if not match:
            raise ValueError(f"Variable '{self.savedVariableName}' not found in file {filePath}")

        luaTableString = match.group(1)
        data = lua.decode(luaTableString)
        if not data:
            raise ValueError(f"Failed to decode Lua variable '{self.savedVariableName}' in file {filePath}")

        return data

    def processAccount(self, accountName: str, characters: List[str]) -> List[dict]:
        logging.info(f"Processing account '{accountName}' with characters: {characters}")
        accountData = []
        accountPath = self.basePath / accountName.upper() / self.realmName

        # If characters list empty or all empty strings, scan folders
        if not characters or all(not c for c in characters):
            logging.info(f"No characters specified for account '{accountName}', scanning directories...")
            characters = self.getCharactersForAccount(accountPath)

        characters = [c for c in characters if c]

        for charName in characters:
            savedVarPath = accountPath / charName / "SavedVariables" / self.savedVariableFilename
            if not savedVarPath.is_file():
                logging.warning(f"Saved variables file missing: {savedVarPath}")
                continue

            try:
                rawData = self.loadSavedVariables(savedVarPath)
            except Exception as e:
                logging.error(f"Error loading saved variables for {accountName} - {charName}: {e}")
                continue

            cleanedEntries = [
                {self.keyMap.get(k, f"unknown_{k}"): v for k, v in entry.items()}
                for entry in rawData.values()
            ]
            accountData.extend(cleanedEntries)

        return accountData

    def extract(self) -> Dict[str, List[dict]]:
        aggregatedData = defaultdict(list)

        for account, chars in self.accountsToCheck.items():
            logging.info(f"Starting processing for account: {account}")
            accountItems = self.processAccount(accountName=account, characters=chars)
            aggregatedData[account].extend(accountItems)

        # Post-process: extract itemId, itemName and remove itemLink
        for account, items in aggregatedData.items():
            for item in items:
                itemId, itemName = self.parseItemLink(item.get("itemLink", ""))
                item["itemId"] = itemId
                item["itemName"] = itemName
                item.pop("itemLink", None)

        return aggregatedData



def validateSinkType(sinkType: str) -> bool:
    validSinkTypes = ["mariadb", "csv", "json"]
    if sinkType not in validSinkTypes:
        raise ValueError(f"Invalid sink type '{sinkType}'. Valid options are: {validSinkTypes}")
    return True



if __name__ == "__main__":
    extractor = WowBankExtractor("conf.json")
    finalData = extractor.extract()

    configFile = "conf.json"
    configPath = Path(configFile)
    with configPath.open("r", encoding="utf-8") as f:
        configData = json.load(f)
    sinkType = configData.get("sinkType", "json")
    validateSinkType(sinkType)
    connection = configData.get("connection", {})

    if sinkType == "mariadb":
        host = connection.get("host", "localhost")
        port = connection.get("port", 3306)
        username = connection.get("username", "")
        password = connection.get("password", "")
        database = connection.get("database", "")

        if not all([host, port, username, password, database]):
            raise ValueError("Incomplete MySQL connection details in the configuration.")

        try:
            dbConnection = mariadb.connect(
                host=host,
                port=port,
                user=username,
                password=password,
                database=database
            )
            logging.info("Successfully connected to the MySQL database.")
        except mariadb.Error as err:
            logging.error(f"Error connecting to MySQL: {err}")
            raise
        cursor = dbConnection.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS bank_items (account VARCHAR(255), charName VARCHAR(255), bagId INT, itemId INT, itemName VARCHAR(255), itemCount INT)")
        cursor.execute("TRUNCATE TABLE bank_items")
        for account, items in finalData.items():
            for item in items:
                cursor.execute(
                    "INSERT INTO bank_items (account, charName, bagId, itemId, itemName, itemCount) VALUES (?, ?, ?, ?, ?, ?)",
                    (account, item.get("charName"), item.get("bagId"), item.get("itemId"), item.get("itemName"), item.get("itemCount"))
                )
        dbConnection.commit()
        cursor.close()
        dbConnection.close()
        logging.info("Data successfully inserted into the MySQL database.")
    elif sinkType == "csv":
        outputFile = connection.get("outputFileName", "bank_items.csv")
        outputFileLocation = connection.get("outputFileLocation", ".")
        outputFile = Path(outputFileLocation) / f"{outputFile}.csv"
        with open(outputFile, "w", newline="", encoding="utf-8") as csvfile:
            fieldnames = ["account", "charName", "bagId", "itemId", "itemName", "itemCount"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for account, items in finalData.items():
                for item in items:
                    writer.writerow({
                        "account": account,
                        **{k: item[k] for k in fieldnames[1:]}
                    })
        logging.info(f"Data successfully written to {outputFile}.")
    elif sinkType == "json":
        outputFile = connection.get("outputFileName", "bank_items.json")
        outputFileLocation = connection.get("outputFileLocation", ".")
        outputFile = Path(outputFileLocation) / f"{outputFile}.json"
        with open(outputFile, "w", encoding="utf-8") as jsonfile:
            json.dump(finalData, jsonfile, ensure_ascii=False, indent=4)
        logging.info(f"Data successfully written to {outputFile}.")
    else:
        raise ValueError(f"Unsupported sink type '{sinkType}'.")
    logging.info("Extraction and processing completed.")
    logging.info("Exiting program.")
    exit(0)
