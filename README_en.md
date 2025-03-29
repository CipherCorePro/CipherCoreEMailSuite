# **CipherMailArchiver** 📩🔒
_Efficient & secure email archiving with IMAP & POP3 – Open-Source & local storage._
![logo](https://github.com/user-attachments/assets/33990230-ad64-44ab-90c0-e2e328829246)

---

# CipherCore E-Mail Suite

**A Desktop Email Client Focused on Secure Local Archiving, Management, and Exploration.**

[![Language](https://img.shields.io/badge/Language-Python%203-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE) <!-- Add a LICENSE file -->

---

## Table of Contents

1.  [Overview](#overview)
2.  [Features](#features)
3.  [Screenshots](#screenshots)
4.  [Prerequisites](#prerequisites)
5.  [Installation](#installation)
6.  [Usage](#usage)
    *   [GUI Mode](#gui-mode)
    *   [Command Line Mode (CLI)](#command-line-mode-cli)
7.  [Configuration](#configuration)
    *   [`accounts.txt`](#accountstxt)
    *   [Password Management (Keyring)](#password-management-keyring)
8.  [Archive Structure](#archive-structure)
9.  [Troubleshooting & Logging](#troubleshooting--logging)
10. [Frequently Asked Questions (FAQ)](#frequently-asked-questions-faq)
11. [Glossary](#glossary)
12. [License](#license)
13. [Contact & Support](#contact--support)

---

## Overview

The **CipherCore E-Mail Suite** is a desktop application written in Python that allows users to retrieve emails from IMAP and POP3 accounts, securely archive them locally in `.eml` format, and search and manage these archives. The suite offers a graphical user interface (GUI) for intuitive operation as well as a command-line mode (CLI) for automated archiving tasks.

A special focus is placed on security: Passwords are not stored directly in configuration files but are managed securely in the system's native keychain using the `keyring` library.

The application not only allows viewing archived emails and their attachments but also composing, replying to, and forwarding emails via configured SMTP servers.

## Features

*   **Account Management:** Add and remove multiple email accounts (IMAP/POP3 for receiving, SMTP for sending).
*   **Secure Password Storage:** Uses the system's native keychain management via `keyring` to store account passwords.
*   **Email Retrieval & Archiving:**
    *   Retrieval of emails via IMAP or POP3.
    *   Storage of emails in the standardized `.eml` format in a clear folder structure.
    *   Selective archiving of specific IMAP folders.
    *   Optional separation of archiving based on email age (older emails in `archive`, newer ones in `emails`).
    *   Automatic saving of attachments in separate subfolders.
*   **Archive Explorer (GUI):**
    *   Tree view for navigating through archived emails and folders.
    *   Integrated email preview (headers and text body).
    *   Opening attachments with the default system program.
    *   Opening the storage location of emails or folders in the system explorer.
    *   **Fuzzy Search:** Searches subject, sender, recipient, and body of `.eml` files (requires `fuzzywuzzy`).
*   **Email Management (GUI):**
    *   Composing new emails.
    *   Replying to and forwarding archived emails.
    *   Adding attachments to outgoing emails.
    *   Sending via configured SMTP servers (supports SSL/TLS and STARTTLS).
*   **Command Line Mode (CLI):**
    *   Automated archiving for a specific account.
    *   Filtering by folders and email age.
    *   Ideal for scheduled tasks (e.g., Cronjobs).
*   **Logging:** Detailed logging of actions and errors to the `email_archiver.log` file.

## Screenshots

*(Insert screenshots of the application here to provide a visual impression)*

*   **Main Window (Accounts & Actions):**
   ![image](https://github.com/user-attachments/assets/a259c8aa-9c8b-45d7-8485-56209e07e961)

*   **Archive Explorer:**
    ![image](https://github.com/user-attachments/assets/59420de1-0174-4cde-a610-e71afdd96a29)

*   **Email Preview:**
   ![image](https://github.com/user-attachments/assets/6598a8a0-def7-4f3b-8c6b-6c8a282d3ab1)


*   **Compose Email:**
    ![image](https://github.com/user-attachments/assets/efe9ca0a-6fc5-4b81-af98-580d3c9497b2)



## Prerequisites

*   **Python:** Version 3.7 or higher is recommended.
*   **Tkinter:** Required for the GUI. Usually included with Python distributions for Windows and macOS. On Linux, it might need to be installed separately (e.g., `sudo apt-get install python3-tk` for Debian/Ubuntu).
*   **Python Libraries:**
    *   `keyring`: For secure password storage.
    *   `fuzzywuzzy` (Optional): For the search function in the Archive Explorer. Significantly improves search quality.
    *   `python-Levenshtein` (Optional, recommended for `fuzzywuzzy`): Significantly speeds up `fuzzywuzzy` calculations.

*   **Keyring Backend:** `keyring` needs a backend to store passwords.
    *   **Windows/macOS:** A system backend is usually available.
    *   **Linux:** A backend might need to be installed (e.g., `SecretService` or `KWallet`). A file-based alternative is `keyrings.cryptfile` (`pip install keyrings.cryptfile`). You might need to initialize the backend once or set a master password after installation.

## Installation

1.  **Clone or download the repository:**
    ```bash
    git clone <repository_url> # Replace <repository_url> with the URL of your Git repository
    cd <repository_directory>
    ```
    Or download the source code as a ZIP file and extract it.

2.  **Set up a Python environment (Recommended):**
    Using a virtual environment is highly recommended:
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # macOS / Linux
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    Install the required Python libraries. To use the optional search and its acceleration:
    ```bash
    pip install keyring "fuzzywuzzy[speedup]"
    ```
    If you don't need `fuzzywuzzy`, install only `keyring`:
    ```bash
    pip install keyring
    ```
    If `keyring` causes issues on Linux, additionally install a file-based backend (see [Prerequisites](#prerequisites)):
    ```bash
    pip install keyrings.cryptfile
    ```

4.  **Make the script executable (Optional, Linux/macOS):**
    ```bash
    chmod +x ciphercore_email_suite.py # Replace with the actual script filename if necessary
    ```

## Usage

Replace `ciphercore_email_suite.py` below with the actual name of your Python script file.

### GUI Mode

Start the application without additional arguments to open the graphical user interface:

```bash
python ciphercore_email_suite.py
```

**First Steps:**

1.  On the first launch, the account list is empty.
2.  Click **"Add Account"**.
3.  Fill in the details for your email account:
    *   **Name:** Any name for identification (e.g., "Work", "Personal").
    *   **Protocol:** Choose IMAP or POP3 for email reception.
    *   **Server (Incoming):** Your provider's IMAP or POP3 server (e.g., `imap.example.com`).
    *   **Port:** The appropriate port for the server (e.g., 993 for IMAP SSL, 995 for POP3 SSL).
    *   **Email Address:** Your full email address.
    *   **Password:** Your email password. This will be stored securely in the keyring.
    *   **SMTP Server (Outgoing):** The server for sending emails (e.g., `smtp.example.com`). Optional, but required for sending/replying/forwarding.
    *   **SMTP Port:** The port for the SMTP server (e.g., 587 for TLS/STARTTLS, 465 for SSL).
4.  Click **"Save"**. The account will appear in the list.
5.  Select the account in the list.
6.  **(IMAP only):** Click **"Select Folders"** to load the IMAP folders and choose the ones you want to archive. Save the selection.
7.  Click **"Archive Selected Folders"** to start the retrieval and saving process. A progress window will be displayed.
8.  Use **"Open Archive Explorer"** to browse and view your archived emails.
9.  Use **"Compose Email"** to write new emails (requires configured SMTP for the selected account).

### Command Line Mode (CLI)

The CLI mode is used for automated archiving without a graphical interface.

**Syntax:**

```bash
python ciphercore_email_suite.py --cli --account_name "Account Name" [--folders "Folder1,Folder2,..."] [--age_days DAYS]
```

**Arguments:**

*   `--cli`: (Required) Activates CLI mode.
*   `--account_name "Account Name"`: (Required) The name of the account (as added in the GUI, case-insensitive) to be processed. Enclose names with spaces in quotes.
*   `--folders "Folder1,Folder2,..."`: (Optional) A comma-separated list of IMAP folders to check. If not specified, defaults to checking only `INBOX` for IMAP. This argument is ignored for POP3 (always just the inbox).
*   `--age_days DAYS`: (Optional) The minimum age (in days) an email must have to be saved in the `archive` folder. Emails younger than this are saved in the `emails` folder. The default value is `30`.

**Examples:**

1.  **Archive all emails older than 60 days from the INBOX and the "Gesendet" (Sent) folder of the "Work" IMAP account:**
    ```bash
    python ciphercore_email_suite.py --cli --account_name "Work" --folders "INBOX,Gesendet" --age_days 60
    ```

2.  **Archive all emails older than 30 days (default) from the "Personal" POP3 account:**
    ```bash
    python ciphercore_email_suite.py --cli --account_name "Personal"
    ```
    *(Note: `--folders` is irrelevant here)*

3.  **Archive all emails older than 7 days from the INBOX of the "Backup Mail" IMAP account:**
    ```bash
    python ciphercore_email_suite.py --cli --account_name "Backup Mail" --age_days 7
    ```
    *(Note: Only INBOX is checked as `--folders` is not specified)*

The CLI mode outputs progress information to the console and writes detailed logs to the `email_archiver.log` file.

## Configuration

### `accounts.txt`

This file is automatically created in the same directory as the script and contains the configuration details for your email accounts, **but no passwords**.

*   **Format:** Comma-separated values (CSV), one line per account.
*   **Columns:** `Name,Server,Port,Email Address,Protocol,SMTP Server,SMTP Port`
*   **Example line:** `Work,imap.company.com,993,john.doe@company.com,imap,smtp.company.com,587`
*   **Editing:** You can edit this file manually, but it is recommended to add or remove accounts via the GUI to avoid inconsistencies with the keyring.
*   **Security:** **Never store passwords in this file!**

### Password Management (Keyring)

The application uses the `keyring` library to store your email passwords securely.

*   **How it works:** `keyring` interacts with your operating system's secure credential store (e.g., Windows Credential Manager, macOS Keychain, Linux Secret Service/KWallet).
*   **Advantage:** Passwords are not stored in plaintext and are protected by your operating system's security mechanisms.
*   **Setup:** Usually automatic. On Linux, you might need to install and configure a compatible backend (see [Prerequisites](#prerequisites)).
*   **Access:** When the application needs the password for an account (when adding, retrieving, or sending), it requests it from `keyring`. You might need to grant access once or enter your keychain's master password.

## Archive Structure

Archived emails and attachments are stored by default in the `EmailArchiv` subfolder (in the script's directory). The structure is organized as follows:

```
EmailArchiv/
└── <Account Name>/                # One folder per configured account (sanitized name)
    ├── archive/                   # Contains emails older than --age_days (CLI) or classified as old during GUI archiving
    │   └── <Original Folder Name>/ # Subfolder per IMAP folder (sanitized, '/' becomes '__') or 'inbox' for POP3
    │       └── YYYY-MM-DD/        # Subfolder per archiving day
    │           ├── <Timestamp>_<Subject>_<ID>.eml
    │           ├── ...            # Other .eml files
    │           └── attachments/   # Folder for attachments (only if present)
    │               ├── attachment1.pdf
    │               └── image.jpg
    └── emails/                    # Contains emails younger than --age_days (CLI) or classified as not old during GUI archiving
        └── <Original Folder Name>/
            └── YYYY-MM-DD/
                ├── <Timestamp>_<Subject>_<ID>.eml
                └── attachments/
                    └── ...
```

*   **`<Account Name>`:** Derived from the name you assigned when adding the account (invalid characters are replaced).
*   **`archive` vs. `emails`:** Separation is based on the email's age compared to the `age_days` parameter (default 30 days). This is primarily relevant for CLI archiving or if you keep the age check in the GUI logic.
*   **`<Original Folder Name>`:** The name of the IMAP folder the email came from (sanitized). For POP3, this is always `inbox`. IMAP hierarchies (e.g., `A/B/C`) typically become `A__B__C`.
*   **`YYYY-MM-DD`:** The date the archiving was performed.
*   **`.eml` files:** The emails in raw format. The filename includes a timestamp, subject (shortened/sanitized), and a unique ID.
*   **`attachments` folder:** Contains all attachments from the emails in the respective daily folder.

## Troubleshooting & Logging

*   **Log File:** All important actions, warnings, and errors are written to the `email_archiver.log` file in the same directory as the script. This file is the first place to check for issues.
*   **Keyring Issues:** If saving or retrieving passwords fails, check if a `keyring` backend is correctly installed and configured (see [Prerequisites](#prerequisites) and FAQ). Error messages in the log or GUI often provide clues.
*   **Connection Errors:** Ensure server names, ports, and protocols are correct and that your network allows connections to the email servers (firewall, antivirus).
*   **Authentication Errors:** Verify the email address and password. Some providers require app-specific passwords if Two-Factor Authentication (2FA) is active.
*   **GUI Freezes:** Although retrieval and sending operations run in separate threads, very large operations might briefly slow down the GUI. If it freezes permanently, check the log file for errors.
*   **Search Not Working:** Ensure `fuzzywuzzy` and `python-Levenshtein` are installed (`pip install "fuzzywuzzy[speedup]"`).

## Frequently Asked Questions (FAQ)

**Q: Why is `keyring` used? Can't I just store passwords in `accounts.txt`?**
A: `keyring` is used for security reasons. Storing passwords in plaintext in a file is extremely insecure. `keyring` utilizes the operating system's secure stores, significantly reducing the risk of password theft.

**Q: I can't get `keyring` to work on Linux. What can I do?**
A: Ensure a compatible backend like `python3-secretstorage` (for GNOME/SecretService) or `python3-kwallet` (for KDE) is installed. Alternatively, install the file-based backend with `pip install keyrings.cryptfile`. You might need to unlock your keyring or set a master password. Check the `keyring` documentation for details.

**Q: The search in the Archive Explorer is slow or doesn't find anything.**
A: The search scans the content of `.eml` files at runtime, which can take time for large archives. Ensure `fuzzywuzzy` and ideally `python-Levenshtein` are installed (`pip install "fuzzywuzzy[speedup]"`) to enable and accelerate the search. The quality of the fuzzy search depends on the search term and the content.

**Q: Can the application delete emails from the server (e.g., after archiving)?**
A: No, the application is primarily designed as an archiving and viewing tool. It does not delete emails from the server. This is a safety measure to prevent data loss.

**Q: How are email attachments handled?**
A: Attachments are extracted from the `.eml` files and saved in the `attachments` subfolder of the respective daily archive. The original `.eml` file remains complete.

**Q: Can I use the application on different operating systems (Windows, macOS, Linux)?**
A: Yes, since the application is written in Python with Tkinter, it should work cross-platform as long as Python 3 and the dependencies are installed correctly. Tkinter and Keyring behavior might differ slightly between systems.

**Q: Are HTML emails displayed correctly?**
A: The email preview attempts to display the `text/plain` part of an email. If unavailable, it displays the `text/html` part, but without complex formatting, images, or styles (plain text of the HTML). It does not include a full HTML rendering engine.

**Q: The GUI freezes when retrieving/sending emails.**
A: Time-consuming operations (retrieval, sending) are executed in background threads to keep the GUI responsive. However, with very large numbers of emails or slow connections, brief delays might still occur. If the GUI freezes permanently, it indicates an error – please check `email_archiver.log`.

**Q: I get an SMTP authentication error even though my password is correct.**
A: Some email providers (like Gmail, Outlook.com) require the use of "app-specific passwords" when Two-Factor Authentication (2FA) is enabled. You need to generate such a password in your email account's security settings and then use that password in the CipherCore E-Mail Suite.

## Glossary

*   **IMAP (Internet Message Access Protocol):** A protocol for retrieving emails. Emails remain stored on the server, and folder structures are synchronized.
*   **POP3 (Post Office Protocol version 3):** An older protocol for retrieving emails. Typically, emails are downloaded to the client and deleted from the server (though this is configurable). Does not support folder synchronization.
*   **SMTP (Simple Mail Transfer Protocol):** The standard protocol for sending emails.
*   **.eml file:** A file format for storing individual email messages, including headers, body, and attachments, according to the MIME standard.
*   **Keyring / Keychain:** A secure storage facility provided by the operating system to manage credentials like passwords and keys.
*   **CLI (Command Line Interface):** A text-based interface for interacting with a program using command-line commands.
*   **GUI (Graphical User Interface):** A graphical interface with windows, buttons, and other visual elements for operating a program.
*   **Fuzzy Search:** A search technique that finds matches even when the search term does not exactly match the text (e.g., due to typos or similar words).
*   **Header (Email):** Metadata of an email, such as sender (From), recipients (To, Cc, Bcc), Subject, and Date.
*   **Payload (Email):** The actual content of a part of an email message (e.g., the body text or the content of an attachment), often encoded (e.g., Base64).
*   **MIME (Multipurpose Internet Mail Extensions):** A standard that extends the format of emails to support non-text content like attachments, different character sets, and multi-part messages.
*   **Threading (in Programming):** A technique allowing a program to perform multiple tasks (seemingly) concurrently, e.g., to improve GUI responsiveness during long operations.
*   **RFC 822 / RFC 2822 / RFC 5322:** A series of standards defining the format of email messages.
*   **SSL/TLS (Secure Sockets Layer / Transport Layer Security):** Encryption protocols for securing communication over a network, commonly used for IMAP, POP3, and SMTP (e.g., ports 993, 995, 465).
*   **STARTTLS:** An SMTP command that upgrades an unencrypted connection on a standard port (like 587 or 25) to an encrypted TLS connection if supported by the server.

## License

This project is licensed under the MIT License. See the `LICENSE` file for more details.

```markdown
MIT License

Copyright (c) [Year] [Copyright Holder Name]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```



## Contact & Support

For problems, questions, or suggestions:

*   Open an **Issue** in the GitHub repository (if available).
*   Contact the author: `support@ciphercore.de`

---
```
