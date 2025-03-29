# **CipherCore E-Mail Suite** 📩🔒  
_Effiziente & sichere E-Mail-Archivierung mit IMAP & POP3 – Open-Source & lokal speichernd._
![logo](https://github.com/user-attachments/assets/33990230-ad64-44ab-90c0-e2e328829246)

---

# CipherCore E-Mail Suite

**Ein Desktop E-Mail-Client mit Fokus auf sichere lokale Archivierung, Verwaltung und Exploration.**

[![Sprache](https://img.shields.io/badge/Sprache-Python%203-blue.svg)](https://www.python.org/)
[![Lizenz](https://img.shields.io/badge/Lizenz-MIT-green.svg)](LICENSE) <!-- Fügen Sie eine LICENSE-Datei hinzu -->

---

## Inhaltsverzeichnis

1.  [Übersicht](#übersicht)
2.  [Funktionen](#funktionen)
3.  [Screenshots](#screenshots)
4.  [Voraussetzungen](#voraussetzungen)
5.  [Installation](#installation)
6.  [Verwendung](#verwendung)
    *   [GUI-Modus](#gui-modus)
    *   [Kommandozeilenmodus (CLI)](#kommandozeilenmodus-cli)
7.  [Konfiguration](#konfiguration)
    *   [`accounts.txt`](#accountstxt)
    *   [Passwortverwaltung (Keyring)](#passwortverwaltung-keyring)
8.  [Archivstruktur](#archivstruktur)
9.  [Fehlerbehebung & Logging](#fehlerbehebung--logging)
10. [Häufig gestellte Fragen (FAQ)](#häufig-gestellte-fragen-faq)
11. [Glossar](#glossar)
12. [Lizenz](#lizenz)
13. [Kontakt & Support](#kontakt--support)

---

## Übersicht

Die **CipherCore E-Mail Suite** ist eine in Python geschriebene Desktop-Anwendung, die es Benutzern ermöglicht, E-Mails von IMAP- und POP3-Konten abzurufen, sicher lokal im `.eml`-Format zu archivieren und diese Archive zu durchsuchen und zu verwalten. Die Suite bietet eine grafische Benutzeroberfläche (GUI) für eine intuitive Bedienung sowie einen Kommandozeilenmodus (CLI) für automatisierte Archivierungsaufgaben.

Ein besonderer Fokus liegt auf der Sicherheit: Passwörter werden nicht direkt in Konfigurationsdateien gespeichert, sondern über die `keyring`-Bibliothek sicher im systemeigenen Schlüsselbund verwaltet.

Die Anwendung ermöglicht nicht nur das Betrachten archivierter E-Mails und ihrer Anhänge, sondern auch das Verfassen, Beantworten und Weiterleiten von E-Mails über konfigurierte SMTP-Server.

## Funktionen

*   **Kontoverwaltung:** Hinzufügen und Entfernen von mehreren E-Mail-Konten (IMAP/POP3 für Empfang, SMTP für Versand).
*   **Sichere Passwortspeicherung:** Nutzt die systemeigene Schlüsselbundverwaltung über `keyring` zur Speicherung von Account-Passwörtern.
*   **E-Mail-Abruf & Archivierung:**
    *   Abruf von E-Mails via IMAP oder POP3.
    *   Speicherung der E-Mails im standardisierten `.eml`-Format in einer übersichtlichen Ordnerstruktur.
    *   Selektive Archivierung bestimmter IMAP-Ordner.
    *   Optionale Trennung der Archivierung basierend auf dem E-Mail-Alter (ältere Mails in `archiv`, neuere in `emails`).
    *   Automatische Speicherung von Anhängen in separaten Unterordnern.
*   **Archiv-Explorer (GUI):**
    *   Baumansicht zur Navigation durch die archivierten E-Mails und Ordner.
    *   Integrierte E-Mail-Vorschau (Header und Textkörper).
    *   Öffnen von Anhängen mit dem Standard-Systemprogramm.
    *   Öffnen des Speicherorts von E-Mails oder Ordnern im System-Explorer.
    *   **Unscharfe Suche (Fuzzy Search):** Durchsucht Betreff, Absender, Empfänger und Textkörper von `.eml`-Dateien (erfordert `fuzzywuzzy`).
*   **E-Mail-Verwaltung (GUI):**
    *   Verfassen neuer E-Mails.
    *   Antworten und Weiterleiten von archivierten E-Mails.
    *   Hinzufügen von Anhängen zu ausgehenden E-Mails.
    *   Versand über konfigurierte SMTP-Server (unterstützt SSL/TLS und STARTTLS).
*   **Kommandozeilenmodus (CLI):**
    *   Automatisierte Archivierung für ein bestimmtes Konto.
    *   Filterung nach Ordnern und E-Mail-Alter.
    *   Ideal für geplante Aufgaben (z.B. Cronjobs).
*   **Logging:** Detaillierte Protokollierung von Aktionen und Fehlern in die Datei `email_archiver.log`.

## Screenshots

*(Fügen Sie hier Screenshots der Anwendung ein, um einen visuellen Eindruck zu vermitteln)*

*   **Hauptfenster (Konten & Aktionen):**
   ![image](https://github.com/user-attachments/assets/a259c8aa-9c8b-45d7-8485-56209e07e961)

*   **Archiv-Explorer:**
    ![image](https://github.com/user-attachments/assets/59420de1-0174-4cde-a610-e71afdd96a29)

*   **E-Mail-Vorschau:**
   ![image](https://github.com/user-attachments/assets/6598a8a0-def7-4f3b-8c6b-6c8a282d3ab1)


*   **E-Mail verfassen:**
    ![image](https://github.com/user-attachments/assets/efe9ca0a-6fc5-4b81-af98-580d3c9497b2)



## Voraussetzungen

*   **Python:** Version 3.7 oder höher wird empfohlen.
*   **Tkinter:** Wird für die GUI benötigt. Ist in den meisten Python-Distributionen für Windows und macOS enthalten. Unter Linux muss es eventuell separat installiert werden (z.B. `sudo apt-get install python3-tk` für Debian/Ubuntu).
*   **Python-Bibliotheken:**
    *   `keyring`: Zur sicheren Passwortspeicherung.
    *   `fuzzywuzzy` (Optional): Für die Suchfunktion im Archiv-Explorer. Verbessert die Suchqualität erheblich.
    *   `python-Levenshtein` (Optional, empfohlen für `fuzzywuzzy`): Beschleunigt die Berechnungen von `fuzzywuzzy` erheblich.

*   **Keyring Backend:** `keyring` benötigt ein Backend, um Passwörter speichern zu können.
    *   **Windows/macOS:** Normalerweise ist ein System-Backend vorhanden.
    *   **Linux:** Es muss eventuell ein Backend installiert werden (z.B. `SecretService` oder `KWallet`). Eine dateibasierte Alternative ist `keyrings.cryptfile` (`pip install keyrings.cryptfile`). Möglicherweise müssen Sie das Backend nach der Installation einmalig initialisieren oder ein Master-Passwort festlegen.

## Installation

1.  **Repository klonen oder herunterladen:**
    ```bash
    git clone <repository_url> # Ersetzen Sie <repository_url> durch die URL Ihres Git-Repositorys
    cd <repository_directory>
    ```
    Oder laden Sie den Quellcode als ZIP-Datei herunter und entpacken Sie ihn.

2.  **Python-Umgebung einrichten (Empfohlen):**
    Es wird dringend empfohlen, eine virtuelle Umgebung zu verwenden:
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # macOS / Linux
    source venv/bin/activate
    ```

3.  **Abhängigkeiten installieren:**
    Installieren Sie die benötigten Python-Bibliotheken. Um die optionale Suche und deren Beschleunigung zu nutzen:
    ```bash
    pip install keyring "fuzzywuzzy[speedup]"
    ```
    Wenn Sie `fuzzywuzzy` nicht benötigen, installieren Sie nur `keyring`:
    ```bash
    pip install keyring
    ```
    Wenn `keyring` unter Linux Probleme macht, installieren Sie zusätzlich ein dateibasiertes Backend (siehe [Voraussetzungen](#voraussetzungen)):
    ```bash
    pip install keyrings.cryptfile
    ```

4.  **Script ausführbar machen (Optional, Linux/macOS):**
    ```bash
    chmod +x ciphercore_email_suite.py # Ersetzen Sie den Dateinamen falls nötig
    ```

## Verwendung

Ersetzen Sie `ciphercore_email_suite.py` im Folgenden durch den tatsächlichen Namen Ihrer Python-Skriptdatei.

### GUI-Modus

Starten Sie die Anwendung ohne zusätzliche Argumente, um die grafische Benutzeroberfläche zu öffnen:

```bash
python ciphercore_email_suite.py
```

**Erste Schritte:**

1.  Beim ersten Start ist die Kontenliste leer.
2.  Klicken Sie auf **"Konto hinzufügen"**.
3.  Füllen Sie die Details für Ihr E-Mail-Konto aus:
    *   **Name:** Ein beliebiger Name zur Identifizierung (z.B. "Arbeit", "Privat").
    *   **Protokoll:** Wählen Sie IMAP oder POP3 für den E-Mail-Empfang.
    *   **Server (Posteingang):** Der IMAP- oder POP3-Server Ihres Anbieters (z.B. `imap.example.com`).
    *   **Port:** Der passende Port für den Server (z.B. 993 für IMAP SSL, 995 für POP3 SSL).
    *   **E-Mail Adresse:** Ihre vollständige E-Mail-Adresse.
    *   **Passwort:** Ihr E-Mail-Passwort. Dieses wird sicher im Keyring gespeichert.
    *   **SMTP Server (Postausgang):** Der Server zum Senden von E-Mails (z.B. `smtp.example.com`). Optional, aber für Senden/Antworten/Weiterleiten benötigt.
    *   **SMTP Port:** Der Port für den SMTP-Server (z.B. 587 für TLS/STARTTLS, 465 für SSL).
4.  Klicken Sie auf **"Speichern"**. Das Konto erscheint in der Liste.
5.  Wählen Sie das Konto in der Liste aus.
6.  **(Nur IMAP):** Klicken Sie auf **"Ordner auswählen"**, um die IMAP-Ordner zu laden und diejenigen auszuwählen, die Sie archivieren möchten. Speichern Sie die Auswahl.
7.  Klicken Sie auf **"Ausgewählte Ordner archivieren"**, um den Abruf- und Speichervorgang zu starten. Ein Fortschrittsfenster wird angezeigt.
8.  Verwenden Sie **"Archiv Explorer öffnen"**, um Ihre archivierten E-Mails zu durchsuchen und anzuzeigen.
9.  Verwenden Sie **"E-Mail verfassen"**, um neue E-Mails zu schreiben (erfordert konfiguriertes SMTP für das ausgewählte Konto).

### Kommandozeilenmodus (CLI)

Der CLI-Modus dient der automatisierten Archivierung ohne grafische Oberfläche.

**Syntax:**

```bash
python ciphercore_email_suite.py --cli --account_name "Konto Name" [--folders "Ordner1,Ordner2,..."] [--age_days TAGE]
```

**Argumente:**

*   `--cli`: (Erforderlich) Aktiviert den CLI-Modus.
*   `--account_name "Konto Name"`: (Erforderlich) Der Name des Kontos (wie in der GUI hinzugefügt, Groß-/Kleinschreibung wird ignoriert), das verarbeitet werden soll. Setzen Sie Namen mit Leerzeichen in Anführungszeichen.
*   `--folders "Ordner1,Ordner2,..."`: (Optional) Eine komma-separierte Liste von IMAP-Ordnern, die geprüft werden sollen. Wenn nicht angegeben, wird für IMAP standardmäßig nur `INBOX` geprüft. Für POP3 wird dieses Argument ignoriert (immer nur die Inbox).
*   `--age_days TAGE`: (Optional) Das Mindestalter (in Tagen), das eine E-Mail haben muss, um im `archiv`-Ordner gespeichert zu werden. E-Mails, die jünger sind, werden im `emails`-Ordner gespeichert. Standardwert ist `30`.

**Beispiele:**

1.  **Archiviere alle E-Mails älter als 60 Tage aus der INBOX und dem Ordner "Gesendet" des IMAP-Kontos "Arbeit":**
    ```bash
    python ciphercore_email_suite.py --cli --account_name "Arbeit" --folders "INBOX,Gesendet" --age_days 60
    ```

2.  **Archiviere alle E-Mails älter als 30 Tage (Standard) aus dem POP3-Konto "Privat":**
    ```bash
    python ciphercore_email_suite.py --cli --account_name "Privat"
    ```
    *(Hinweis: `--folders` ist hier irrelevant)*

3.  **Archiviere alle E-Mails älter als 7 Tage aus der INBOX des IMAP-Kontos "Backup Mail":**
    ```bash
    python ciphercore_email_suite.py --cli --account_name "Backup Mail" --age_days 7
    ```
    *(Hinweis: Nur INBOX wird geprüft, da `--folders` nicht angegeben ist)*

Der CLI-Modus gibt Fortschrittsinformationen auf der Konsole aus und schreibt detaillierte Logs in die Datei `email_archiver.log`.

## Konfiguration

### `accounts.txt`

Diese Datei wird automatisch im selben Verzeichnis wie das Skript erstellt und enthält die Konfigurationsdetails für Ihre E-Mail-Konten, **jedoch keine Passwörter**.

*   **Format:** Komma-separierte Werte (CSV), eine Zeile pro Konto.
*   **Spalten:** `Name,Server,Port,E-Mail Adresse,Protokoll,SMTP Server,SMTP Port`
*   **Beispielzeile:** `Arbeit,imap.firma.de,993,max.mustermann@firma.de,imap,smtp.firma.de,587`
*   **Bearbeitung:** Sie können diese Datei manuell bearbeiten, aber es wird empfohlen, Konten über die GUI hinzuzufügen oder zu entfernen, um Inkonsistenzen mit dem Keyring zu vermeiden.
*   **Sicherheit:** **Speichern Sie niemals Passwörter in dieser Datei!**

### Passwortverwaltung (Keyring)

Die Anwendung verwendet die `keyring`-Bibliothek, um Ihre E-Mail-Passwörter sicher zu speichern.

*   **Funktionsweise:** `keyring` interagiert mit dem sicheren Anmeldeinformationsspeicher Ihres Betriebssystems (z.B. Windows Credential Manager, macOS Keychain, Linux Secret Service/KWallet).
*   **Vorteil:** Passwörter werden nicht im Klartext gespeichert und sind durch die Sicherheitsmechanismen Ihres Betriebssystems geschützt.
*   **Einrichtung:** Normalerweise automatisch. Unter Linux müssen Sie eventuell ein kompatibles Backend installieren und konfigurieren (siehe [Voraussetzungen](#voraussetzungen)).
*   **Zugriff:** Wenn die Anwendung das Passwort für ein Konto benötigt (beim Hinzufügen, Abrufen oder Senden), fragt sie es bei `keyring` an. Sie müssen möglicherweise den Zugriff einmalig erlauben oder das Master-Passwort Ihres Schlüsselbunds eingeben.

## Archivstruktur

Archivierte E-Mails und Anhänge werden standardmäßig im Unterordner `EmailArchiv` (im Verzeichnis des Skripts) gespeichert. Die Struktur ist wie folgt aufgebaut:

```
EmailArchiv/
└── <Konto Name>/                 # Ein Ordner pro konfiguriertem Konto (gesäuberter Name)
    ├── archiv/                   # Enthält E-Mails, die älter als --age_days sind (CLI) oder bei GUI-Archivierung als alt eingestuft wurden
    │   └── <Original Ordnername>/ # Unterordner pro IMAP-Ordner (gesäubert, '/' wird zu '__') oder 'inbox' für POP3
    │       └── YYYY-MM-DD/       # Unterordner pro Archivierungstag
    │           ├── <Timestamp>_<Betreff>_<ID>.eml
    │           ├── ...           # Weitere .eml Dateien
    │           └── anhänge/      # Ordner für Anhänge (nur wenn vorhanden)
    │               ├── anhang1.pdf
    │               └── bild.jpg
    └── emails/                   # Enthält E-Mails, die jünger als --age_days sind (CLI) oder bei GUI-Archivierung als nicht alt eingestuft wurden
        └── <Original Ordnername>/
            └── YYYY-MM-DD/
                ├── <Timestamp>_<Betreff>_<ID>.eml
                └── anhänge/
                    └── ...
```

*   **`<Konto Name>`:** Abgeleitet vom Namen, den Sie beim Hinzufügen des Kontos vergeben haben (ungültige Zeichen werden ersetzt).
*   **`archiv` vs. `emails`:** Die Trennung erfolgt basierend auf dem Alter der E-Mail im Vergleich zum `age_days`-Parameter (Standard 30 Tage). Dies ist primär relevant für die CLI-Archivierung oder wenn Sie die Altersprüfung in der GUI-Logik beibehalten.
*   **`<Original Ordnername>`:** Der Name des IMAP-Ordners, aus dem die E-Mail stammt (gesäubert). Bei POP3 ist dies immer `inbox`. IMAP-Hierarchien (z.B. `A/B/C`) werden typischerweise zu `A__B__C`.
*   **`YYYY-MM-DD`:** Das Datum, an dem die Archivierung durchgeführt wurde.
*   **`.eml`-Dateien:** Die E-Mails im Rohformat. Der Dateiname enthält Zeitstempel, Betreff (gekürzt/gesäubert) und eine eindeutige ID.
*   **`anhänge`-Ordner:** Enthält alle Anhänge der E-Mails aus dem jeweiligen Tagesordner.

## Fehlerbehebung & Logging

*   **Logdatei:** Alle wichtigen Aktionen, Warnungen und Fehler werden in die Datei `email_archiver.log` im selben Verzeichnis wie das Skript geschrieben. Diese Datei ist die erste Anlaufstelle bei Problemen.
*   **Keyring-Probleme:** Wenn das Speichern oder Abrufen von Passwörtern fehlschlägt, prüfen Sie, ob ein `keyring`-Backend korrekt installiert und konfiguriert ist (siehe [Voraussetzungen](#voraussetzungen) und FAQ). Fehlermeldungen im Log oder in der GUI geben oft Hinweise.
*   **Verbindungsfehler:** Stellen Sie sicher, dass Servernamen, Ports und Protokolle korrekt sind und Ihr Netzwerk die Verbindung zu den E-Mail-Servern zulässt (Firewall, Antivirus).
*   **Authentifizierungsfehler:** Überprüfen Sie E-Mail-Adresse und Passwort. Manche Anbieter erfordern App-spezifische Passwörter, wenn Zwei-Faktor-Authentifizierung (2FA) aktiv ist.
*   **GUI friert ein:** Obwohl Abruf- und Sendevorgänge in separaten Threads laufen, können sehr große Operationen die GUI kurzzeitig verlangsamen. Bei dauerhaftem Einfrieren prüfen Sie die Logdatei auf Fehler.
*   **Suche funktioniert nicht:** Stellen Sie sicher, dass `fuzzywuzzy` und `python-Levenshtein` installiert sind (`pip install "fuzzywuzzy[speedup]"`).

## Häufig gestellte Fragen (FAQ)

**F: Warum wird `keyring` verwendet? Kann ich Passwörter nicht einfach in `accounts.txt` speichern?**
A: `keyring` wird aus Sicherheitsgründen verwendet. Das Speichern von Passwörtern im Klartext in einer Datei ist extrem unsicher. `keyring` nutzt die sicheren Speicher des Betriebssystems, was das Risiko eines Passwortdiebstahls erheblich reduziert.

**F: Ich bekomme `keyring` unter Linux nicht zum Laufen. Was kann ich tun?**
A: Stellen Sie sicher, dass ein kompatibles Backend wie `python3-secretstorage` (für GNOME/SecretService) oder `python3-kwallet` (für KDE) installiert ist. Alternativ installieren Sie das dateibasierte Backend mit `pip install keyrings.cryptfile`. Möglicherweise müssen Sie Ihren Schlüsselbund entsperren oder ein Master-Passwort festlegen. Prüfen Sie die `keyring`-Dokumentation für Details.

**F: Die Suche im Archiv-Explorer ist langsam oder findet nichts.**
A: Die Suche durchsucht den Inhalt von `.eml`-Dateien zur Laufzeit. Dies kann bei großen Archiven dauern. Stellen Sie sicher, dass `fuzzywuzzy` und idealerweise `python-Levenshtein` installiert sind (`pip install "fuzzywuzzy[speedup]"`), um die Suche zu aktivieren und zu beschleunigen. Die Qualität der Fuzzy-Suche hängt vom Suchbegriff und dem Inhalt ab.

**F: Kann die Anwendung E-Mails vom Server löschen (z.B. nach der Archivierung)?**
A: Nein, die Anwendung ist primär als Archivierungs- und Betrachtungswerkzeug konzipiert. Sie löscht keine E-Mails vom Server. Dies ist eine Sicherheitsmaßnahme, um Datenverlust zu vermeiden.

**F: Wie werden E-Mail-Anhänge gehandhabt?**
A: Anhänge werden aus den `.eml`-Dateien extrahiert und im `anhänge`-Unterordner des jeweiligen Tagesarchivs gespeichert. Die ursprüngliche `.eml`-Datei bleibt vollständig erhalten.

**F: Kann ich die Anwendung auf verschiedenen Betriebssystemen (Windows, macOS, Linux) verwenden?**
A: Ja, da die Anwendung in Python mit Tkinter geschrieben ist, sollte sie plattformübergreifend funktionieren, solange Python 3 und die Abhängigkeiten korrekt installiert sind. Tkinter- und Keyring-Verhalten können sich leicht zwischen den Systemen unterscheiden.

**F: Werden HTML-E-Mails korrekt angezeigt?**
A: Die E-Mail-Vorschau versucht, den `text/plain`-Teil einer E-Mail anzuzeigen. Wenn dieser nicht verfügbar ist, wird der `text/html`-Teil angezeigt, jedoch ohne komplexe Formatierungen, Bilder oder Stile (reiner Text des HTML). Es ist keine vollständige HTML-Rendering-Engine integriert.

**F: Die GUI friert beim Abrufen/Senden von E-Mails ein.**
A: Die zeitaufwändigen Operationen (Abrufen, Senden) werden in Hintergrund-Threads ausgeführt, um die GUI responsiv zu halten. Bei sehr vielen E-Mails oder langsamen Verbindungen kann es dennoch zu kurzen Verzögerungen kommen. Wenn die GUI dauerhaft einfriert, deutet dies auf einen Fehler hin – bitte prüfen Sie die `email_archiver.log`.

**F: Ich erhalte einen SMTP-Authentifizierungsfehler, obwohl mein Passwort korrekt ist.**
A: Manche E-Mail-Anbieter (wie Google Mail, Outlook.com) erfordern die Verwendung von "App-spezifischen Passwörtern", wenn die Zwei-Faktor-Authentifizierung (2FA) aktiviert ist. Sie müssen ein solches Passwort in den Sicherheitseinstellungen Ihres E-Mail-Kontos generieren und dieses dann in der CipherCore E-Mail Suite verwenden.

## Glossar

*   **IMAP (Internet Message Access Protocol):** Ein Protokoll zum Abrufen von E-Mails. E-Mails bleiben auf dem Server gespeichert, und Ordnerstrukturen werden synchronisiert.
*   **POP3 (Post Office Protocol version 3):** Ein älteres Protokoll zum Abrufen von E-Mails. Typischerweise werden E-Mails auf den Client heruntergeladen und vom Server gelöscht (obwohl dies konfigurierbar ist). Unterstützt keine Ordnersynchronisation.
*   **SMTP (Simple Mail Transfer Protocol):** Das Standardprotokoll zum Senden von E-Mails.
*   **.eml-Datei:** Ein Dateiformat zur Speicherung einzelner E-Mail-Nachrichten, einschließlich Header, Textkörper und Anhängen, im MIME-Standard.
*   **Keyring / Schlüsselbund:** Ein sicherer Speicher des Betriebssystems zur Verwaltung von Anmeldeinformationen wie Passwörtern und Schlüsseln.
*   **CLI (Command Line Interface):** Eine textbasierte Schnittstelle zur Interaktion mit einem Programm über Kommandozeilenbefehle.
*   **GUI (Graphical User Interface):** Eine grafische Benutzeroberfläche mit Fenstern, Schaltflächen und anderen visuellen Elementen zur Bedienung eines Programms.
*   **Fuzzy Search / Unscharfe Suche:** Eine Suchtechnik, die auch dann Treffer findet, wenn der Suchbegriff nicht exakt mit dem Text übereinstimmt (z.B. bei Tippfehlern oder ähnlichen Wörtern).
*   **Header (E-Mail):** Metadaten einer E-Mail, wie Absender (From), Empfänger (To, Cc, Bcc), Betreff (Subject) und Datum (Date).
*   **Payload (E-Mail):** Der eigentliche Inhalt eines Teils einer E-Mail-Nachricht (z.B. der Textkörper oder der Inhalt eines Anhangs), oft kodiert (z.B. Base64).
*   **MIME (Multipurpose Internet Mail Extensions):** Ein Standard, der das Format von E-Mails erweitert, um Nicht-Text-Inhalte wie Anhänge, verschiedene Zeichensätze und mehrteilige Nachrichten zu unterstützen.
*   **Threading (in Programmierung):** Eine Technik, die es einem Programm ermöglicht, mehrere Aufgaben (scheinbar) gleichzeitig auszuführen, um z.B. die Reaktionsfähigkeit der GUI während langer Operationen zu verbessern.
*   **RFC 822 / RFC 2822 / RFC 5322:** Eine Reihe von Standards, die das Format von E-Mail-Nachrichten definieren.
*   **SSL/TLS (Secure Sockets Layer / Transport Layer Security):** Verschlüsselungsprotokolle zur Sicherung der Kommunikation über ein Netzwerk, häufig verwendet für IMAP, POP3 und SMTP (z.B. Ports 993, 995, 465).
*   **STARTTLS:** Ein SMTP-Befehl, der eine unverschlüsselte Verbindung auf einem Standard-Port (wie 587 oder 25) zu einer verschlüsselten TLS-Verbindung aufwertet, falls vom Server unterstützt.

## Lizenz

Dieses Projekt steht unter der MIT-Lizenz. Siehe die Datei `LICENSE` für weitere Details.

```markdown
MIT License

Copyright (c) [Jahr] [Name des Copyright-Inhabers]

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



## Kontakt & Support

Bei Problemen, Fragen oder Vorschlägen:

*   Öffnen Sie ein **Issue** im GitHub-Repository (falls vorhanden).
*   Kontaktieren Sie den Autor: `support@ciphercore.de` 

---

