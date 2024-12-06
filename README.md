# Sheets2Anki

**Sheets2Anki** is an Anki add-on that syncs your Anki decks with a Google Sheets document published as CSV. It supports both Basic and Cloze note types, automatically assigns tags, and removes cards that are no longer in Google Sheets.

## Features
- **Sync from Google Sheets (CSV):** Publish your Google Sheet as a CSV and easily integrate with Anki.
- **Supports Cloze and Basic Cards:** Automatically detect if a question is Cloze-formatted or a simple Q&A.
- **Automatic Tag Assignment:** Tags are derived from a specified column in your sheet.
- **Removes Deleted Cards:** If a card no longer appears in the Google Sheet, it’s removed from Anki to maintain consistency.

## Installation
1. Go to the [Releases](https://github.com/sebastianpaez/sheets2anki/releases) page of this repository.
2. Download the latest `.ankiaddon` file.
3. In Anki, go to `Tools > Add-ons > Install from file...`.
4. Select the downloaded `.ankiaddon` file and restart Anki.

## Usage
1. **Add a New Remote Deck:**
   - Go to `Tools > Manage Remote Deck > Add New Remote Deck`.
   - Paste the URL of your published Google Sheet CSV.
   - Enter a deck name and confirm.

2. **Syncing Decks:**
   - Go to `Tools > Manage Remote Deck > Sync Remote Decks` to synchronize your local Anki deck with Google Sheets.

3. **Remove a Remote Deck:**
   - Go to `Tools > Manage Remote Deck > Remove Remote Deck`.
   - Select the deck you want to unlink.

## Requirements
- **Anki Version:** Compatible with Anki 2.1.x.
- **Models Needed:**
  - **Basic Model:** Should have `Front` and `Back` fields.
  - **Cloze Model:** Should have `Text` and `Extra` fields.

## Troubleshooting
- **No Cards Imported?:** Check that your CSV headers are correct (`question`, `answer`, `tags`) and that your note models exist.
- **Permission Denied (Publickey):** If using Git via SSH, ensure your SSH keys are correctly added to GitHub.
- **Cards Not Deleting?:** Verify that the cards no longer appear in the CSV and re-sync.

## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contact
For suggestions or issues, please open an issue on GitHub or contact me via [Your Contact Info or GitHub Profile].
