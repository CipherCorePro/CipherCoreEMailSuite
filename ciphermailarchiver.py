import tkinter as tk
from tkinter import ttk, messagebox, Listbox, Scrollbar, END
import imaplib
import poplib
import email
import os
import datetime
import logging
import keyring  # Für die sichere Passwortspeicherung
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
import traceback # Import für Traceback
import unicodedata # Import für Dateinamen-Normalisierung

# Einrichtung des Loggings für Debugging und Fehlerbehandlung
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@dataclass
class EmailAccount:
    """
    Datenklasse zur Speicherung von E-Mail-Kontoinformationen.

    Diese Klasse dient als Datenstruktur, um die notwendigen Informationen für ein E-Mail-Konto zu bündeln.
    Dazu gehören der Name des Kontos, Serveradresse, Portnummer, E-Mail-Adresse, Protokolltyp (IMAP oder POP3)
    und das temporär gespeicherte Passwort. Das Passwort wird über `keyring` sicher verwaltet.

    Attribute:
        name (str): Ein benutzerdefinierter Name für das E-Mail-Konto (z.B. 'Persönlich', 'Arbeit').
        server (str): Die Adresse des E-Mail-Servers (z.B. 'imap.gmail.com', 'pop.web.de').
        port (int): Die Portnummer für die Serververbindung (z.B. 993 für IMAP SSL, 995 für POP3 SSL).
        email_address (str): Die vollständige E-Mail-Adresse des Kontos.
        protocol (str): Das verwendete Protokoll zum E-Mail-Abruf ('imap' oder 'pop3').
        password (str): Das Passwort für das E-Mail-Konto (wird hier temporär gehalten, sichere Speicherung via Keyring).
    """
    name: str
    server: str
    port: int
    email_address: str
    protocol: str  # 'imap' oder 'pop3'
    password: str # Passwort wird hier temporär gehalten, sichere Speicherung via Keyring

class EmailArchiverGUI(tk.Tk):
    """
    GUI-Klasse für die E-Mail-Archivierungsanwendung.

    Diese Klasse erweitert `tkinter.Tk` und implementiert die Hauptanwendung zur Verwaltung und
    Archivierung von E-Mails. Sie bietet eine grafische Benutzeroberfläche zur Konfiguration von
    E-Mail-Konten, zum manuellen Starten des E-Mail-Abrufs und zur Anzeige des Verarbeitungsstatus.

    Die Anwendung unterstützt das Hinzufügen, Entfernen und Auswählen von E-Mail-Konten.
    E-Mails werden basierend auf dem Datum in 'emails' oder 'archiv' Ordnern gespeichert.
    Anhänge werden ebenfalls heruntergeladen und in separaten Ordnern abgelegt.

    Attribute:
        accounts (list[EmailAccount]): Liste der konfigurierten E-Mail-Konten.
        selected_account_index (int | None): Index des aktuell ausgewählten Kontos in der `accounts` Liste oder None, wenn keines ausgewählt ist.
        account_listbox (tk.Listbox): Listbox-Widget zur Anzeige der E-Mail-Konten in der GUI.
        fetch_button (ttk.Button): Button zum Auslösen des E-Mail-Abruf- und Verarbeitungsprozesses.
        status_label (ttk.Label): Label zur Anzeige von Statusmeldungen am unteren Fensterrand.
        name_entry (ttk.Entry): Eingabefeld für den Kontonamen im Fenster zum Hinzufügen von Konten.
        server_entry (ttk.Entry): Eingabefeld für die Serveradresse im Fenster zum Hinzufügen von Konten.
        port_entry (ttk.Entry): Eingabefeld für die Portnummer im Fenster zum Hinzufügen von Konten.
        email_entry (ttk.Entry): Eingabefeld für die E-Mail-Adresse im Fenster zum Hinzufügen von Konten.
        password_entry (ttk.Entry): Eingabefeld für das Passwort im Fenster zum Hinzufügen von Konten.
        protocol_entry (ttk.Entry): Eingabefeld für das Protokoll im Fenster zum Hinzufügen von Konten.

    Methods:
        __init__(self): Initialisiert die GUI und erstellt die Benutzeroberfläche.
        _load_accounts(self): Lädt gespeicherte E-Mail-Konten beim Start der Anwendung.
        _save_accounts(self): Speichert E-Mail-Konten, inklusive Passwörter in `keyring`.
        _create_widgets(self): Erstellt alle GUI-Elemente (Buttons, Listen, Labels, etc.).
        _update_account_listbox(self): Aktualisiert die Anzeige der E-Mail-Konten in der Listbox.
        _add_account_window(self): Öffnet ein Fenster zum Hinzufügen eines neuen E-Mail-Kontos.
        _save_new_account(self): Speichert ein neu hinzugefügtes E-Mail-Konto.
        _remove_account(self): Entfernt ein ausgewähltes E-Mail-Konto.
        _fetch_and_process_emails(self): Hauptfunktion zum Abrufen und Verarbeiten von E-Mails.
        _fetch_email_ids(self, account): Ruft E-Mail-IDs vom Server ab (IMAP oder POP3).
        _process_single_email(self, account, email_id): Verarbeitet eine einzelne E-Mail.
        _get_email_date(self, email_msg): Extrahiert das Datum aus einer E-Mail-Nachricht.
        _is_older_than_days(self, email_date: datetime.datetime | None, days: int = 5) -> bool: Prüft, ob ein Datum älter als eine Anzahl von Tagen ist.
        _download_email(self, account, email_id): Lädt den Rohinhalt einer E-Mail vom Server herunter.
        _create_account_folder(self, account): Erstellt den Basisordner für ein E-Mail-Konto.
        _create_target_folder(self, account_folder, target_folder): Erstellt Zielordner (emails/archiv) innerhalb des Kontoordners.
        _save_email(self, account, email_msg, target_folder): Speichert den E-Mail-Inhalt als Textdatei.
        _process_attachments(self, account, email_msg, target_folder): Verarbeitet und speichert E-Mail-Anhänge.
        update_status(self, message: str, error: bool = False): Aktualisiert die Statusanzeige in der GUI und färbt sie bei Fehlern rot.
    """
    def __init__(self):
        """
        Initialisiert die EmailArchiverGUI-Anwendung.

        Konfiguriert das Hauptfenster, lädt gespeicherte Konten und erstellt die GUI-Elemente.
        """
        super().__init__()
        self.title("CipherCore E-Mail Archivierer")
        self.geometry("800x600")
        self.resizable(False, False) # Fenstergröße fixieren

        self.accounts = [] # Liste zum Speichern von EmailAccount-Objekten
        self.selected_account_index = None # Index des ausgewählten Kontos in der Liste

        self._load_accounts() # Konten beim Start laden
        self._create_widgets()

    def _load_accounts(self):
        """
        Lädt E-Mail-Konten aus der Konfigurationsdatei 'accounts.txt' und keyring.

        Liest die Konteninformationen aus der Datei, wobei jede Zeile ein Konto repräsentiert.
        Das Passwort wird sicher aus dem keyring abgerufen. Fehlerhafte Zeilen oder fehlende Passwörter
        werden protokolliert und ignoriert, um die Anwendung nicht zu unterbrechen.

        Raises:
            Exception: Zeigt eine Fehlermeldung an und protokolliert den Fehler, falls das Laden der Konten fehlschlägt.
        """
        try:
            if not os.path.exists("accounts.txt"):
                logging.info("Kontendatei nicht gefunden. Starte mit leerer Kontenliste.")
                return

            with open("accounts.txt", "r") as f:
                for line in f:
                    try:
                        name, server, port, email_address, protocol = line.strip().split(",")
                        password = keyring.get_password("EmailArchiver", email_address) # Passwort sicher abrufen
                        if password:
                            self.accounts.append(EmailAccount(name, server, int(port), email_address, protocol, password))
                        else:
                            logging.warning(f"Passwort für Konto {email_address} nicht in keyring gefunden. Konto wird ignoriert.")
                    except ValueError:
                        logging.warning(f"Ungültige Zeile in accounts.txt gefunden: {line.strip()}. Zeile wird ignoriert.")

        except Exception as e:
            logging.error(f"Fehler beim Laden der Konten: {e}\n{traceback.format_exc()}") # Traceback hinzugefügt
            messagebox.showerror("Fehler", "Fehler beim Laden der Konten.")

    def _save_accounts(self):
        """
        Speichert E-Mail-Konten in der Datei 'accounts.txt' und keyring.

        Schreibt die aktuellen Konteninformationen in die Datei. Passwörter werden sicher im keyring gespeichert
        und nicht in der Klartext-Datei. Im Fehlerfall wird eine Fehlermeldung angezeigt und geloggt.

        Raises:
            Exception: Zeigt eine Fehlermeldung an und protokolliert den Fehler, falls das Speichern der Konten fehlschlägt.
        """
        try:
            with open("accounts.txt", "w") as f:
                for account in self.accounts:
                    keyring.set_password("EmailArchiver", account.email_address, account.password) # Passwort sicher speichern
                    f.write(f"{account.name},{account.server},{account.port},{account.email_address},{account.protocol}\n")
            logging.info("Konten erfolgreich gespeichert.")
        except Exception as e:
            logging.error(f"Fehler beim Speichern der Konten: {e}")
            messagebox.showerror("Fehler", "Fehler beim Speichern der Konten.")

    def _create_widgets(self):
        """
        Erstellt und platziert alle GUI-Elemente im Hauptfenster.

        Diese Methode erzeugt die Rahmen für die Kontenverwaltung und E-Mail-Verarbeitung,
        die Listenbox zur Anzeige der Konten, Buttons zum Hinzufügen und Entfernen von Konten,
        den Button zum Starten der E-Mail-Verarbeitung und das Statuslabel.
        """
        # Rahmen für Kontenverwaltung
        accounts_frame = ttk.LabelFrame(self, text="E-Mail Konten verwalten")
        accounts_frame.pack(padx=10, pady=10, fill=tk.X)

        # Kontenliste
        self.account_listbox = Listbox(accounts_frame, height=5, selectmode=tk.SINGLE)
        self.account_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar = Scrollbar(accounts_frame, orient=tk.VERTICAL)
        scrollbar.config(command=self.account_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        self.account_listbox.config(yscrollcommand=scrollbar.set)
        self._update_account_listbox() # Liste beim GUI-Start befüllen

        # Buttons für Kontenverwaltung
        add_account_button = ttk.Button(accounts_frame, text="Konto hinzufügen", command=self._add_account_window)
        add_account_button.pack(side=tk.LEFT, padx=5, pady=5)
        remove_account_button = ttk.Button(accounts_frame, text="Konto entfernen", command=self._remove_account)
        remove_account_button.pack(side=tk.LEFT, padx=5, pady=5)

        # Rahmen für E-Mail-Verarbeitung
        process_frame = ttk.LabelFrame(self, text="E-Mail Verarbeitung starten")
        process_frame.pack(padx=10, pady=10, fill=tk.X)

        # Button für E-Mail-Verarbeitung
        self.fetch_button = ttk.Button(process_frame, text="E-Mails abrufen und verarbeiten", command=self._fetch_and_process_emails)
        self.fetch_button.pack(side=tk.LEFT, padx=5, pady=5)

        # Statusanzeige
        self.status_label = ttk.Label(self, text="Bereit")
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5, anchor="w") # Status linksbündig

    def _update_account_listbox(self):
        """
        Aktualisiert die Listbox mit den aktuell geladenen E-Mail-Konten.

        Leert die Listbox und fügt für jedes Konto in `self.accounts` einen Eintrag hinzu,
        der den Kontonamen und die E-Mail-Adresse anzeigt.
        """
        self.account_listbox.delete(0, END)
        for account in self.accounts:
            self.account_listbox.insert(END, account.name + f" ({account.email_address})")

    def _add_account_window(self):
        """
        Öffnet ein neues Toplevel-Fenster zum Hinzufügen eines E-Mail-Kontos.

        Erstellt ein separates Fenster mit Eingabefeldern für die Kontodetails (Name, Server, Port,
        E-Mail-Adresse, Passwort, Protokoll) und einem Button zum Speichern des neuen Kontos.
        """
        add_window = tk.Toplevel(self)
        add_window.title("Konto hinzufügen")
        add_window.resizable(False, False) # Fenstergröße fixieren

        # Labels und Eingabefelder
        row_num = 0

        ttk.Label(add_window, text="Name (z.B. Arbeit):").grid(row=row_num, column=0, padx=5, pady=5, sticky="e")
        self.name_entry = ttk.Entry(add_window)
        self.name_entry.grid(row=row_num, column=1, padx=5, pady=5)
        row_num += 1

        ttk.Label(add_window, text="Server (z.B. imap.gmail.com):").grid(row=row_num, column=0, padx=5, pady=5, sticky="e")
        self.server_entry = ttk.Entry(add_window)
        self.server_entry.grid(row=row_num, column=1, padx=5, pady=5)
        row_num += 1

        ttk.Label(add_window, text="Port (z.B. 993 für IMAP SSL):").grid(row=row_num, column=0, padx=5, pady=5, sticky="e")
        self.port_entry = ttk.Entry(add_window)
        self.port_entry.grid(row=row_num, column=1, padx=5, pady=5)
        row_num += 1

        ttk.Label(add_window, text="E-Mail Adresse:").grid(row=row_num, column=0, padx=5, pady=5, sticky="e")
        self.email_entry = ttk.Entry(add_window)
        self.email_entry.grid(row=row_num, column=1, padx=5, pady=5)
        row_num += 1

        ttk.Label(add_window, text="Passwort:").grid(row=row_num, column=0, padx=5, pady=5, sticky="e")
        self.password_entry = ttk.Entry(add_window, show="*") # Passwort verbergen
        self.password_entry.grid(row=row_num, column=1, padx=5, pady=5)
        row_num += 1

        ttk.Label(add_window, text="Protokoll (imap/pop3):").grid(row=row_num, column=0, padx=5, pady=5, sticky="e")
        self.protocol_entry = ttk.Entry(add_window)
        self.protocol_entry.grid(row=row_num, column=1, padx=5, pady=5)
        row_num += 1

        # Speichern Button
        save_button = ttk.Button(add_window, text="Speichern", command=self._save_new_account)
        save_button.grid(row=row_num, column=0, columnspan=2, pady=10)

        # Eingabefelder fokussieren für bessere UX
        self.server_entry.focus_set() # Fokus auf Server-Eingabefeld gesetzt

    def _save_new_account(self):
        """
        Speichert ein neues E-Mail-Konto basierend auf den Eingaben im AddAccount-Fenster.

        Liest die Werte aus den Eingabefeldern, validiert sie, erstellt ein `EmailAccount`-Objekt,
        fügt es der Kontenliste hinzu, speichert die Konten und aktualisiert die GUI.
        Bei Fehlern während der Validierung oder Speicherung wird eine Fehlermeldung angezeigt.

        Raises:
            ValueError: Wenn nicht alle Felder ausgefüllt sind oder das Protokoll ungültig ist.
            Exception: Wenn ein unerwarteter Fehler beim Speichern des Kontos auftritt.
        """
        name = self.name_entry.get()
        server = self.server_entry.get()
        port = self.port_entry.get()
        email_address = self.email_entry.get()
        password = self.password_entry.get()
        protocol = self.protocol_entry.get().lower()
        window = self.name_entry.winfo_toplevel() # TopLevel Window ermitteln

        try:
            if not all([name, server, port, email_address, password, protocol]):
                raise ValueError("Bitte alle Felder ausfüllen.")
            port = int(port) # Port in Integer umwandeln
            if protocol not in ('imap', 'pop3'):
                raise ValueError("Protokoll muss 'imap' oder 'pop3' sein.")

            new_account = EmailAccount(name, server, port, email_address, protocol, password)
            self.accounts.append(new_account)
            self._save_accounts() # Konten in Datei speichern (inkl. Passwort in keyring)
            self._update_account_listbox() # Listbox aktualisieren
            window.destroy() # Fenster schließen
            messagebox.showinfo("Erfolg", "Konto erfolgreich hinzugefügt.")
        except ValueError as ve:
            messagebox.showerror("Fehler", f"Ungültige Eingabe: {ve}")
        except Exception as e:
            logging.error(f"Fehler beim Speichern des Kontos: {e}")
            messagebox.showerror("Fehler", f"Fehler beim Speichern des Kontos: {e}")

    def _remove_account(self):
        """
        Entfernt das ausgewählte E-Mail-Konto aus der Liste und der Konfiguration.

        Ermittelt das ausgewählte Konto aus der Listbox, fragt den Benutzer um Bestätigung,
        entfernt das Konto aus der internen Liste, speichert die aktualisierte Kontenliste,
        löscht das Passwort aus dem keyring und aktualisiert die GUI-Anzeige.

        Raises:
            IndexError: Wenn kein Konto zum Entfernen ausgewählt wurde oder die Auswahl ungültig ist.
            Exception: Wenn ein unerwarteter Fehler beim Entfernen des Kontos auftritt.
        """
        selected_indices = self.account_listbox.curselection()
        if not selected_indices:
            messagebox.showinfo("Hinweis", "Bitte wählen Sie ein Konto zum Entfernen aus.")
            return

        if messagebox.askyesno("Bestätigung", "Möchten Sie das ausgewählte Konto wirklich entfernen?"):
            try:
                index_to_remove = int(selected_indices[0]) # Index des ausgewählten Elements
                email_address_to_remove = self.accounts[index_to_remove].email_address # Email Adresse vor dem Löschen merken
                del self.accounts[index_to_remove] # Konto aus der Liste entfernen
                self._save_accounts() # Aktualisierte Kontenliste speichern (Passwort in keyring bleibt bestehen, wird aber nicht mehr verwendet)
                keyring.delete_password("EmailArchiver", email_address_to_remove) # Passwort aus Keyring löschen
                self._update_account_listbox() # Listbox aktualisieren
                messagebox.showinfo("Erfolg", "Konto erfolgreich entfernt.")
            except IndexError:
                messagebox.showerror("Fehler", "Ungültige Kontoauswahl zum Entfernen.")
            except Exception as e:
                logging.error(f"Fehler beim Entfernen des Kontos: {e}")
                messagebox.showerror("Fehler", f"Fehler beim Entfernen des Kontos: {e}")

    def _fetch_and_process_emails(self):
        """
        Hauptfunktion zum Starten des E-Mail-Abrufs und der Verarbeitung für das ausgewählte Konto.

        Diese Methode wird durch den "E-Mails abrufen und verarbeiten" Button ausgelöst.
        Sie ermittelt das ausgewählte Konto, deaktiviert den Fetch-Button während der Verarbeitung,
        ruft die E-Mail-IDs ab, verarbeitet jede E-Mail einzeln, zeigt einen Fortschrittsbalken an
        und aktualisiert die Statusanzeige. Nach Abschluss oder bei Fehlern wird der Fetch-Button
        wieder aktiviert.

        Raises:
            Exception: Fängt alle Fehler während des E-Mail-Abrufs und der Verarbeitung ab,
                       zeigt eine Fehlermeldung an und aktiviert den Fetch-Button wieder.
        """
        selected_indices = self.account_listbox.curselection()
        if not selected_indices:
            messagebox.showinfo("Hinweis", "Bitte wählen Sie ein E-Mail-Konto aus der Liste.")
            return

        self.selected_account_index = int(selected_indices[0]) # Index des ausgewählten Kontos speichern
        selected_account = self.accounts[self.selected_account_index]

        # GUI-Elemente deaktivieren während der Verarbeitung
        self.fetch_button.config(state=tk.DISABLED)
        try:
            self.update_status(f"Starte E-Mail-Abruf für Konto: {selected_account.name}...")
            email_ids = self._fetch_email_ids(selected_account) # E-Mail IDs abrufen
            if email_ids:
                email_count = len(email_ids)
                self.update_status(f"Lade {email_count} E-Mails herunter und verarbeite sie...")
                progress_window = tk.Toplevel(self)
                progress_window.title("E-Mail Verarbeitung")
                progress_window.resizable(False, False)
                progress_label = ttk.Label(progress_window, text="Verarbeite E-Mails...")
                progress_label.pack(padx=20, pady=10)
                progressbar = ttk.Progressbar(progress_window, orient=tk.HORIZONTAL, length=300, mode='determinate')
                progressbar.pack(padx=20, pady=10)
                progressbar["maximum"] = email_count
                processed_count = 0

                for email_id in email_ids:
                    self._process_single_email(selected_account, email_id)
                    processed_count += 1
                    progressbar["value"] = processed_count
                    progress_window.update_idletasks() # GUI aktualisieren während der Verarbeitung

                progress_window.destroy() # Fortschrittsfenster schließen
                self.update_status("E-Mail-Verarbeitung abgeschlossen.")
                messagebox.showinfo("Erfolg", "E-Mail-Verarbeitung abgeschlossen.")
            else:
                self.update_status("Keine neuen E-Mails gefunden.")
                messagebox.showinfo("Hinweis", "Keine neuen E-Mails gefunden.")

        except Exception as e:
            logging.error(f"Fehler bei der E-Mail-Verarbeitung: {e}")
            self.update_status(f"Fehler bei der E-Mail-Verarbeitung: {e}", error=True) # Fehler im Status anzeigen und rot färben
            messagebox.showerror("Fehler", f"Fehler bei der E-Mail-Verarbeitung: {e}")
        finally:
            # GUI-Elemente wieder aktivieren
            self.fetch_button.config(state=tk.NORMAL)

    def _fetch_email_ids(self, account) -> list[str]:
        """
        Ruft die IDs aller E-Mails vom Server ab, basierend auf dem Konto-Protokoll (IMAP oder POP3).

        Verbindet sich mit dem E-Mail-Server unter Verwendung des angegebenen Protokolls, loggt sich ein und
        ruft die IDs aller E-Mails im Posteingang ab. Für IMAP wird 'SEARCH ALL' verwendet, für POP3 werden
        die Nachrichten-Nummern von 1 bis zur Anzahl der Nachrichten generiert.

        Args:
            account (EmailAccount): Das E-Mail-Konto, von dem die IDs abgerufen werden sollen.

        Returns:
            list[str]: Eine Liste von E-Mail-IDs (Strings) oder eine leere Liste, falls keine E-Mails gefunden wurden
                       oder ein Fehler aufgetreten ist. Im Fehlerfall wird eine Fehlermeldung in der GUI angezeigt.

        Raises:
            ValueError: Wenn ein ungültiges Protokoll im Konto konfiguriert ist.
            imaplib.IMAP4.error: Wenn ein IMAP-spezifischer Fehler auftritt (z.B. Login-Fehler, Server nicht erreichbar).
            poplib.error_proto: Wenn ein POP3-spezifischer Fehler auftritt.
            Exception: Für alle anderen unerwarteten Fehler beim Abrufen der E-Mail-IDs.
        """
        mail = None
        try:
            if account.protocol == 'imap':
                mail = imaplib.IMAP4_SSL(account.server, account.port)
                mail.login(account.email_address, account.password)
                mail.select("inbox") # Posteingang auswählen
                status, email_ids = mail.search(None, 'ALL') # Alle E-Mail IDs abrufen
                if status == "OK":
                    id_list = email_ids[0].split() # Liste der IDs erstellen
                    return id_list
                else:
                    raise imaplib.IMAP4.error(f"IMAP Suche fehlgeschlagen: {status}") # Spezifischere Exception werfen
            elif account.protocol == 'pop3':
                mail = poplib.POP3_SSL(account.server, account.port)
                mail.user(account.email_address)
                mail.pass_(account.password)
                num_messages = mail.stat()[0] # Anzahl der E-Mails abrufen
                if num_messages > 0:
                    return [str(i) for i in range(1, num_messages + 1)] # IDs als Liste von Strings (POP3 IDs starten bei 1)
                else:
                    return [] # Keine E-Mails
            else:
                raise ValueError("Ungültiges Protokoll.")
        except ValueError as e:
            logging.error(f"Protokoll Fehler beim Abrufen der E-Mail-IDs für Konto {account.email_address}: {e}")
            self.update_status(f"Protokoll Fehler: {e}", error=True)
            messagebox.showerror("Fehler", f"Protokoll Fehler: {e}")
            return [] # Leere Liste zurückgeben, um Verarbeitung fortzusetzen oder Abbruch anders zu handhaben
        except imaplib.IMAP4.error as e:
            error_message = str(e).lower()
            if "authentication failed" in error_message:
                self.update_status("Anmeldung fehlgeschlagen. Bitte prüfen Sie Ihre Anmeldedaten.", error=True)
                messagebox.showerror("Fehler", "Anmeldung fehlgeschlagen. Bitte prüfen Sie Ihre Anmeldedaten.")
            elif "connection timed out" in error_message or "server unavailable" in error_message:
                self.update_status("Der Server ist nicht erreichbar. Prüfen Sie Ihre Internetverbindung und Servereinstellungen.", error=True)
                messagebox.showerror("Fehler", "Der Server ist nicht erreichbar. Prüfen Sie Ihre Internetverbindung und Servereinstellungen.")
            else:
                self.update_status(f"IMAP Fehler beim Abrufen der E-Mail-IDs: {e}", error=True)
                messagebox.showerror("Fehler", f"IMAP Fehler: {e}")
            logging.error(f"IMAP Fehler beim Abrufen der E-Mail-IDs für Konto {account.email_address}: {e}")

            return [] # Leere Liste zurückgeben
        except poplib.error_proto as e:
            error_message = str(e).lower()
            if "authentication failed" in error_message:
                self.update_status("Anmeldung fehlgeschlagen. Bitte prüfen Sie Ihre Anmeldedaten.", error=True)
                messagebox.showerror("Fehler", "Anmeldung fehlgeschlagen. Bitte prüfen Sie Ihre Anmeldedaten.")
            elif "connection timed out" in error_message or "connection refused" in error_message: # "connection refused" hinzugefügt
                self.update_status("Der Server ist nicht erreichbar. Prüfen Sie Ihre Internetverbindung und Servereinstellungen.", error=True)
                messagebox.showerror("Fehler", "Der Server ist nicht erreichbar. Prüfen Sie Ihre Internetverbindung und Servereinstellungen.")
            else:
                self.update_status(f"POP3 Fehler beim Abrufen der E-Mail-IDs: {e}", error=True)
                messagebox.showerror("Fehler", f"POP3 Fehler: {e}")
            logging.error(f"POP3 Fehler beim Abrufen der E-Mail-IDs für Konto {account.email_address}: {e}")
            return [] # Leere Liste zurückgeben
        except Exception as e:
            logging.error(f"Unerwarteter Fehler beim Abrufen der E-Mail-IDs für Konto {account.email_address}: {e}")
            self.update_status(f"Fehler beim Abrufen der E-Mail-IDs: {e}", error=True)
            messagebox.showerror("Fehler", f"Fehler beim Abrufen der E-Mail-IDs: {e}")
            return [] # Leere Liste zurückgeben
        finally:
            if mail:
                try:
                    if account.protocol == 'imap':
                        mail.logout()
                    elif account.protocol == 'pop3':
                        mail.quit()
                except Exception as e:
                    logging.error(f"Fehler beim Schließen der Verbindung für Konto {account.email_address}: {e}")

    def _process_single_email(self, account, email_id):
        """
        Verarbeitet eine einzelne E-Mail anhand ihrer ID.

        Lädt die E-Mail herunter, extrahiert das Datum, bestimmt den Zielordner ('emails' oder 'archiv'
        basierend auf dem Alter der E-Mail), speichert die E-Mail und verarbeitet die Anhänge.

        Args:
            account (EmailAccount): Das E-Mail-Konto, zu dem die E-Mail gehört.
            email_id (str): Die ID der E-Mail, die verarbeitet werden soll.
        """
        try:
            raw_email = self._download_email(account, email_id) # E-Mail herunterladen
            if raw_email:
                email_msg = email.message_from_bytes(raw_email) # E-Mail-Nachricht erstellen
                email_date = self._get_email_date(email_msg) # E-Mail Datum extrahieren
                if self._is_older_than_days(email_date, 5): # Prüfen, ob älter als 5 Tage
                    target_folder = "archiv"
                else:
                    target_folder = "emails"

                self._save_email(account, email_msg, target_folder) # E-Mail speichern mit Zielordner
                self._process_attachments(account, email_msg, target_folder) # Anhänge verarbeiten mit Zielordner
        except Exception as e:
            logging.error(f"Fehler beim Verarbeiten der E-Mail ID {email_id} für Konto {account.email_address}: {e}")
            self.update_status(f"Fehler beim Verarbeiten der E-Mail ID {email_id}: {e}", error=True)

    def _get_email_date(self, email_msg: email.message.Message) -> datetime.datetime | None:
        """
        Extrahiert das Datum aus dem 'Date'-Header einer E-Mail-Nachricht.

        Verwendet `parsedate_to_datetime` um das Datumsformat des Headers in ein datetime-Objekt zu konvertieren.

        Args:
            email_msg (email.message.Message): Die E-Mail-Nachricht.

        Returns:
            datetime.datetime | None: Das Datum der E-Mail als datetime-Objekt oder None, falls kein Datum gefunden wurde.
        """
        date_str = email_msg.get('date')
        if date_str:
            return parsedate_to_datetime(date_str)
        return None

    def _is_older_than_days(self, email_date: datetime.datetime | None, days: int = 5) -> bool:
        """
        Prüft, ob ein gegebenes Datum älter als eine bestimmte Anzahl von Tagen ist.

        Vergleicht das E-Mail-Datum mit dem aktuellen Datum in UTC-Zeit.

        Args:
            email_date (datetime.datetime | None): Das zu prüfende Datum. Kann None sein, wenn kein Datum extrahiert wurde.
            days (int): Die Anzahl der Tage, die das Datum mindestens alt sein muss, um als 'älter' zu gelten.

        Returns:
            bool: True, wenn das E-Mail-Datum älter als die angegebene Anzahl von Tagen ist, sonst False.
                    Gibt False zurück, wenn `email_date` None ist.
        """
        if not email_date:
            return False  # Wenn kein Datum vorhanden, nicht archivieren (oder Standardverhalten definieren)

        now = datetime.datetime.now(datetime.timezone.utc) # UTC Zeit verwenden für Vergleiche
        time_difference = now - email_date
        return time_difference > datetime.timedelta(days=days)


    def _download_email(self, account, email_id) -> bytes | None:
        """
        Lädt den Rohinhalt einer einzelnen E-Mail vom Server herunter.

        Verwendet das Protokoll des Kontos (IMAP oder POP3), um die E-Mail mit der gegebenen ID vom Server
        herunterzuladen. Für IMAP wird 'FETCH (RFC822)' verwendet, für POP3 'RETR'.

        Args:
            account (EmailAccount): Das E-Mail-Konto, von dem die E-Mail heruntergeladen werden soll.
            email_id (str): Die ID der E-Mail, die heruntergeladen werden soll.

        Returns:
            bytes | None: Der Rohinhalt der E-Mail als Bytes-Objekt oder None im Fehlerfall.

        Raises:
            ValueError: Wenn ein ungültiges Protokoll im Konto konfiguriert ist.
            imaplib.IMAP4.error: Wenn ein IMAP-spezifischer Fehler auftritt (z.B. Login-Fehler, Server nicht erreichbar, Fetch-Fehler).
            poplib.error_proto: Wenn ein POP3-spezifischer Fehler auftritt.
            Exception: Für alle anderen unerwarteten Fehler beim Herunterladen der E-Mail.
        """
        mail = None
        try:
            if account.protocol == 'imap':
                mail = imaplib.IMAP4_SSL(account.server, account.port)
                mail.login(account.email_address, account.password)
                mail.select("inbox")
                status, msg_data = mail.fetch(email_id, '(RFC822)')
                if status == 'OK':
                    return msg_data[0][1]
                else:
                    raise imaplib.IMAP4.error(f"IMAP Fetch fehlgeschlagen für ID {email_id}: {status}") # Spezifischere Exception
            elif account.protocol == 'pop3':
                mail = poplib.POP3_SSL(account.server, account.port)
                mail.user(account.email_address)
                mail.pass_(account.password)
                resp, raw_email_lines, octets = mail.retr(email_id)
                raw_email = b'\r\n'.join(raw_email_lines)
                return raw_email
            else:
                raise ValueError("Ungültiges Protokoll.")
        except ValueError as e:
            logging.error(f"Protokoll Fehler beim Herunterladen der E-Mail ID {email_id} für Konto {account.email_address}: {e}")
            self.update_status(f"Protokoll Fehler: {e}", error=True)
            messagebox.showerror("Fehler", f"Protokoll Fehler: {e}")
            return None # Rückgabe None signalisiert Fehler, Verarbeitung der E-Mail abbrechen
        except imaplib.IMAP4.error as e:
            logging.error(f"IMAP Fehler beim Herunterladen der E-Mail ID {email_id} für Konto {account.email_address}: {e}")
            self.update_status(f"IMAP Fehler: {e}", error=True)
            messagebox.showerror("Fehler", f"IMAP Fehler: {e}")
            return None # Rückgabe None
        except poplib.error_proto as e:
            logging.error(f"POP3 Fehler beim Herunterladen der E-Mail ID {email_id} für Konto {account.email_address}: {e}")
            self.update_status(f"POP3 Fehler: {e}", error=True)
            messagebox.showerror("Fehler", f"POP3 Fehler: {e}")
            return None # Rückgabe None
        except Exception as e:
            logging.error(f"Unerwarteter Fehler beim Herunterladen der E-Mail ID {email_id} für Konto {account.email_address}: {e}")
            self.update_status(f"Fehler beim Herunterladen der E-Mail ID {email_id}: {e}", error=True)
            messagebox.showerror("Fehler", f"Fehler beim Herunterladen der E-Mail ID {email_id}: {e}")
            return None # Rückgabe None
        finally:
            if mail:
                try:
                    if account.protocol == 'imap':
                        mail.logout()
                    elif account.protocol == 'pop3':
                        mail.quit()
                except Exception as e:
                    logging.error(f"Fehler beim Schließen der Verbindung für Konto {account.email_address}: {e}")


    def _create_account_folder(self, account):
        """
        Erstellt den Basisordner für ein E-Mail-Konto im Dateisystem.

        Der Ordnername wird aus dem Kontonamen generiert. Wenn der Ordner bereits existiert, wird er nicht neu erstellt.

        Args:
            account (EmailAccount): Das E-Mail-Konto, für das der Ordner erstellt werden soll.

        Returns:
            str: Der absolute Pfad zum erstellten oder existierenden Kontoordner.
        """
        account_folder = account.name  # Ordnername ist der Name des Kontos
        os.makedirs(account_folder, exist_ok=True)
        return account_folder

    def _create_target_folder(self, account_folder, target_folder):
        """
        Erstellt den Zielordner ('emails' oder 'archiv') innerhalb des Kontoordners, inklusive eines Datumsunterordners.

        Erstellt zuerst den Basiszielordner ('emails' oder 'archiv') und dann einen Unterordner basierend auf dem aktuellen Datum im Format YYYY-MM-DD.
        Wenn Ordner bereits existieren, werden sie nicht neu erstellt.

        Args:
            account_folder (str): Der Pfad zum Kontoordner.
            target_folder (str): Der Name des Zielordners ('emails' oder 'archiv').

        Returns:
            str: Der absolute Pfad zum erstellten oder existierenden Datumsordner innerhalb des Zielordners.
        """
        base_folder = os.path.join(account_folder, target_folder)
        os.makedirs(base_folder, exist_ok=True)
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        date_folder = os.path.join(base_folder, date_str)
        os.makedirs(date_folder, exist_ok=True)
        return date_folder


    def _save_email(self, account, email_msg, target_folder):
        """
        Speichert den Inhalt einer E-Mail als Textdatei im Dateisystem.

        Erstellt den Kontoordner und den Datumsordner innerhalb des Zielordners ('emails' oder 'archiv').
        Der Dateiname wird aus dem Betreff der E-Mail und einem Zeitstempel generiert.
        Der E-Mail-Header (Von, An, Datum, Betreff) und der Textkörper (bevorzugt Plain Text, sonst HTML)
        werden in die Datei geschrieben.

        Args:
            account (EmailAccount): Das E-Mail-Konto, zu dem die E-Mail gehört.
            email_msg (email.message.Message): Die E-Mail-Nachricht.
            target_folder (str): Der Zielordner ('emails' oder 'archiv').
        """
        account_folder = self._create_account_folder(account) # Kontoordner erstellen/abrufen
        date_folder = self._create_target_folder(account_folder, target_folder) # Datumsordner im Zielordner
        subject = email_msg.get('subject', 'Kein Betreff').replace('/', '_').replace(':', '_') # Betreff bereinigen für Dateinamen
        safe_subject = "".join(c if c.isalnum() or c in " ._-" else "_" for c in subject).strip() # Noch sicherere Dateinamen
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{safe_subject}.txt"
        filepath = os.path.join(date_folder, filename)

        try:
            with open(filepath, 'w', encoding='utf-8') as outfile:
                outfile.write(f"Von: {email_msg.get('from')}\n")
                outfile.write(f"An: {email_msg.get('to')}\n")
                outfile.write(f"Datum: {email_msg.get('date')}\n")
                outfile.write(f"Betreff: {subject}\n\n")

                # E-Mail-Text extrahieren (Plain Text bevorzugt, sonst HTML)
                body = ""
                content_found = False # Flag um sicherzustellen, dass mindestens ein Inhaltstyp gefunden wurde
                if email_msg.is_multipart():
                    for part in email_msg.walk():
                        content_type = part.get_content_type()
                        content_disposition = str(part.get('Content-Disposition'))
                        if content_type == 'text/plain' and 'attachment' not in content_disposition:
                            body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                            content_found = True
                            break # Plain Text gefunden, Schleife beenden
                    if not content_found: # Falls kein Plain Text gefunden, HTML extrahieren (Fallback)
                        for part in email_msg.walk():
                            content_type = part.get_content_type()
                            content_disposition = str(part.get('Content-Disposition'))
                            if content_type == 'text/html' and 'attachment' not in content_disposition:
                                body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                                content_found = True
                                break
                else: # Nicht-Multipart E-Mail
                    body = email_msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                    content_found = True

                if content_found: # Nur Body schreiben, wenn Inhalt gefunden wurde
                    outfile.write(body)
                else:
                    outfile.write("<Kein E-Mail-Textinhalt gefunden>") # Hinweis, falls kein Textinhalt extrahiert werden konnte

            logging.info(f"E-Mail gespeichert im Ordner '{target_folder}': {filepath}")
        except Exception as e:
            logging.error(f"Fehler beim Speichern der E-Mail-Datei für Konto {account.email_address}: {e}")
            self.update_status(f"Fehler beim Speichern der E-Mail-Datei: {e}", error=True)


    def _process_attachments(self, account, email_msg, target_folder):
        """
        Verarbeitet und speichert Anhänge einer E-Mail im Dateisystem.

        Erstellt einen 'anhänge'-Unterordner innerhalb des Datumsordners im Zielordner.
        Für jeden Anhang wird der Dateiname extrahiert und der Anhang im 'anhänge'-Ordner gespeichert.
        **Dateinamen werden normalisiert, um Kompatibilitätsprobleme zu vermeiden.**

        Args:
            account (EmailAccount): Das E-Mail-Konto, zu dem die E-Mail gehört.
            email_msg (email.message.Message): Die E-Mail-Nachricht.
            target_folder (str): Der Zielordner ('emails' oder 'archiv').
        """
        account_folder = self._create_account_folder(account) # Kontoordner erstellen/abrufen
        date_folder = self._create_target_folder(account_folder, target_folder) # Datumsordner im Zielordner
        attachments_folder = os.path.join(date_folder, "anhänge")
        os.makedirs(attachments_folder, exist_ok=True) # Anhängeordner erstellen, falls nicht existiert

        for part in email_msg.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get('Content-Disposition') is None:
                continue

            filename = part.get_filename()
            if not filename: # Fallback, falls Dateiname fehlt
                filename = f"Anhang_{datetime.datetime.now().timestamp()}.bin"

            # Filename normalisieren, um Sonderzeichen zu entfernen
            normalized_filename = unicodedata.normalize("NFKD", filename).encode("ASCII", "ignore").decode("utf-8")
            filepath = os.path.join(attachments_folder, normalized_filename) # Normalisierten Dateinamen verwenden

            try:
                with open(filepath, 'wb') as outfile:
                    outfile.write(part.get_payload(decode=True))
                logging.info(f"Anhang gespeichert im Ordner '{target_folder}': {filepath}")
            except Exception as e:
                logging.error(f"Fehler beim Speichern des Anhangs '{filename}' für Konto {account.email_address}: {e}")
                self.update_status(f"Fehler beim Speichern des Anhangs '{filename}': {e}", error=True)


    def update_status(self, message: str, error: bool = False):
        """
        Aktualisiert die Statusanzeige am unteren Rand des Hauptfensters und färbt sie bei Bedarf rot.

        Args:
            message (str): Die Statusmeldung, die angezeigt werden soll.
            error (bool): True, wenn es sich um eine Fehlermeldung handelt, False für normale Statusmeldungen.
        """
        self.status_label.config(text=message, foreground="red" if error else "black")
        self.update_idletasks() # GUI sofort aktualisieren

if __name__ == "__main__":
    app = EmailArchiverGUI()
    app.mainloop()
