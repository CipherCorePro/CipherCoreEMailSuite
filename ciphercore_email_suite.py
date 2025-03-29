# -*- coding: utf-8 -*-
import tkinter as tk
# Korrigierte Importzeile: BOTTOM hinzugefügt
from tkinter import ttk, messagebox, Listbox, Scrollbar, END, Toplevel, Button, Label, Text, Y, BOTH, LEFT, RIGHT, X, SINGLE, MULTIPLE, Entry, BOTTOM
import imaplib
import poplib
import email
import os
import datetime
import logging
import keyring
from dataclasses import dataclass
from email.utils import parsedate_to_datetime, formatdate, make_msgid, formataddr, parseaddr # Hinzugefügt für Senden
import traceback
import unicodedata
import argparse  # Import für CLI Argumente
import smtplib  # Import für E-Mail Versand
import mimetypes # NEU: Import für guess_type
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from tkinter import filedialog  # Für Dateiauswahldialoge
import subprocess # Für plattformübergreifendes Öffnen von Dateien
import sys # Für Plattformprüfung
import threading # Für Senden im Hintergrund

try:
    from fuzzywuzzy import fuzz # Import fuzzywuzzy Bibliothek für Fuzzy Search
except ImportError:
    print("WARNUNG: fuzzywuzzy nicht gefunden. Die Suchfunktion im Explorer ist deaktiviert.")
    print("Bitte installieren Sie es mit: pip install fuzzywuzzy python-Levenshtein")
    fuzz = None # Setze fuzz auf None, wenn nicht installiert

# Einrichtung des Loggings für Debugging und Fehlerbehandlung
log_filename = 'email_archiver.log'
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filename=log_filename, filemode='a', encoding='utf-8') # Encoding hinzugefügt
console_handler = logging.StreamHandler(sys.stdout) # An stdout binden
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logging.getLogger().addHandler(console_handler)
logging.info("-------------------- Anwendung gestartet --------------------")


@dataclass
class EmailAccount:
    """
    Datenklasse zur Speicherung von E-Mail-Kontoinformationen.
    Speichert Kontonamen, Serverdetails, Anmeldeinformationen und Protokoll.
    """
    name: str
    server: str
    port: int
    email_address: str
    protocol: str  # 'imap' oder 'pop3'
    password: str  # Passwort wird hier temporär gehalten, sichere Speicherung via Keyring
    smtp_server: str = ""  # SMTP Server für ausgehende E-Mails
    smtp_port: int = 587  # Standard SMTP Port (TLS) oder 465 (SSL)


class EmailArchiverGUI(tk.Tk):
    """
    GUI-Klasse für die E-Mail-Archivierungsanwendung.
    Ermöglicht das Verwalten von Konten, das Abrufen und Archivieren von E-Mails
    sowie das Erkunden archivierter E-Mails und das Verwalten von E-Mails.
    """

    def __init__(self):
        """
        Initialisiert die EmailArchiverGUI-Anwendung.
        Lädt Konten, erstellt GUI-Widgets und setzt den Anfangszustand.
        """
        super().__init__()
        self.title("CipherCore E-Mail Suite") # Titel angepasst
        self.geometry("1000x800")  # Fenstergröße leicht erhöht
        self.resizable(True, True) # Fenstergröße änderbar gemacht

        # --- Initialisierung der Instanzvariablen ---
        self.accounts = []
        self.selected_account_index = None
        self.selected_folders = []  # Liste der ausgewählten IMAP Ordner für die aktuelle Archivierung
        # GUI Widget Variablen initial auf None setzen
        self.account_listbox = None
        self.fetch_button = None
        self.folder_select_button = None
        self.compose_button = None
        self.status_label = None
        self.name_entry = None
        self.server_entry = None
        self.port_entry = None
        self.email_entry = None
        self.password_entry = None
        self.protocol_var = None # Variable für Radiobuttons
        self.smtp_server_entry = None
        self.smtp_port_entry = None
        self.explorer_tree = None # Referenz auf den Treeview im Explorer

        # --- Daten laden und GUI aufbauen ---
        try:
            self._load_accounts()
        except Exception as e:
             # Kritischer Fehler beim Laden, GUI kann nicht richtig starten
             logging.critical(f"Kritischer Fehler beim Laden der Konten in __init__: {e}\n{traceback.format_exc()}")
             messagebox.showerror("Kritischer Fehler", f"Konten konnten nicht geladen werden. Die Anwendung kann nicht korrekt starten.\nFehler: {e}\nLogdatei: {log_filename}")
             # Hier könnte man überlegen, die App zu beenden: self.destroy()
             # Oder mit leerer Liste starten, wie es aktuell der Fall ist.

        self._create_widgets()
        self.update_status("Bereit. Bitte wählen Sie ein Konto oder fügen Sie ein neues hinzu.")


    def _load_accounts(self):
        """
        Lädt E-Mail-Konten aus der Konfigurationsdatei 'accounts.txt' und keyring.
        Ignoriert ungültige Zeilen und fehlende Passwörter.
        """
        logging.info("Lade E-Mail Konten...")
        self.accounts = [] # Sicherstellen, dass die Liste leer ist vor dem Laden
        accounts_file = "accounts.txt"
        try:
            if not os.path.exists(accounts_file):
                logging.info(f"Kontendatei '{accounts_file}' nicht gefunden. Starte mit leerer Kontenliste.")
                return

            with open(accounts_file, "r", encoding='utf-8') as f:
                for i, line in enumerate(f):
                    line = line.strip()
                    if not line or line.startswith('#'): # Leere Zeilen und Kommentare ignorieren
                         continue
                    logging.debug(f"Lese Zeile {i+1}: {line}")
                    try:
                        parts = line.strip().split(",")
                        if len(parts) >= 7:  # Neues Format mit SMTP
                            name, server, port_str, email_address, protocol, smtp_server, smtp_port_str = parts[:7]
                            port = int(port_str)
                            smtp_port = int(smtp_port_str)
                            password = keyring.get_password("EmailArchiver", email_address)
                            if password:
                                self.accounts.append(EmailAccount(name, server, port, email_address, protocol.lower(),
                                                                   password, smtp_server, smtp_port))
                                logging.debug(f"Konto '{name}' ({email_address}) mit SMTP geladen.")
                            else:
                                logging.warning(
                                    f"Passwort für Konto {email_address} (Zeile {i+1}) nicht in keyring gefunden. Konto wird ignoriert.")
                        elif len(parts) >= 5:  # Altes Format ohne SMTP
                             name, server, port_str, email_address, protocol = parts[:5]
                             port = int(port_str)
                             password = keyring.get_password("EmailArchiver", email_address)
                             if password:
                                 # Standard-SMTP-Werte hinzufügen und loggen
                                 smtp_server_guess = f"smtp.{server.split('.', 1)[-1]}" if ('imap.' in server or 'pop.' in server) and '.' in server else ""
                                 smtp_port_guess = 587
                                 self.accounts.append(
                                     EmailAccount(name, server, port, email_address, protocol.lower(), password, smtp_server_guess, smtp_port_guess)
                                 )
                                 logging.info(f"Konto '{name}' ({email_address}) aus altem Format geladen. Standard SMTP-Daten hinzugefügt ({smtp_server_guess}:{smtp_port_guess}). Bitte überprüfen.")
                             else:
                                 logging.warning(
                                     f"Passwort für Konto {email_address} (Zeile {i+1}, altes Format) nicht in keyring gefunden. Konto wird ignoriert.")
                        else:
                            logging.warning(f"Ungültige Zeile {i+1} in {accounts_file} (zu wenige Teile: {len(parts)}): '{line}'. Zeile wird ignoriert.")
                    except ValueError as ve:
                        logging.warning(f"Ungültige Zeile {i+1} in {accounts_file} (Wertfehler: {ve}): '{line}'. Zeile wird ignoriert.")
                    except Exception as e:
                         logging.warning(f"Fehler beim Parsen der Zeile {i+1} in {accounts_file}: '{line}'. Fehler: {e}. Zeile wird ignoriert.")
        except Exception as e:
            # Dies fängt Fehler beim Öffnen/Lesen der Datei selbst ab
            logging.error(f"Schwerwiegender Fehler beim Laden der Kontendatei '{accounts_file}': {e}\n{traceback.format_exc()}")
            # Wir werfen den Fehler hier weiter, damit er in __init__ behandelt wird
            raise IOError(f"Fehler beim Lesen der Kontendatei '{accounts_file}': {e}") from e
        logging.info(f"{len(self.accounts)} Konten erfolgreich geladen.")


    def _save_accounts(self):
        """
        Speichert E-Mail-Konten in der Datei 'accounts.txt' und Passwörter in keyring.
        Überschreibt die bestehende Datei.
        """
        accounts_file = "accounts.txt"
        logging.info(f"Speichere {len(self.accounts)} Konten in '{accounts_file}' und Keyring...")
        temp_file = accounts_file + ".tmp" # Temporäre Datei für atomares Speichern
        try:
            with open(temp_file, "w", encoding='utf-8') as f:
                for account in self.accounts:
                    # Passwort im Keyring speichern
                    try:
                         keyring.set_password("EmailArchiver", account.email_address, account.password)
                         logging.debug(f"Passwort für {account.email_address} im Keyring gespeichert/aktualisiert.")
                    except Exception as ke:
                         logging.error(f"Konnte Passwort für {account.email_address} nicht im Keyring speichern: {ke}. Konto wird NICHT in die Datei geschrieben.")
                         # Zeige Warnung, aber mache weiter mit dem nächsten Konto
                         messagebox.showwarning("Keyring Fehler", f"Konnte Passwort für {account.email_address} nicht sicher speichern: {ke}\n\nDas Konto wird nicht in der Datei gespeichert, um Inkonsistenzen zu vermeiden.", parent=self)
                         continue # Nächstes Konto

                    # Schreibe Konto in die temporäre Datei
                    f.write(
                        f"{account.name},{account.server},{account.port},{account.email_address},{account.protocol},{account.smtp_server},{account.smtp_port}\n")

            # Wenn Schreiben erfolgreich war, ersetze die alte Datei durch die neue
            os.replace(temp_file, accounts_file)
            logging.info("Konten erfolgreich gespeichert.")

        except Exception as e:
            logging.error(f"Fehler beim Speichern der Konten in '{accounts_file}': {e}\n{traceback.format_exc()}")
            messagebox.showerror("Speicherfehler", f"Fehler beim Speichern der Konten: {e}", parent=self)
            # Lösche die temporäre Datei, falls vorhanden
            if os.path.exists(temp_file):
                 try: os.remove(temp_file)
                 except OSError: pass


    def _create_widgets(self):
        """
        Erstellt und platziert alle GUI-Elemente im Hauptfenster.
        Organisiert Widgets in Frames für bessere Struktur.
        Ruft _on_account_select am Ende auf, um den initialen Button-Status zu setzen.
        """
        logging.debug("Erstelle GUI Widgets...")
        # Haupt-PanedWindow für flexible Größenänderung
        main_pane = ttk.PanedWindow(self, orient=tk.VERTICAL)
        main_pane.pack(fill=BOTH, expand=True)

        # --- Oberer Bereich: Konten und Aktionen ---
        top_frame = ttk.Frame(main_pane)
        main_pane.add(top_frame, weight=1) # Gewichtung anpassen nach Bedarf

        # Rahmen für Kontenverwaltung
        accounts_frame = ttk.LabelFrame(top_frame, text="E-Mail Konten verwalten")
        accounts_frame.pack(padx=10, pady=10, fill=tk.X)

        # Kontenliste
        listbox_frame = ttk.Frame(accounts_frame) # Extra Frame für Listbox und Scrollbar
        listbox_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=5, pady=5)
        self.account_listbox = Listbox(listbox_frame, height=5, selectmode=SINGLE, exportselection=False) # exportselection=False wichtig
        self.account_listbox.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar = Scrollbar(listbox_frame, orient=tk.VERTICAL)
        scrollbar.config(command=self.account_listbox.yview)
        scrollbar.pack(side=RIGHT, fill=Y)
        self.account_listbox.config(yscrollcommand=scrollbar.set)
        self.account_listbox.bind('<<ListboxSelect>>', self._on_account_select) # Event bei Auswahl

        # Kontenliste initial befüllen (ohne _on_account_select Aufruf hier)
        self._update_account_listbox_content()

        # Buttons für Kontenverwaltung (vertikal angeordnet)
        account_button_frame = ttk.Frame(accounts_frame)
        account_button_frame.pack(side=LEFT, padx=5, pady=5, fill=Y)
        add_account_button = ttk.Button(account_button_frame, text="Konto hinzufügen", command=self._add_account_window)
        add_account_button.pack(fill=X, pady=2)
        remove_account_button = ttk.Button(account_button_frame, text="Konto entfernen", command=self._remove_account)
        remove_account_button.pack(fill=X, pady=2)
        # Folder Select Button wird hier erstellt
        self.folder_select_button = ttk.Button(account_button_frame, text="Ordner auswählen",
                                           command=self._open_folder_selection_window, state=tk.DISABLED) # Initial deaktiviert
        self.folder_select_button.pack(fill=X, pady=2)

        # Rahmen für Aktionen (Archivieren, Explorer, Verfassen)
        actions_frame = ttk.LabelFrame(top_frame, text="Aktionen")
        actions_frame.pack(padx=10, pady=10, fill=tk.X)

        # Fetch Button wird hier erstellt
        self.fetch_button = ttk.Button(actions_frame, text="Ausgewählte Ordner archivieren",
                                       command=self._fetch_and_process_emails, state=tk.DISABLED) # Initial deaktiviert
        self.fetch_button.pack(side=LEFT, padx=5, pady=5)

        explorer_button = ttk.Button(actions_frame, text="Archiv Explorer öffnen",
                                      command=self._open_email_explorer)
        explorer_button.pack(side=LEFT, padx=5, pady=5)

        # Compose Button wird hier erstellt
        self.compose_button = ttk.Button(actions_frame, text="E-Mail verfassen",
                                      command=lambda: self._open_compose_email_window(mode='compose'), # Lambda für Standard-Modus
                                      state=tk.DISABLED) # Initial deaktiviert
        self.compose_button.pack(side=LEFT, padx=5, pady=5)

        # --- Unterer Bereich: Statusanzeige ---
        status_frame = ttk.Frame(main_pane) # Eigener Frame für Status
        main_pane.add(status_frame, weight=0) # Kein Expand

        # Status Label wird hier erstellt
        self.status_label = ttk.Label(status_frame, text="Initialisiere...", anchor="w")
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

        # Jetzt, da alle Widgets erstellt sind, den initialen Button-Status setzen
        self._on_account_select()
        logging.debug("GUI Widgets erfolgreich erstellt.")

    def _update_account_listbox_content(self):
        """ Nur den Inhalt der Listbox aktualisieren. """
        if not self.account_listbox:
             logging.error("Versuch, account_listbox zu aktualisieren, bevor es erstellt wurde.")
             return
        self.account_listbox.delete(0, END)
        for account in self.accounts:
            self.account_listbox.insert(END, f"{account.name} ({account.email_address})")

    def _on_account_select(self, event=None):
        """
        Wird aufgerufen, wenn ein Konto in der Listbox ausgewählt wird ODER
        wenn der Status nach einer Aktion aktualisiert werden muss.
        Aktiviert/Deaktiviert Buttons basierend auf der Auswahl und Kontokonfiguration.
        Stellt sicher, dass die Widgets existieren, bevor darauf zugegriffen wird.
        """
        logging.debug("Aktualisiere Button-Status basierend auf Kontauswahl...")
        # Prüfen, ob die relevanten Widgets bereits erstellt wurden
        if not all([self.account_listbox, self.fetch_button, self.folder_select_button, self.compose_button]):
            logging.warning("_on_account_select aufgerufen, bevor alle Widgets erstellt wurden. Überspringe.")
            return

        selected_indices = self.account_listbox.curselection()
        if not selected_indices:
            # Kein Konto ausgewählt
            self.fetch_button.config(state=tk.DISABLED)
            self.folder_select_button.config(state=tk.DISABLED)
            self.compose_button.config(state=tk.DISABLED)
            self.selected_account_index = None
            self.selected_folders = [] # Ordnerauswahl zurücksetzen
            logging.debug("Kein Konto ausgewählt, Buttons deaktiviert.")
            return

        # Ein Konto ist ausgewählt
        self.selected_account_index = int(selected_indices[0])
        try:
             selected_account = self.accounts[self.selected_account_index]
             logging.debug(f"Konto Index {self.selected_account_index} ausgewählt: {selected_account.name}")
        except IndexError:
             logging.error(f"IndexError in _on_account_select: Index {self.selected_account_index} ist ungültig für Kontoliste der Länge {len(self.accounts)}")
             # Zustand zurücksetzen, als wäre nichts ausgewählt
             self.account_listbox.selection_clear(0, END)
             self._on_account_select() # Erneut aufrufen, um Buttons zu deaktivieren
             return


        # Buttons entsprechend dem ausgewählten Konto konfigurieren
        self.fetch_button.config(state=tk.NORMAL)
        self.compose_button.config(state=tk.NORMAL if selected_account.smtp_server and selected_account.smtp_port else tk.DISABLED)

        if selected_account.protocol == 'imap':
            self.folder_select_button.config(state=tk.NORMAL)
        else:
            self.folder_select_button.config(state=tk.DISABLED)
            # Bei POP3 gibt es keine Ordnerauswahl, also leeren wir sie ggf.
            self.selected_folders = []

        logging.debug(f"Button-Status: Fetch={self.fetch_button['state']}, FolderSelect={self.folder_select_button['state']}, Compose={self.compose_button['state']}")
        # Statusleiste nur aktualisieren, wenn es nicht der Initialaufruf ist (optional)
        # self.update_status(f"Konto '{selected_account.name}' ausgewählt. {len(self.selected_folders)} Ordner zum Archivieren gewählt.")


    def _update_account_listbox(self):
        """
        Aktualisiert die Listbox mit den aktuell geladenen E-Mail-Konten
        UND ruft _on_account_select auf, um den Button-Status anzupassen.
        Wird nach Hinzufügen/Entfernen von Konten verwendet.
        """
        logging.debug("Aktualisiere Kontenliste und Button-Status...")
        self._update_account_listbox_content()
        # Nach dem Aktualisieren der Liste den Status der Buttons neu setzen
        self._on_account_select()

    def _add_account_window(self):
        """
        Öffnet ein neues Toplevel-Fenster zum Hinzufügen eines E-Mail-Kontos.
        Verwendet Grid-Layout für eine saubere Anordnung.
        """
        add_window = Toplevel(self)
        add_window.title("Konto hinzufügen")
        add_window.resizable(False, False)
        add_window.transient(self) # Modal zum Hauptfenster
        add_window.grab_set() # Fokus auf dieses Fenster

        frame = ttk.Frame(add_window, padding="10")
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(1, weight=1) # Eingabefelder sollen sich ausdehnen

        row_num = 0
        ttk.Label(frame, text="Name (z.B. Arbeit):").grid(row=row_num, column=0, padx=5, pady=5, sticky="w")
        self.name_entry = ttk.Entry(frame, width=40)
        self.name_entry.grid(row=row_num, column=1, padx=5, pady=5, sticky="ew")
        row_num += 1

        ttk.Label(frame, text="Protokoll:").grid(row=row_num, column=0, padx=5, pady=5, sticky="w")
        # Verwende Instanzvariable für protocol_var
        self.protocol_var = tk.StringVar(value='imap')
        protocol_frame = ttk.Frame(frame)
        protocol_frame.grid(row=row_num, column=1, padx=5, pady=5, sticky="w")
        ttk.Radiobutton(protocol_frame, text="IMAP", variable=self.protocol_var, value='imap').pack(side=LEFT)
        ttk.Radiobutton(protocol_frame, text="POP3", variable=self.protocol_var, value='pop3').pack(side=LEFT, padx=10)
        row_num += 1

        ttk.Label(frame, text="Server (Posteingang):").grid(row=row_num, column=0, padx=5, pady=5, sticky="w")
        self.server_entry = ttk.Entry(frame, width=40)
        self.server_entry.grid(row=row_num, column=1, padx=5, pady=5, sticky="ew")
        row_num += 1

        ttk.Label(frame, text="Port (z.B. 993):").grid(row=row_num, column=0, padx=5, pady=5, sticky="w")
        self.port_entry = ttk.Entry(frame, width=10)
        self.port_entry.grid(row=row_num, column=1, padx=5, pady=5, sticky="w")
        row_num += 1

        ttk.Label(frame, text="E-Mail Adresse:").grid(row=row_num, column=0, padx=5, pady=5, sticky="w")
        self.email_entry = ttk.Entry(frame, width=40)
        self.email_entry.grid(row=row_num, column=1, padx=5, pady=5, sticky="ew")
        row_num += 1

        ttk.Label(frame, text="Passwort:").grid(row=row_num, column=0, padx=5, pady=5, sticky="w")
        self.password_entry = ttk.Entry(frame, show="*", width=40)
        self.password_entry.grid(row=row_num, column=1, padx=5, pady=5, sticky="ew")
        row_num += 1

        ttk.Label(frame, text="SMTP Server (Postausgang):").grid(row=row_num, column=0, padx=5, pady=5, sticky="w")
        self.smtp_server_entry = ttk.Entry(frame, width=40)
        self.smtp_server_entry.grid(row=row_num, column=1, padx=5, pady=5, sticky="ew")
        row_num += 1

        ttk.Label(frame, text="SMTP Port (z.B. 587):").grid(row=row_num, column=0, padx=5, pady=5, sticky="w")
        self.smtp_port_entry = ttk.Entry(frame, width=10)
        self.smtp_port_entry.grid(row=row_num, column=1, padx=5, pady=5, sticky="w")
        row_num += 1

        # Speichern/Abbrechen Buttons
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=row_num, column=0, columnspan=2, pady=10)
        # Verwende Lambda, um das Fensterobjekt an die save-Methode zu übergeben
        save_button = ttk.Button(button_frame, text="Speichern", command=lambda w=add_window: self._save_new_account(w))
        save_button.pack(side=LEFT, padx=5)
        cancel_button = ttk.Button(button_frame, text="Abbrechen", command=add_window.destroy)
        cancel_button.pack(side=LEFT, padx=5)

        self.name_entry.focus_set()
        add_window.wait_window() # Warten bis das Fenster geschlossen wird


    def _save_new_account(self, window: Toplevel): # Typ-Hint für das Fenster
        """
        Speichert ein neues E-Mail-Konto basierend auf den Eingaben im AddAccount-Fenster.
        Schließt das Fenster bei Erfolg. Validiert Eingaben.
        """
        # Eingaben abrufen und bereinigen
        name = self.name_entry.get().strip()
        server = self.server_entry.get().strip()
        port_str = self.port_entry.get().strip()
        email_address = self.email_entry.get().strip()
        password = self.password_entry.get() # Kein strip bei Passwort
        protocol = self.protocol_var.get() # Von StringVar abrufen
        smtp_server = self.smtp_server_entry.get().strip()
        smtp_port_str = self.smtp_port_entry.get().strip()
        logging.info(f"Versuche, neues Konto zu speichern: Name='{name}', Email='{email_address}', Proto='{protocol}'")

        try:
            # --- Grundlegende Validierung ---
            required_fields = {'Name': name, 'Server': server, 'Port': port_str, 'E-Mail Adresse': email_address, 'Passwort': password}
            missing = [k for k, v in required_fields.items() if not v]
            if missing:
                raise ValueError(f"Bitte füllen Sie die folgenden erforderlichen Felder aus: {', '.join(missing)}.")

            # E-Mail-Adresse auf '@' prüfen (einfache Prüfung)
            if '@' not in email_address or '.' not in email_address.split('@')[-1]:
                 raise ValueError("Bitte geben Sie eine gültige E-Mail Adresse ein.")

            # Ports validieren
            try:
                 port = int(port_str)
                 if not (0 < port < 65536): raise ValueError()
            except ValueError:
                 raise ValueError("Der Port für den Posteingangsserver muss eine Zahl zwischen 1 und 65535 sein.")

            smtp_port = 0
            if smtp_server or smtp_port_str: # Wenn SMTP-Daten teilweise angegeben sind...
                if not smtp_server:
                     # Automatisch erraten, wenn Port da ist? Oder Fehler? -> Fehler ist sicherer.
                     raise ValueError("SMTP Server muss angegeben werden, wenn ein SMTP Port gesetzt ist.")
                if not smtp_port_str:
                     # Standardport setzen, wenn nur Server da ist
                     smtp_port = 587 # Standard TLS Port
                     self.smtp_port_entry.insert(0, str(smtp_port)) # Im UI eintragen
                     logging.info(f"SMTP Port nicht angegeben, setze Standard auf {smtp_port}.")
                else:
                     try:
                          smtp_port = int(smtp_port_str)
                          if not (0 < smtp_port < 65536): raise ValueError()
                     except ValueError:
                          raise ValueError("Der SMTP Port muss eine Zahl zwischen 1 und 65535 sein.")
            # Kein else hier: Wenn beide SMTP Felder leer sind, ist das OK.

            # Protokoll sollte durch Radiobuttons valide sein, aber zur Sicherheit
            if protocol not in ('imap', 'pop3'):
                raise ValueError("Ungültiges Protokoll ausgewählt.") # Sollte nie passieren

            # --- Zusätzliche Prüfungen ---
            # Prüfen ob Konto (E-Mail) bereits existiert
            if any(acc.email_address.lower() == email_address.lower() for acc in self.accounts):
                 raise ValueError(f"Ein Konto mit der E-Mail-Adresse '{email_address}' existiert bereits.")

            # --- Passwort im Keyring speichern (vor dem Hinzufügen zur Liste) ---
            try:
                logging.debug(f"Versuche Passwort für {email_address} im Keyring zu speichern...")
                keyring.set_password("EmailArchiver", email_address, password)
                logging.info(f"Passwort für {email_address} erfolgreich im Keyring gespeichert.")
            except Exception as ke:
                 # Wenn Keyring fehlschlägt, Konto nicht hinzufügen, da es unbrauchbar wäre
                 logging.error(f"Konnte Passwort für {email_address} nicht im Keyring speichern: {ke}")
                 # Detailliertere Fehlermeldung für den Benutzer
                 error_detail = str(ke)
                 if "No recommended backend was found" in error_detail:
                      error_detail += "\n\nMöglicherweise fehlt ein Keyring-Backend (z.B. 'keyrings.cryptfile' oder ein System-Backend)."
                 elif "Locked" in error_detail or "unlock" in error_detail:
                       error_detail += "\n\nDer Keyring ist möglicherweise gesperrt. Bitte entsperren Sie ihn."

                 raise ValueError(f"Konto konnte nicht hinzugefügt werden: Passwort konnte nicht sicher gespeichert werden.\n\nFehlerdetails: {error_detail}") from ke

            # --- Neues Konto erstellen und hinzufügen ---
            new_account = EmailAccount(name, server, port, email_address, protocol, password, smtp_server, smtp_port)
            self.accounts.append(new_account)
            logging.info(f"Konto '{name}' zur Liste hinzugefügt.")

            # --- Konten in Datei speichern ---
            self._save_accounts() # Speichert die gesamte Liste inkl. neuem Konto

            # --- GUI aktualisieren ---
            self._update_account_listbox() # Aktualisiert Listbox und Button-Status
            # Neues Konto in der Liste auswählen
            try:
                 # Finde den Index des neuen Kontos (sollte der letzte sein)
                 new_index = len(self.accounts) - 1
                 self.account_listbox.selection_set(new_index)
                 self.account_listbox.see(new_index) # Sicherstellen, dass es sichtbar ist
                 self._on_account_select() # Button-Status explizit aktualisieren
            except tk.TclError: # Falls die Listbox aus irgendeinem Grund nicht bereit ist
                 logging.warning("Konnte neues Konto in Listbox nicht auswählen.")


            # --- Abschluss ---
            window.destroy() # Fenster schließen
            messagebox.showinfo("Erfolg", f"Konto '{name}' erfolgreich hinzugefügt.", parent=self) # Parent setzen für korrekte Position

        except ValueError as ve:
            logging.warning(f"Fehler beim Speichern des Kontos (Validierung): {ve}")
            messagebox.showerror("Ungültige Eingabe", str(ve), parent=window) # Fehler im Add-Fenster anzeigen
        except Exception as e:
            logging.error(f"Allgemeiner Fehler beim Speichern des neuen Kontos: {e}\n{traceback.format_exc()}")
            messagebox.showerror("Fehler", f"Ein unerwarteter Fehler ist aufgetreten:\n{e}", parent=window)

    def _remove_account(self):
        """
        Entfernt das ausgewählte E-Mail-Konto aus der Liste, der Konfiguration und dem Keyring.
        """
        if self.selected_account_index is None:
             # Dies sollte durch Button-Status verhindert werden, aber zur Sicherheit
             messagebox.showinfo("Hinweis", "Bitte wählen Sie zuerst ein Konto zum Entfernen aus.", parent=self)
             return

        try:
            account_to_remove = self.accounts[self.selected_account_index]
        except IndexError:
             logging.error(f"Fehler in _remove_account: selected_account_index ({self.selected_account_index}) ungültig.")
             messagebox.showerror("Fehler", "Interner Fehler: Ungültige Kontoauswahl.", parent=self)
             # Auswahl zurücksetzen und UI aktualisieren
             if self.account_listbox: self.account_listbox.selection_clear(0, END)
             self._on_account_select()
             return


        confirm_msg = f"Möchten Sie das Konto '{account_to_remove.name}' ({account_to_remove.email_address}) wirklich entfernen?\n\nDas Passwort wird aus dem Keyring gelöscht und die Kontodaten aus der Konfigurationsdatei entfernt."
        if messagebox.askyesno("Bestätigung", confirm_msg, parent=self):
            logging.info(f"Entferne Konto: {account_to_remove.name} ({account_to_remove.email_address})")
            try:
                email_address_to_remove = account_to_remove.email_address

                # Aus der Liste entfernen
                del self.accounts[self.selected_account_index]
                logging.debug(f"Konto aus interner Liste entfernt.")

                # Aktualisierte Liste speichern
                self._save_accounts()

                # Versuche Passwort aus Keyring zu löschen
                try:
                     keyring.delete_password("EmailArchiver", email_address_to_remove)
                     logging.info(f"Passwort für {email_address_to_remove} aus Keyring entfernt.")
                except keyring.errors.PasswordDeleteError:
                     logging.warning(f"Passwort für {email_address_to_remove} konnte nicht im Keyring gefunden/gelöscht werden (möglicherweise bereits entfernt oder Keyring-Problem).")
                except Exception as ke:
                     logging.error(f"Fehler beim Löschen des Passworts aus Keyring für {email_address_to_remove}: {ke}")
                     messagebox.showwarning("Keyring Fehler", f"Fehler beim Löschen des Passworts aus dem Keyring:\n{ke}", parent=self)
                     # Fortfahren, Konto ist trotzdem aus der App entfernt

                # GUI aktualisieren
                self.selected_account_index = None # Auswahl aufheben
                self.selected_folders = [] # Ordnerauswahl zurücksetzen
                self._update_account_listbox() # Liste aktualisieren (ruft auch _on_account_select auf)

                messagebox.showinfo("Erfolg", "Konto erfolgreich entfernt.", parent=self)
                logging.info("Konto erfolgreich entfernt.")

            except Exception as e:
                logging.error(f"Fehler beim Entfernen des Kontos nach Bestätigung: {e}\n{traceback.format_exc()}")
                messagebox.showerror("Fehler", f"Fehler beim Entfernen des Kontos: {e}", parent=self)
                # Versuchen, den Zustand zu retten? Z.B. Konten neu laden?
                # self._load_accounts()
                # self._update_account_listbox()


    def _open_folder_selection_window(self):
        """
        Öffnet ein Fenster zur Auswahl der IMAP Ordner für das aktuell ausgewählte Konto.
        Nur verfügbar für IMAP-Konten.
        """
        if self.selected_account_index is None:
            messagebox.showinfo("Hinweis", "Bitte wählen Sie zuerst ein E-Mail-Konto aus.", parent=self)
            return

        selected_account = self.accounts[self.selected_account_index]

        if selected_account.protocol != 'imap':
            messagebox.showinfo("Hinweis", "Ordnerauswahl ist nur für IMAP-Konten verfügbar.", parent=self)
            return

        folder_window = Toplevel(self)
        folder_window.title(f"Ordnerauswahl für {selected_account.name}")
        folder_window.geometry("400x450") # Etwas höher für Buttons
        folder_window.transient(self)
        folder_window.grab_set()

        folder_frame = ttk.Frame(folder_window, padding="10")
        folder_frame.pack(fill=BOTH, expand=True)

        ttk.Label(folder_frame, text="Wählen Sie die zu archivierenden Ordner:").pack(pady=5, anchor='w')

        list_frame = ttk.Frame(folder_frame)
        list_frame.pack(fill=BOTH, expand=True, pady=5)

        folder_listbox = Listbox(list_frame, selectmode=MULTIPLE, exportselection=False)
        scrollbar = Scrollbar(list_frame, orient=tk.VERTICAL, command=folder_listbox.yview)
        folder_listbox.config(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=RIGHT, fill=Y)
        folder_listbox.pack(side=LEFT, fill=BOTH, expand=True)

        status_label_folder = ttk.Label(folder_frame, text="Lade Ordner...", style="Status.TLabel") # Style für spätere Anpassung?
        status_label_folder.pack(pady=5, fill=X)
        folder_window.update_idletasks() # Status anzeigen

        # Funktion zum Abrufen der Ordner im Hintergrund
        def fetch_folders_thread():
            mail = None
            all_folders = []
            error_message = None
            try:
                logging.info(f"Stelle IMAP Verbindung für Ordnerliste her: {selected_account.server}:{selected_account.port}")
                mail = imaplib.IMAP4_SSL(selected_account.server, selected_account.port, timeout=15) # Timeout hinzufügen
                mail.login(selected_account.email_address, selected_account.password)
                logging.info(f"IMAP Login erfolgreich für {selected_account.email_address}.")
                status, folders_raw = mail.list()
                mail.logout()
                logging.info(f"IMAP Verbindung für Ordnerliste geschlossen.")

                if status == "OK":
                    for folder_item_bytes in folders_raw:
                        try:
                            folder_item_str = folder_item_bytes.decode('utf-8', 'ignore')
                            # Robusteres Parsen von Ordnernamen, z.B. '(Bereich1 Bereich2) "/" Ordnername'
                            parts = folder_item_str.split('"')
                            folder_name = None
                            flags = ""
                            if len(parts) >= 3: # Format: (...) "/" "Ordnername"
                                folder_name = parts[-2].strip()
                                flag_part = parts[0].split('(')[-1].split(')')[0]
                                if flag_part: flags = flag_part
                            else: # Fallback: Versuche, das letzte Element nach dem Separator zu nehmen
                                separator = folder_item_str.split(' ')[-2] # Der Separator (meist "/")
                                if separator and len(separator) == 1: # Einfache Prüfung auf Separator
                                     folder_name = folder_item_str.split(separator)[-1].strip()

                            if folder_name:
                                # \Noselect Flag prüfen
                                if r'\Noselect' not in flags.split():
                                    all_folders.append(folder_name)
                                else:
                                     logging.debug(f"Ignoriere Ordner '{folder_name}' wegen Flag \\Noselect.")
                            else:
                                 logging.warning(f"Konnte Ordnernamen nicht aus Eintrag extrahieren: {folder_item_str}")

                        except Exception as parse_error:
                             logging.warning(f"Fehler beim Parsen des Ordnernamens: {folder_item_bytes}. Fehler: {parse_error}")
                    all_folders.sort(key=str.lower) # Sortiere Ordner case-insensitive
                else:
                    error_message = f"Fehler beim Abrufen der Ordnerliste vom Server (Status: {status})."
                    logging.error(error_message)

            except imaplib.IMAP4.error as imap_err:
                 error_message = f"IMAP Fehler bei Verbindung/Login:\n{imap_err}"
                 logging.error(f"IMAP Fehler beim Abrufen der Ordnerliste für {selected_account.email_address}: {imap_err}")
            except TimeoutError:
                 error_message = f"Timeout beim Verbinden mit {selected_account.server}."
                 logging.error(error_message)
            except Exception as e:
                error_message = f"Unerwarteter Fehler:\n{e}"
                logging.error(f"Unerwarteter Fehler beim Abrufen der Ordnerliste: {e}\n{traceback.format_exc()}")
            finally:
                 if mail and mail.state == 'SELECTED': # Sicherstellen, dass ausgeloggt wird
                     try: mail.logout()
                     except: pass
                 # Nach Beendigung des Threads die GUI aktualisieren
                 folder_window.after(0, update_folder_list_ui, all_folders, error_message)

        # Funktion zum Aktualisieren der GUI nach dem Thread
        def update_folder_list_ui(folders, error_msg):
            if error_msg:
                status_label_folder.config(text=f"Fehler: {error_msg}", foreground="red")
                messagebox.showerror("Fehler", f"Fehler beim Abrufen der Ordnerliste:\n{error_msg}", parent=folder_window)
                # Fenster schließen bei Fehler? Oder leer lassen?
                # folder_window.destroy()
            else:
                folder_listbox.delete(0, END) # Alte Einträge löschen
                for folder_name in folders:
                     folder_listbox.insert(END, folder_name)
                     # Bereits global ausgewählte Ordner vorselektieren
                     if folder_name in self.selected_folders:
                         # Finde den Index des gerade eingefügten Elements
                         current_index = folder_listbox.size() - 1
                         folder_listbox.selection_set(current_index)

                status_label_folder.config(text=f"{len(folders)} Ordner gefunden.", foreground="black")
                # Buttons aktivieren, wenn Liste geladen wurde
                save_button.config(state=tk.NORMAL)


        # Funktion zum Speichern der Auswahl
        def save_selected_folders():
            selected_folder_indices = folder_listbox.curselection()
            # Korrekte Extraktion der Namen aus der Listbox
            self.selected_folders = [folder_listbox.get(i) for i in selected_folder_indices]
            folder_window.destroy()
            folder_display = ', '.join(self.selected_folders) if self.selected_folders else "Keine"
            messagebox.showinfo("Auswahl gespeichert", f"Ausgewählte Ordner für die nächste Archivierung: {folder_display}", parent=self)
            self.update_status(f"Konto '{selected_account.name}' ausgewählt. {len(self.selected_folders)} Ordner zum Archivieren gewählt.")


        # Buttons erstellen (initial deaktiviert, außer Abbrechen)
        button_frame = ttk.Frame(folder_frame)
        button_frame.pack(pady=10)
        save_button = ttk.Button(button_frame, text="Auswahl speichern", command=save_selected_folders, state=tk.DISABLED)
        save_button.pack(side=LEFT, padx=5)
        cancel_button = ttk.Button(button_frame, text="Abbrechen", command=folder_window.destroy)
        cancel_button.pack(side=LEFT, padx=5)

        # Ordnerabruf im Hintergrund starten
        folder_thread = threading.Thread(target=fetch_folders_thread, daemon=True)
        folder_thread.start()

        folder_window.wait_window()


    def _fetch_and_process_emails(self):
        """
        Hauptfunktion zum Starten des E-Mail-Abrufs und der Archivierung
        für das ausgewählte Konto und die ausgewählten Ordner (IMAP) oder Inbox (POP3).
        Zeigt ein Fortschrittsfenster an und läuft im Hintergrund Thread.
        """
        if self.selected_account_index is None:
            messagebox.showinfo("Hinweis", "Bitte wählen Sie ein E-Mail-Konto aus der Liste.", parent=self)
            return

        selected_account = self.accounts[self.selected_account_index]

        # Bestimmen der zu archivierenden Ordner
        if selected_account.protocol == 'imap':
            if not self.selected_folders:
                 messagebox.showinfo("Hinweis", "Bitte wählen Sie zuerst die zu archivierenden Ordner über 'Ordner auswählen' aus.", parent=self)
                 return
            folders_to_archive = self.selected_folders
        else: # POP3 hat nur Inbox
            folders_to_archive = ["inbox"]

        # --- GUI-Elemente deaktivieren ---
        self._set_ui_state(tk.DISABLED)
        self.update_status(f"Starte E-Mail-Abruf für Konto: {selected_account.name} ({', '.join(folders_to_archive)})...")
        logging.info(f"Archivierung gestartet für Konto {selected_account.email_address}, Ordner: {folders_to_archive}")

        # --- Fortschrittsfenster erstellen ---
        progress_window = Toplevel(self)
        progress_window.title("E-Mail Archivierung läuft...")
        progress_window.geometry("450x150")
        progress_window.resizable(False, False)
        progress_window.transient(self)
        progress_window.protocol("WM_DELETE_WINDOW", lambda: None) # Verhindert Schließen des Fensters
        progress_window.grab_set() # Modal machen

        prog_frame = ttk.Frame(progress_window, padding="10")
        prog_frame.pack(fill=BOTH, expand=True)

        prog_label_status = ttk.Label(prog_frame, text=f"Verbinde mit {selected_account.server}...", anchor="w")
        prog_label_status.pack(fill=X, pady=5)
        prog_label_count = ttk.Label(prog_frame, text="E-Mails: 0/0", anchor="w")
        prog_label_count.pack(fill=X, pady=2)
        prog_label_errors = ttk.Label(prog_frame, text="Fehler: 0", anchor="w", foreground="darkgrey")
        prog_label_errors.pack(fill=X, pady=2)

        progressbar = ttk.Progressbar(prog_frame, orient=tk.HORIZONTAL, length=400, mode='determinate')
        progressbar.pack(pady=10)
        # Kein Abbrechen-Button im Moment, da das Stoppen komplex ist

        # --- Daten für den Thread vorbereiten ---
        thread_data = {
            'account': selected_account,
            'folders': folders_to_archive,
            'progress_window': progress_window,
            'labels': {'status': prog_label_status, 'count': prog_label_count, 'errors': prog_label_errors},
            'progressbar': progressbar,
            'results': {'processed': 0, 'archived': 0, 'saved_new': 0, 'errors': 0, 'total_found': 0} # 'saved_new' hinzugefügt
        }

        # --- Archivierungs-Thread starten ---
        archive_thread = threading.Thread(target=self._archive_thread_worker, args=(thread_data,), daemon=True)
        archive_thread.start()


    def _set_ui_state(self, state):
         """ Aktiviert oder deaktiviert die Haupt-UI-Elemente. """
         widgets_to_toggle = [
             self.account_listbox,
             self.fetch_button,
             self.folder_select_button,
             self.compose_button
         ]
         # Buttons im Kontenverwaltungs-Frame auch (add/remove)
         if self.account_listbox: # Prüfen ob Listbox existiert
              accounts_frame = self.account_listbox.master.master # Frame -> LabelFrame
              if accounts_frame:
                   for child in accounts_frame.winfo_children():
                       # Buttons sind im account_button_frame
                       if isinstance(child, ttk.Frame):
                            for btn in child.winfo_children():
                                 if isinstance(btn, ttk.Button):
                                     widgets_to_toggle.append(btn)

         for widget in widgets_to_toggle:
             if widget: # Prüfen ob Widget bereits erstellt wurde
                 try:
                     widget.config(state=state)
                 except tk.TclError as e:
                      logging.warning(f"Fehler beim Setzen des Status für Widget {widget}: {e}")

         # Nach Deaktivierung, Buttons spezifisch wieder aktivieren, wenn nötig
         if state == tk.NORMAL:
              self._on_account_select() # Stellt korrekten Status wieder her


    def _archive_thread_worker(self, data):
        """ Diese Funktion läuft im Hintergrundthread für die Archivierung. """
        account = data['account']
        folders = data['folders']
        progress_window = data['progress_window']
        labels = data['labels']
        progressbar = data['progressbar']
        results = data['results'] # Enthält jetzt auch 'saved_new'

        def update_progress(status_msg=None, count_msg=None, error_count=None, progress_val=None):
            """ Hilfsfunktion zum Aktualisieren der GUI aus dem Thread via after(). """
            def task():
                # Versuche, auf Widgets zuzugreifen, nur wenn das Fenster noch existiert
                try:
                    if not progress_window.winfo_exists():
                        return # Fenster ist weg, keine Updates mehr nötig
                    if status_msg is not None: labels['status'].config(text=status_msg)
                    if count_msg is not None: labels['count'].config(text=count_msg)
                    if error_count is not None:
                         labels['errors'].config(text=f"Fehler: {error_count}", foreground="red" if error_count > 0 else "darkgrey")
                    if progress_val is not None: progressbar['value'] = progress_val
                    progress_window.update_idletasks()
                except tk.TclError as e:
                     logging.warning(f"Fehler beim Aktualisieren des Fortschrittsfensters (möglicherweise geschlossen): {e}")
            # Schedule the task in the main thread
            try:
                 if progress_window.winfo_exists():
                     progress_window.after(0, task)
            except tk.TclError:
                 pass # Fenster wurde zwischen Prüfung und after() geschlossen

        mail_connection = None
        download_connection = None
        all_email_ids_with_folder = []
        total_ids_found = 0
        fetch_errors = 0

        try:
            # --- Phase 1: E-Mail IDs abrufen ---
            update_progress(status_msg=f"Rufe E-Mail IDs ab ({account.protocol.upper()})...")
            if account.protocol == 'imap':
                 try:
                     logging.debug(f"Thread: Stelle IMAP Verbindung für ID-Abruf her.")
                     mail_connection = imaplib.IMAP4_SSL(account.server, account.port, timeout=20) # Längerer Timeout
                     mail_connection.login(account.email_address, account.password)
                 except Exception as conn_err:
                     logging.error(f"Thread: IMAP Verbindungsfehler für ID-Abruf: {conn_err}")
                     raise ConnectionError(f"IMAP Verbindungsfehler (ID-Abruf): {conn_err}") from conn_err

            for i, folder in enumerate(folders):
                update_progress(status_msg=f"Prüfe Ordner '{folder}' ({i+1}/{len(folders)})...")
                email_ids = self._fetch_email_ids(account, folder, mail_connection)
                if email_ids is not None:
                    count = len(email_ids)
                    total_ids_found += count
                    logging.debug(f"Thread: {count} IDs in '{folder}' gefunden.")
                    for email_id in email_ids:
                        all_email_ids_with_folder.append((email_id, folder))
                    update_progress(count_msg=f"Gefundene E-Mails: {total_ids_found}")
                else:
                    fetch_errors += 1
                    logging.warning(f"Thread: Fehler beim Abrufen der IDs aus Ordner '{folder}'.")
                    update_progress(error_count=fetch_errors) # Fehlerzahl direkt aktualisieren

            # ID-Abruf Verbindung schließen (nur wenn IMAP und lokal geöffnet)
            if mail_connection and account.protocol == 'imap':
                 try: mail_connection.logout()
                 except: pass
                 logging.debug(f"Thread: IMAP Verbindung für ID-Abruf geschlossen.")


            results['total_found'] = total_ids_found
            if total_ids_found > 0:
                 progressbar['maximum'] = total_ids_found
            else:
                 progressbar['maximum'] = 1 # Verhindert Division durch Null

            if fetch_errors > 0:
                 logging.warning(f"Thread: Fehler beim Abrufen von IDs aus {fetch_errors} Ordner(n).")
                 # Optional: Kurze Pause, damit Benutzer es sieht? time.sleep(1)

            if not all_email_ids_with_folder:
                 update_progress(status_msg="Keine E-Mails in den Ordnern gefunden.")
                 logging.info("Thread: Keine E-Mails gefunden.")
                 # Beende Thread hier, da nichts zu tun ist
                 raise StopIteration("Keine Emails gefunden") # Eigene Exception zum sauberen Beenden

            # --- Phase 2: Download und Archivierung ---
            # TODO: age_days aus GUI Einstellung holen statt fest 30
            age_days_gui = 30
            update_progress(status_msg=f"Beginne Download & Speichern ({total_ids_found} E-Mails, Archiv > {age_days_gui} T.)...")

            try:
                 # Verbindung für Download aufbauen
                 logging.debug(f"Thread: Stelle {account.protocol.upper()} Verbindung für Download her.")
                 if account.protocol == 'imap':
                     download_connection = imaplib.IMAP4_SSL(account.server, account.port, timeout=20)
                     download_connection.login(account.email_address, account.password)
                 elif account.protocol == 'pop3':
                      download_connection = poplib.POP3_SSL(account.server, account.port, timeout=20)
                      download_connection.user(account.email_address)
                      download_connection.pass_(account.password)
                 logging.info(f"Thread: {account.protocol.upper()} Verbindung für Download für {account.email_address} hergestellt.")

                 current_folder_imap = None
                 for i, (email_id, folder_name) in enumerate(all_email_ids_with_folder):
                     status_text = f"Verarbeite '{folder_name}' ({i+1}/{total_ids_found})"
                     update_progress(status_msg=status_text, progress_val=i)

                     try:
                         if account.protocol == 'imap':
                             if current_folder_imap != folder_name:
                                 logging.debug(f"Thread: Wähle IMAP Ordner '{folder_name}'")
                                 try:
                                     # Ordnernamen immer in Anführungszeichen setzen für IMAP (readonly)
                                     encoded_folder = f'"{folder_name}"'
                                     status, _ = download_connection.select(encoded_folder, readonly=True)
                                     if status != 'OK':
                                          # Fallback ohne Anführungszeichen versuchen
                                          logging.warning(f"Thread: Konnte Ordner {encoded_folder} nicht auswählen (Status {status}), versuche ohne Anführungszeichen...")
                                          status_alt, _ = download_connection.select(folder_name, readonly=True)
                                          if status_alt != 'OK':
                                              raise imaplib.IMAP4.error(f"Konnte Ordner '{folder_name}' nicht auswählen (Status: {status}/{status_alt})")
                                     current_folder_imap = folder_name
                                 except Exception as select_err:
                                     logging.error(f"Thread: Fehler beim Auswählen des IMAP Ordners '{folder_name}': {select_err}")
                                     results['errors'] += 1
                                     update_progress(error_count=results['errors'])
                                     continue # Nächste E-Mail

                         # E-Mail verarbeiten (diese Funktion loggt intern bei Fehlern)
                         result = self._process_single_email_cli(account, email_id, folder_name, age_days_gui, download_connection)
                         results['processed'] += 1
                         if result == "archived":
                             results['archived'] += 1
                         elif result == "saved_new": # Neue Kategorie für neuere Mails
                             results['saved_new'] += 1
                         elif result == "skipped_age":
                              # Dies sollte jetzt nicht mehr passieren, da wir sie in 'emails' speichern
                              logging.warning(f"Thread: Unerwarteter Status 'skipped_age' erhalten von _process_single_email_cli für ID {email_id.decode()}.")
                              # Zähle es vorerst als Fehler oder ignoriere es? Ignorieren ist weniger verwirrend.
                         else: # "error"
                             results['errors'] += 1
                             update_progress(error_count=results['errors'])

                     except Exception as proc_err:
                          # Schwerwiegender Fehler bei dieser E-Mail
                          logging.error(f"Thread: Unerwarteter Fehler bei Verarbeitung von Email ID {email_id.decode()} aus Ordner {folder_name}: {proc_err}\n{traceback.format_exc()}")
                          results['errors'] += 1
                          update_progress(error_count=results['errors'])
                          # Hier könnte man überlegen, den Thread abzubrechen bei zu vielen Fehlern

                 # Fortschritt auf 100% setzen am Ende
                 update_progress(progress_val=total_ids_found)

            except ConnectionError as ce: # Abfangen von oben
                 raise ce # Weitergeben an äußeres try/except
            except Exception as dl_loop_err:
                 logging.error(f"Thread: Fehler in der Download/Verarbeitungsschleife: {dl_loop_err}\n{traceback.format_exc()}")
                 # Hier einen allgemeinen Fehler setzen
                 raise RuntimeError(f"Fehler während der Verarbeitung: {dl_loop_err}") from dl_loop_err
            finally:
                 # Download Verbindung immer schließen
                 if download_connection:
                     try:
                         if account.protocol == 'imap' and download_connection.state != 'LOGOUT': download_connection.logout()
                         elif account.protocol == 'pop3': download_connection.quit()
                         logging.debug(f"Thread: {account.protocol.upper()} Download Verbindung geschlossen.")
                     except Exception as close_err:
                         logging.warning(f"Thread: Fehler beim Schließen der Download-Verbindung: {close_err}")

        except StopIteration as si: # Sauberes Ende, wenn keine Mails gefunden
             final_message = str(si)
        except ConnectionError as ce: # Verbindungsfehler explizit fangen
             results['errors'] = results['total_found'] - results['processed'] # Rest als Fehler annehmen
             final_message = f"Verbindungsfehler: {ce}"
             logging.critical(f"Thread: Kritischer Verbindungsfehler: {ce}")
        except Exception as e:
             results['errors'] = results['total_found'] - results['processed'] # Fehler für Rest annehmen
             final_message = f"Unerwarteter Fehler: {e}"
             logging.critical(f"Thread: Kritischer Fehler im Archivierungs-Worker: {e}\n{traceback.format_exc()}")
        else:
             # Kein Fehler aufgetreten
             # Nachricht anpassen, um beide Speicherorte zu erwähnen
             final_message = f"Verarbeitung abgeschlossen. {results['archived']} E-Mails archiviert (> {age_days_gui} T.), {results['saved_new']} neuere gespeichert."
             if results['errors'] > 0:
                 final_message += f" ({results['errors']} Fehler)"
             logging.info(f"Thread: Verarbeitung beendet. {results}")

        # --- Phase 3: Abschluss (GUI im Main Thread aktualisieren) ---
        def final_update_task():
            try:
                # Nur zerstören, wenn Fenster noch existiert
                if progress_window and progress_window.winfo_exists():
                    progress_window.destroy() # Fortschrittsfenster schließen
            except tk.TclError: pass # Fenster könnte schon weg sein

            self.update_status(final_message, error=(results['errors'] > 0 or 'Fehler' in final_message))
            messagebox.showinfo("Verarbeitung beendet", final_message, parent=self)
            self._set_ui_state(tk.NORMAL) # Haupt-UI wieder aktivieren
            logging.info("Haupt-UI nach Verarbeitung wieder aktiviert.")

        self.after(100, final_update_task) # Kurze Verzögerung, damit letzte Updates sichtbar sind


    def _fetch_email_ids(self, account: EmailAccount, folder: str = "inbox", mail_connection=None) -> list[bytes] | None:
        """
        Ruft die IDs aller E-Mails aus einem bestimmten Ordner (IMAP) oder der Inbox (POP3) ab.
        Kann eine bestehende Mail-Verbindung wiederverwenden.
        Gibt eine Liste von Bytes zurück oder None bei Fehlern.
        """
        mail = mail_connection # Bestehende Verbindung nutzen, falls übergeben
        close_connection_locally = False # Nur schließen, wenn hier geöffnet
        ids_fetched = [] # Liste für die Ergebnisse

        try:
            if account.protocol == 'imap':
                if not mail: # Nur verbinden, wenn keine Verbindung übergeben wurde
                    logging.debug(f"_fetch_email_ids: Erstelle temporäre IMAP Verbindung für Ordner '{folder}'.")
                    mail = imaplib.IMAP4_SSL(account.server, account.port, timeout=15)
                    mail.login(account.email_address, account.password)
                    close_connection_locally = True
                else:
                    logging.debug(f"_fetch_email_ids: Nutze bestehende IMAP Verbindung für Ordner '{folder}'.")


                # Ordner auswählen (mit Anführungszeichen für mögliche Leerzeichen/Sonderzeichen)
                try:
                     # Ordnernamen korrekt quoten (wichtig für Namen mit Leerzeichen oder Sonderzeichen)
                     encoded_folder = f'"{folder}"' # Einfaches Quoting
                     # encoded_folder = imaplib.quote(folder) # Bessere Methode, falls verfügbar? Nein, quote ist für Strings in Kommandos
                     logging.debug(f"Versuche IMAP SELECT für: {encoded_folder}")
                     status_select, _ = mail.select(encoded_folder, readonly=True) # Readonly ist sicherer für ID-Abruf
                     if status_select != 'OK':
                          logging.warning(f"IMAP SELECT für '{encoded_folder}' fehlgeschlagen (Status: {status_select}). Versuche ohne Quotes...")
                          status_select_alt, _ = mail.select(folder, readonly=True)
                          if status_select_alt != 'OK':
                              logging.error(f"IMAP SELECT für Ordner '{folder}' endgültig fehlgeschlagen (Status: {status_select}/{status_select_alt}).")
                              raise imaplib.IMAP4.error(f"IMAP Fehler: Konnte Ordner '{folder}' nicht auswählen.")
                          else:
                               logging.debug(f"IMAP SELECT für '{folder}' (ohne Quotes) erfolgreich.")
                     else:
                          logging.debug(f"IMAP SELECT für '{encoded_folder}' erfolgreich.")

                except Exception as select_err:
                     logging.error(f"Fehler beim Auswählen des IMAP-Ordners '{folder}': {select_err}")
                     # Verbindung schließen, wenn lokal geöffnet, und Fehler signalisieren
                     if close_connection_locally and mail:
                          try: mail.logout()
                          except: pass
                     return None # Signalisiert Fehler

                # E-Mails suchen
                logging.debug(f"Führe IMAP SEARCH ALL im Ordner '{folder}' aus.")
                status_search, email_ids_raw = mail.search(None, 'ALL')
                if status_search == "OK":
                    ids_fetched = email_ids_raw[0].split() # Liste von Bytes
                    logging.info(f"{len(ids_fetched)} E-Mail IDs im Ordner '{folder}' für {account.email_address} gefunden.")
                else:
                    logging.error(f"IMAP Suche im Ordner '{folder}' fehlgeschlagen: Status {status_search}, Data: {email_ids_raw}")
                    # Hier keinen Fehler werfen, könnte ein leerer Ordner sein oder Rechteproblem, das nicht kritisch ist?
                    # Doch, ein Fehler ist hier angebracht, da der Status nicht OK war.
                    raise imaplib.IMAP4.error(f"IMAP Suche im Ordner '{folder}' fehlgeschlagen: Status {status_search}")


            elif account.protocol == 'pop3':
                # POP3 unterstützt keine Ordner, ignoriere 'folder' Parameter
                if folder.lower() != "inbox":
                     logging.warning("POP3 unterstützt nur den Posteingang (Inbox). Der Parameter 'folder' wird ignoriert.")

                # POP3 Verbindung kann nicht für verschiedene Ordner wiederverwendet werden.
                # Wenn eine POP3 Verbindung übergeben wird, ignorieren wir sie und bauen neu auf.
                if mail and isinstance(mail, poplib.POP3):
                    logging.debug("_fetch_email_ids: Ignoriere übergebene POP3 Verbindung, baue neu auf.")
                    try: mail.quit()
                    except: pass
                    mail = None

                # Immer neu verbinden für POP3 ID Abruf
                logging.debug(f"_fetch_email_ids: Erstelle temporäre POP3 Verbindung.")
                mail = poplib.POP3_SSL(account.server, account.port, timeout=15)
                mail.user(account.email_address)
                mail.pass_(account.password)
                close_connection_locally = True # Muss hier geschlossen werden

                # Anzahl und IDs holen (list() gibt ['+OK...', [b'1 1234', b'2 5678', ...], octets])
                response, lines, octets = mail.list()
                if response.startswith(b'+OK'):
                    # Extrahiere nur die Nachrichtennummern (als Bytes)
                    ids_fetched = [line.split()[0] for line in lines]
                    logging.info(f"{len(ids_fetched)} E-Mail IDs im POP3 Posteingang für {account.email_address} gefunden.")
                else:
                     logging.error(f"POP3 LIST Befehl fehlgeschlagen: {response}")
                     raise poplib.error_proto(f"POP3 LIST Befehl fehlgeschlagen: {response}")

            else:
                logging.error(f"Ungültiges Protokoll '{account.protocol}' in _fetch_email_ids.")
                raise ValueError(f"Ungültiges Protokoll: {account.protocol}")

            return ids_fetched # Gibt Liste zurück (kann leer sein)

        except (imaplib.IMAP4.error, poplib.error_proto, smtplib.SMTPException) as conn_err:
             # Behandle spezifische Verbindungs-/Authentifizierungsfehler
             error_message = str(conn_err).lower()
             user_readable_error = f"{account.protocol.upper()} Fehler (Ordner '{folder}'): {conn_err}"
             log_level = logging.ERROR
             if "authentication failed" in error_message or "login failed" in error_message or "invalid credentials" in error_message:
                 user_readable_error = f"Anmeldung für {account.email_address} fehlgeschlagen (Ordner '{folder}'). Bitte prüfen Sie E-Mail/Passwort."
                 log_level = logging.WARNING # Könnte temporär sein oder falsches PW
             elif "timeout" in error_message or "connection timed out" in error_message:
                 user_readable_error = f"Timeout bei Verbindung zu {account.server} (Ordner '{folder}')."
             elif "connection refused" in error_message:
                  user_readable_error = f"Verbindung zu {account.server} abgelehnt (Ordner '{folder}'). Läuft der Server?"
             elif "temporarily unavailable" in error_message:
                  user_readable_error = f"Server {account.server} temporär nicht verfügbar (Ordner '{folder}')."
                  log_level = logging.WARNING
             # Hier könnten weitere spezifische Fehlercodes von IMAP/POP3 behandelt werden

             logging.log(log_level, f"{account.protocol.upper()} Fehler beim Abrufen der E-Mail-IDs für Konto {account.email_address}, Ordner '{folder}': {conn_err}")
             # Wir geben None zurück, um den Fehler zu signalisieren
             return None
        except TimeoutError: # Fängt Socket Timeout
             logging.error(f"Timeout Fehler beim Abrufen der E-Mail-IDs für Konto {account.email_address}, Ordner '{folder}'.")
             return None
        except Exception as e:
            # Fängt alle anderen unerwarteten Fehler
            logging.error(f"Unerwarteter Fehler beim Abrufen der E-Mail-IDs für Konto {account.email_address}, Ordner '{folder}': {e}\n{traceback.format_exc()}")
            return None # Signalisiert Fehler
        finally:
             # Verbindung nur schließen, wenn sie in *dieser* Funktion geöffnet wurde
             if close_connection_locally and mail:
                 try:
                     if account.protocol == 'imap' and mail.state != 'LOGOUT':
                         mail.logout()
                         logging.debug(f"Temporäre IMAP Verbindung für ID-Abruf ({folder}) geschlossen.")
                     elif account.protocol == 'pop3':
                         mail.quit()
                         logging.debug(f"Temporäre POP3 Verbindung für ID-Abruf geschlossen.")
                 except Exception as e_close:
                     logging.error(f"Fehler beim Schließen der temporären Verbindung ({account.protocol}, Ordner {folder}): {e_close}")


    def _process_single_email(self, account: EmailAccount, email_id: bytes, folder_name: str, mail_connection) -> bool:
        """
        Veraltet - wird durch _process_single_email_cli ersetzt, auch für GUI-Nutzung.
        Behalten für den Fall, dass spezifische GUI-Logik hier benötigt würde.
        Gibt True zurück, wenn erfolgreich gespeichert (egal ob alt oder neu), sonst False.
        """
        # Rufe die CLI-Version auf, da die Logik identisch ist
        # TODO: Age Days aus GUI Einstellung holen statt fest 30
        age_days_gui = 30
        cli_result = self._process_single_email_cli(account, email_id, folder_name, age_days_gui, mail_connection)
        # Erfolg, wenn archiviert oder neu gespeichert (kein Fehler und nicht übersprungen)
        return cli_result in ["archived", "saved_new"]


    def _get_email_date(self, email_msg: email.message.Message) -> datetime.datetime | None:
        """
        Extrahiert das Datum aus dem 'Date'-Header einer E-Mail-Nachricht.
        Versucht, verschiedene Datumsformate zu parsen und gibt ein timezone-aware datetime Objekt zurück oder None.
        """
        date_str = email_msg.get('Date')
        if not date_str:
            logging.warning("Kein 'Date'-Header in der E-Mail gefunden.")
            return None

        try:
            # email.utils.parsedate_to_datetime ist gut für RFC 2822 Formate
            dt = parsedate_to_datetime(date_str)
            if dt:
                # Stelle sicher, dass das Datum timezone-aware ist
                if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
                    # Es ist ein naives Datum. Das ist problematisch für Vergleiche.
                    # Wir können nicht sicher wissen, welche Zeitzone gemeint war.
                    # Annahme: UTC ist die sicherste Wahl, obwohl es falsch sein kann.
                    logging.debug(f"Datum '{date_str}' -> '{dt}' ist timezone-naive. Nehme UTC an.")
                    return dt.replace(tzinfo=datetime.timezone.utc)
                else:
                    # Es ist bereits timezone-aware
                    logging.debug(f"Datum '{date_str}' -> '{dt}' erfolgreich geparsed (timezone-aware).")
                    return dt
            else:
                # Konnte nicht geparsed werden
                logging.warning(f"Konnte Datum '{date_str}' nicht mit parsedate_to_datetime parsen.")
                return None

        except Exception as e:
            logging.warning(f"Fehler beim Parsen des Datums '{date_str}' mit parsedate_to_datetime: {e}. Versuche Fallbacks.")
            # Fallback mit anderen Bibliotheken oder Formaten (optional)
            # try:
            #     from dateutil import parser
            #     return parser.parse(date_str) # dateutil ist oft robuster
            # except ImportError:
            #     pass
            # except Exception as e_fallback:
            #      logging.error(f"Endgültiger Fehler beim Parsen des Datums: '{date_str}', Fehler: {e_fallback}")

            return None


    def _is_older_than_days(self, email_date: datetime.datetime | None, days: int = 5) -> bool:
        """
        Prüft, ob ein gegebenes Datum älter als eine bestimmte Anzahl von Tagen ist.
        Verwendet timezone-aware Vergleiche.
        Gibt False zurück, wenn kein Datum vorhanden ist.
        """
        if not email_date:
            logging.debug("_is_older_than_days: Kein Datum angegeben, Ergebnis: False (wird als 'nicht alt' behandelt).")
            return False # Unbekanntes Datum wird als nicht alt behandelt

        # Stelle sicher, dass email_date timezone-aware ist (sollte durch _get_email_date erledigt sein)
        if email_date.tzinfo is None or email_date.tzinfo.utcoffset(email_date) is None:
             logging.warning(f"_is_older_than_days: Vergleiche timezone-naive E-Mail-Datum {email_date}. Ergebnis kann ungenau sein. Nehme UTC an.")
             email_date = email_date.replace(tzinfo=datetime.timezone.utc)

        # Aktuelle Zeit, timezone-aware (UTC)
        now_utc = datetime.datetime.now(datetime.timezone.utc)

        # Berechne die Zeitdifferenz
        time_difference = now_utc - email_date

        # Vergleiche mit dem Zeitdelta
        is_older = time_difference > datetime.timedelta(days=days)
        logging.debug(f"_is_older_than_days: E-Mail Datum={email_date}, Now(UTC)={now_utc}, Diff={time_difference}, OlderThan {days} days? -> {is_older}")
        return is_older


    def _download_email(self, account: EmailAccount, email_id: bytes, folder_name: str, mail_connection) -> bytes | None:
        """
        Lädt den Rohinhalt einer einzelnen E-Mail vom Server herunter.
        Nutzt die übergebene, bereits initialisierte und ggf. selektierte Verbindung.
        Gibt die rohen Bytes der E-Mail zurück oder None bei Fehlern.
        """
        mail = mail_connection # Bestehende Verbindung nutzen
        email_id_str = email_id.decode('ascii', 'ignore') # Für Logging

        try:
            if not mail:
                 logging.error(f"Download fehlgeschlagen: Keine gültige Mail-Verbindung für ID {email_id_str} übergeben.")
                 raise ConnectionError("Keine gültige Mail-Verbindung zum Download übergeben.")

            if account.protocol == 'imap':
                # Der Ordner sollte bereits ausgewählt sein. Nur Fetch ausführen.
                fetch_cmd = '(RFC822)'
                logging.debug(f"IMAP Fetch für ID {email_id_str} aus Ordner '{folder_name}'...")
                status, msg_data = mail.fetch(email_id, fetch_cmd)

                if status == 'OK':
                    # msg_data Struktur prüfen: [(b'1 (RFC822 {size}', b'raw_email_content'), b')'] oder [b'1 (RFC822 {size}\r\nraw_email_content\r\n)'] bei manchen Servern
                    raw_email_content = None
                    if msg_data and msg_data[0] is not None:
                         if isinstance(msg_data[0], tuple) and len(msg_data[0]) >= 2: # Standard-Format
                              raw_email_content = msg_data[0][1]
                         elif isinstance(msg_data[0], bytes) and b'RFC822' in msg_data[0]: # alternatives Format
                              # Finde den Start des E-Mail-Inhalts nach dem Header-Teil
                              header_end = msg_data[0].find(b'\r\n')
                              if header_end != -1:
                                   raw_email_content = msg_data[0][header_end+2:]
                                   # Entferne das abschließende ')' wenn vorhanden
                                   if raw_email_content.endswith(b')'):
                                        raw_email_content = raw_email_content[:-1].rstrip()

                    if raw_email_content is not None:
                        logging.debug(f"E-Mail ID {email_id_str} erfolgreich via IMAP aus '{folder_name}' heruntergeladen ({len(raw_email_content)} Bytes).")
                        return raw_email_content
                    else:
                         logging.error(f"Unerwartete Antwortstruktur beim IMAP Fetch für ID {email_id_str} in Ordner '{folder_name}': {msg_data}")
                         raise imaplib.IMAP4.error(f"Unerwartete Antwortstruktur beim IMAP Fetch für ID {email_id_str}")

                else:
                    # Mögliche Fehler: Nachricht nicht gefunden, Berechtigungsproblem etc.
                    logging.error(f"IMAP Fetch fehlgeschlagen für ID {email_id_str} in Ordner '{folder_name}'. Status: {status}, Data: {msg_data}")
                    raise imaplib.IMAP4.error(f"IMAP Fetch fehlgeschlagen für ID {email_id_str}: Status {status}")

            elif account.protocol == 'pop3':
                # POP3: Verbindung sollte bereits bestehen.
                logging.debug(f"POP3 RETR für ID {email_id_str}...")
                resp, raw_email_lines, octets = mail.retr(email_id_str)
                if resp.startswith(b'+OK'):
                     raw_email = b'\r\n'.join(raw_email_lines)
                     logging.debug(f"E-Mail ID {email_id_str} erfolgreich via POP3 heruntergeladen ({octets} Bytes).")
                     return raw_email
                else:
                     logging.error(f"POP3 RETR fehlgeschlagen für ID {email_id_str}. Response: {resp}")
                     raise poplib.error_proto(f"POP3 RETR fehlgeschlagen für ID {email_id_str}: {resp}")
            else:
                # Sollte nie passieren
                logging.critical(f"Ungültiges Protokoll '{account.protocol}' in _download_email.")
                raise ValueError(f"Ungültiges Protokoll: {account.protocol}")

        except (imaplib.IMAP4.error, poplib.error_proto) as conn_err:
            logging.error(f"{account.protocol.upper()} Fehler beim Herunterladen der E-Mail ID {email_id_str} aus Ordner '{folder_name}': {conn_err}")
            return None
        except ConnectionError as ce:
             logging.error(f"Verbindungsfehler beim Download Versuch für E-Mail ID {email_id_str}: {ce}")
             return None
        except Exception as e:
            logging.error(f"Unerwarteter Fehler beim Herunterladen der E-Mail ID {email_id_str} aus Ordner '{folder_name}': {e}\n{traceback.format_exc()}")
            return None


    def _create_account_folder(self, account: EmailAccount) -> str:
        """
        Erstellt den Basisordner für ein E-Mail-Konto im Dateisystem, falls nicht vorhanden.
        Verwendet einen gesäuberten Kontonamen als Ordnernamen.
        Gibt den Pfad zum Kontoordner zurück.
        """
        # Sanitize account name für Dateisystem
        # Ersetze ungültige Zeichen, aber erlaube Umlaute etc.
        invalid_chars = '<>:"/\\|?*'
        safe_account_name = account.name
        for char in invalid_chars:
             safe_account_name = safe_account_name.replace(char, '_')
        safe_account_name = safe_account_name.strip() # Führende/folgende Leerzeichen entfernen
        if not safe_account_name: safe_account_name = f"konto_{account.email_address.split('@')[0]}" # Fallback

        # Basisverzeichnis für alle Archive (könnte konfigurierbar sein)
        base_archive_dir = "EmailArchiv"
        account_folder = os.path.join(base_archive_dir, safe_account_name) # Im Unterordner EmailArchiv
        try:
            # Erstelle Basisordner und Kontoordner
            os.makedirs(account_folder, exist_ok=True)
            logging.debug(f"Konto-Ordner sichergestellt: {os.path.abspath(account_folder)}")
        except OSError as e:
             logging.error(f"Fehler beim Erstellen des Konto-Ordners '{account_folder}': {e}")
             # Hier eventuell einen Fallback-Ordner verwenden oder Fehler auslösen?
             raise  # Fehler weitergeben, da Speichern sonst nicht möglich ist
        return account_folder

    def _create_target_folder(self, account_base_path: str, target_type: str, original_folder_name: str) -> str:
        """
        Erstellt den Zielordner ('emails' oder 'archiv') innerhalb des Kontoordners,
        inklusive Unterordner für den ursprünglichen IMAP-Ordner (gesäubert) und einem Datumsunterordner.
        Gibt den vollständigen Pfad zum Datumsordner zurück (z.B. ./EmailArchiv/KontoName/archiv/Gesendet/2023-10-27).
        """
        try:
            # Sanitize original_folder_name
            invalid_chars = '<>:"/\\|?*'
            safe_folder_name = original_folder_name
            for char in invalid_chars:
                 safe_folder_name = safe_folder_name.replace(char, '_')
            # Speziell für IMAP: Ersetze Hierarchie-Trenner (oft '/') durch einen anderen Charakter
            safe_folder_name = safe_folder_name.replace('/', '__') # z.B. Arbeit/Projekte -> Arbeit__Projekte
            safe_folder_name = safe_folder_name.strip()
            if not safe_folder_name: safe_folder_name = "_unbekannter_ordner_"

            # Pfad zusammensetzen
            type_folder = os.path.join(account_base_path, target_type)
            source_folder_path = os.path.join(type_folder, safe_folder_name)
            date_str = datetime.datetime.now().strftime("%Y-%m-%d")
            date_folder = os.path.join(source_folder_path, date_str)

            # Alle notwendigen Ordner erstellen
            os.makedirs(date_folder, exist_ok=True)
            logging.debug(f"Ziel-Ordner sichergestellt: {os.path.abspath(date_folder)}")
            return date_folder
        except OSError as e:
            logging.error(f"Fehler beim Erstellen des Ziel-Ordners unter '{account_base_path}/{target_type}/{safe_folder_name}': {e}")
            raise # Fehler weitergeben


    def _save_email(self, account: EmailAccount, email_msg: email.message.Message, target_date_folder: str) -> str | None:
        """
        Speichert die E-Mail als .eml-Datei im angegebenen Zielordner.
        Verwendet einen sicheren Dateinamen basierend auf Zeitstempel und Betreff.
        Gibt den vollständigen Pfad zur gespeicherten Datei zurück oder None bei Fehlern.
        """
        try:
            # Betreff extrahieren, dekodieren und säubern
            subject_header = email_msg.get('Subject', 'Kein_Betreff')
            decoded_subject = self._decode_header(subject_header)
            if not decoded_subject: decoded_subject = "Kein_Betreff"

            # Dateinamen sicher machen
            invalid_chars = '<>:"/\\|?*'
            safe_subject = decoded_subject
            for char in invalid_chars:
                 safe_subject = safe_subject.replace(char, '_')
            safe_subject = safe_subject.strip()
            # Begrenze die Länge des Betreffs im Dateinamen
            max_subj_len = 80
            safe_subject = safe_subject[:max_subj_len]
            if not safe_subject: safe_subject = "Kein_Betreff" # Erneuter Fallback

            # Eindeutigen Dateinamen generieren
            email_dt = self._get_email_date(email_msg)
            timestamp = email_dt.strftime("%Y%m%d_%H%M%S") if email_dt else datetime.datetime.now().strftime("%Y%m%d_%H%M%S%f")[:-3]

            # Eindeutigkeit erhöhen durch Message-ID Hash oder Zeitstempel mit Mikrosekunden
            msg_id = email_msg.get('Message-ID', '')
            unique_suffix = "_" + str(abs(hash(msg_id)))[-6:] if msg_id else "_" + datetime.datetime.now().strftime("%f")

            filename = f"{timestamp}_{safe_subject}{unique_suffix}.eml"
            filepath = os.path.join(target_date_folder, filename)

            # Überschreiben verhindern (falls Hash/Timestamp nicht eindeutig genug war)
            counter = 1
            original_filepath = filepath
            while os.path.exists(filepath):
                name, ext = os.path.splitext(original_filepath)
                filepath = f"{name}_{counter}{ext}"
                counter += 1
                if counter > 100: # Schutz gegen Endlosschleife
                     logging.error(f"Zu viele Dateien mit ähnlichem Namen wie '{original_filepath}'. Überspringe Speichern.")
                     return None

            # E-Mail im Rohformat speichern (.eml)
            with open(filepath, 'wb') as outfile:
                # Verwende den Generator für bessere Speicherverwaltung bei großen Mails?
                # from email.generator import BytesGenerator
                # generator = BytesGenerator(outfile)
                # generator.flatten(email_msg)
                # Einfacher:
                 outfile.write(email_msg.as_bytes())


            logging.info(f"E-Mail gespeichert als '{os.path.basename(filepath)}' in: {target_date_folder}")
            return filepath

        except OSError as e:
            logging.error(f"Datei-System Fehler beim Speichern der E-Mail '{decoded_subject}' in '{target_date_folder}': {e}")
        except Exception as e:
            logging.error(f"Allgemeiner Fehler beim Speichern der E-Mail-Datei '{decoded_subject}': {e}\n{traceback.format_exc()}")

        return None # Signalisiert Fehler


    def _process_attachments(self, email_msg: email.message.Message, target_date_folder: str):
        """
        Verarbeitet und speichert Anhänge einer E-Mail im Unterordner 'anhänge'
        des angegebenen Zielordners. Erstellt den Ordner nur, wenn Anhänge vorhanden sind.
        """
        attachments_folder = os.path.join(target_date_folder, "anhänge")
        attachment_saved = False # Um den Ordner nur bei Bedarf zu erstellen

        for part in email_msg.walk():
            # Prüfen, ob es sich um einen Anhang handelt
            content_disposition = str(part.get('Content-Disposition'))
            is_explicit_attachment = 'attachment' in content_disposition.lower()
            filename = part.get_filename()

            # Behandle als Anhang, wenn:
            # 1. Explizit als 'attachment' deklariert UND Dateiname vorhanden
            # 2. Nicht 'inline' ODER kein Text-Typ UND Dateiname vorhanden (z.B. Bilder ohne Disposition)
            # 3. Content-Type nicht text/* oder multipart/* UND Dateiname vorhanden (generischer Fallback)

            is_attachment = False
            if filename: # Nur Teile mit Dateinamen sind potenzielle Anhänge
                 if is_explicit_attachment:
                      is_attachment = True
                 elif 'inline' not in content_disposition.lower():
                       maintype = part.get_content_maintype()
                       if maintype not in ['text', 'multipart']:
                            is_attachment = True
                 # Hier könnte man noch spezifische Content-Types erlauben/ausschließen

            if is_attachment:
                if not attachment_saved: # Nur beim ersten Anhang den Ordner erstellen
                     try:
                         os.makedirs(attachments_folder, exist_ok=True)
                         attachment_saved = True
                         logging.debug(f"Anhang-Ordner erstellt/gefunden: {attachments_folder}")
                     except OSError as e:
                          logging.error(f"Fehler beim Erstellen des Anhang-Ordners '{attachments_folder}': {e}")
                          # Breche Anhangverarbeitung für diese Mail ab, wenn Ordner nicht erstellt werden kann
                          return

                # Dateinamen dekodieren und säubern
                decoded_filename = self._decode_header(filename) # Verwende Header-Dekodierung
                if not decoded_filename: decoded_filename = f"Unbenannter_Anhang_{datetime.datetime.now().timestamp()}"

                # Dateinamen für Dateisystem sicher machen
                invalid_chars = '<>:"/\\|?*'
                safe_filename = decoded_filename
                for char in invalid_chars:
                     safe_filename = safe_filename.replace(char, '_')
                safe_filename = safe_filename.strip()
                if not safe_filename: safe_filename = f"Anhang_{datetime.datetime.now().timestamp()}.bin" # Fallback

                filepath = os.path.join(attachments_folder, safe_filename)

                # Überschreiben verhindern
                counter = 1
                original_filepath = filepath
                while os.path.exists(filepath):
                    name, ext = os.path.splitext(original_filepath)
                    filepath = f"{name}_{counter}{ext}"
                    counter += 1
                    if counter > 100:
                         logging.error(f"Zu viele Dateien mit ähnlichem Namen wie '{os.path.basename(original_filepath)}' in '{attachments_folder}'. Überspringe Speichern.")
                         filepath = None
                         break
                if filepath is None: continue # Nächsten Anhang versuchen

                # Anhang speichern
                logging.debug(f"Speichere Anhang: {filepath}")
                try:
                    payload = part.get_payload(decode=True) # Payload dekodieren (Base64 etc.)
                    if payload is not None: # Prüfen ob Payload existiert
                        with open(filepath, 'wb') as outfile:
                             outfile.write(payload)
                        logging.info(f"Anhang '{safe_filename}' ({len(payload)} Bytes) gespeichert.")
                    else:
                         logging.warning(f"Anhang '{safe_filename}' hatte keinen Inhalt (Payload=None). Datei nicht erstellt.")
                except FileNotFoundError: # Sollte nicht passieren wegen makedirs
                    logging.error(f"Fehler: Zielordner '{attachments_folder}' für Anhang '{safe_filename}' nicht gefunden.")
                except OSError as e:
                    logging.error(f"Fehler beim Schreiben des Anhangs '{safe_filename}' nach '{filepath}': {e}")
                except Exception as e:
                    logging.error(f"Allgemeiner Fehler beim Speichern des Anhangs '{safe_filename}': {e}\n{traceback.format_exc()}")

            # Debugging für übersprungene Teile
            # elif filename or 'attachment' in content_disposition.lower() or part.get_content_maintype() not in ['text','multipart']:
            #     logging.debug(f"Überspringe potenziellen Anhang: Name='{filename}', Type={part.get_content_type()}, Disp={content_disposition}")


    def update_status(self, message: str, error: bool = False):
        """
        Aktualisiert die Statusanzeige am unteren Rand des Hauptfensters.
        Färbt die Nachricht bei Bedarf rot. Loggt die Nachricht auch.
        Stellt sicher, dass das Label existiert.
        """
        if not self.status_label:
             # Sollte nicht passieren, wenn Initialisierung korrekt läuft
             print(f"Status Update Ignoriert (Label nicht bereit): {message}")
             logging.warning(f"Status Update Ignoriert (Label nicht bereit): {message}")
             return

        # Lange Nachrichten kürzen für die Statusleiste
        display_message = message
        if len(display_message) > 150:
             display_message = display_message[:147] + "..."

        if error:
            self.status_label.config(text=f"FEHLER: {display_message}", foreground="red")
            logging.error(f"Status Update (Error): {message}") # Logge die volle Nachricht
        else:
            self.status_label.config(text=display_message, foreground="black")
            logging.info(f"Status Update: {message}") # Logge die volle Nachricht

        # update_idletasks() kann bei häufigen Updates die GUI blockieren.
        # Besser ist es oft, dies nur bei wichtigen Updates oder am Ende einer Operation zu tun.
        # self.update_idletasks()
        # Stattdessen: schedule update mit self.after(0, self.status_label.update) ? Nein, config reicht normalerweise.


    # --- Erweiterungen: E-Mail Explorer ---

    def _open_email_explorer(self):
        """
        Öffnet ein neues Fenster für den E-Mail Explorer, um archivierte E-Mails und Anhänge anzuzeigen.
        """
        # Basisverzeichnis für das Archiv festlegen
        base_archive_dir = os.path.abspath("EmailArchiv")

        # Prüfen, ob das Basisverzeichnis existiert
        if not os.path.isdir(base_archive_dir):
             messagebox.showinfo("Hinweis", f"Das Archivverzeichnis '{base_archive_dir}' wurde noch nicht gefunden.\nBitte archivieren Sie zuerst E-Mails.", parent=self)
             return

        explorer_window = Toplevel(self)
        explorer_window.title(f"Archiv Explorer - [{base_archive_dir}]")
        explorer_window.geometry("950x700")
        explorer_window.transient(self)
        # explorer_window.grab_set() # Nicht grabben, damit man parallel arbeiten kann

        # --- Suchleiste ---
        search_frame = ttk.Frame(explorer_window)
        search_frame.pack(pady=5, fill=X, padx=10)

        search_label = ttk.Label(search_frame, text="Suche (in .eml Dateien):")
        search_label.pack(side=LEFT, padx=5)

        search_entry = ttk.Entry(search_frame, width=50)
        search_entry.pack(side=LEFT, fill=X, expand=True, padx=5)

        # Referenz auf Treeview für Callbacks speichern (wird später erstellt)
        tree_ref = {}

        # Callback Funktion für die Suche
        def perform_search_callback(event=None):
            search_term = search_entry.get().strip()
            tree = tree_ref.get('tree')
            status_label = tree_ref.get('status_label')
            if not tree or not status_label: return # Noch nicht initialisiert

            if fuzz is None and search_term:
                 messagebox.showwarning("Suche nicht verfügbar", "Die Bibliothek 'fuzzywuzzy' wurde nicht gefunden. Suche ist deaktiviert.", parent=explorer_window)
                 return

            logging.info(f"Explorer: Starte Suche nach '{search_term}'")
            status_label.config(text=f"Suche nach '{search_term}'...")
            explorer_window.update_idletasks()

            tree.delete(*tree.get_children()) # Alten Tree Inhalt löschen
            # Treeview mit Suchergebnis befüllen (oder leer lassen, wenn kein Begriff)
            found_items = self._populate_tree_explorer(tree, base_archive_dir, search_term if search_term else None)
            result_text = f"{found_items} Element(e) gefunden für '{search_term}'." if search_term else f"Archivstruktur geladen ({found_items} Elemente)."
            status_label.config(text=result_text)
            logging.info(f"Explorer: Suche beendet. {result_text}")

        search_button = ttk.Button(search_frame, text="Suchen", command=perform_search_callback)
        search_button.pack(side=LEFT, padx=5)
        search_entry.bind('<Return>', perform_search_callback) # Enter Key löst Suche aus

        # Callback Funktion zum Leeren
        def clear_search_callback():
             tree = tree_ref.get('tree')
             status_label = tree_ref.get('status_label')
             if not tree or not status_label: return

             logging.info("Explorer: Setze Suche zurück.")
             search_entry.delete(0, END) # Suchfeld leeren
             status_label.config(text="Lade Archivstruktur neu...")
             explorer_window.update_idletasks()
             tree.delete(*tree.get_children()) # Tree leeren
             found_items = self._populate_tree_explorer(tree, base_archive_dir, None) # Tree neu befüllen ohne Suche
             status_label.config(text=f"Archivstruktur geladen ({found_items} Elemente).")
             logging.info("Explorer: Suche zurückgesetzt.")


        clear_button = ttk.Button(search_frame, text="Leeren", command=clear_search_callback)
        clear_button.pack(side=LEFT, padx=5)

        # --- Treeview für die Anzeige ---
        tree_frame = ttk.Frame(explorer_window)
        tree_frame.pack(fill=BOTH, expand=True, padx=10, pady=5)

        tree = ttk.Treeview(tree_frame, columns=('type', 'size', 'date'), show='tree headings')
        self.explorer_tree = tree # Referenz für andere Methoden speichern
        tree_ref['tree'] = tree # Referenz für Callbacks

        # Spalten konfigurieren
        tree.heading('#0', text='Ordner / Datei', anchor='w')
        tree.column('#0', width=450, minwidth=250, stretch=tk.YES)
        tree.heading('type', text='Typ', anchor='w')
        tree.column('type', width=80, minwidth=60, stretch=tk.NO, anchor='w')
        tree.heading('size', text='Größe', anchor='e') # rechtsbündig
        tree.column('size', width=100, minwidth=80, stretch=tk.NO, anchor='e')
        tree.heading('date', text='Datum (Mail/Änderung)', anchor='center')
        tree.column('date', width=150, minwidth=120, stretch=tk.NO, anchor='center')

        # Scrollbars hinzufügen
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.pack(side='right', fill='y')
        hsb.pack(side='bottom', fill='x')
        tree.pack(side='left', fill='both', expand=True)

        # --- Statusleiste für den Explorer ---
        status_label_explorer = ttk.Label(explorer_window, text="Lade Archivstruktur...", anchor="w")
        status_label_explorer.pack(side=tk.BOTTOM, fill=X, padx=10, pady=5)
        tree_ref['status_label'] = status_label_explorer

        # Treeview initial befüllen
        explorer_window.update_idletasks() # Sicherstellen, dass UI bereit ist
        logging.info(f"Explorer: Lade initiale Struktur aus {base_archive_dir}")
        found_items_init = self._populate_tree_explorer(tree, base_archive_dir, None) # Starte im Basisverzeichnis ohne Suche
        status_label_explorer.config(text=f"Archivstruktur geladen ({found_items_init} Elemente).")
        logging.info(f"Explorer: Initiale Struktur geladen.")


        # --- Event Bindings für den Treeview ---
        def open_email_or_attachment_callback(event):
            selected_items = tree.selection()
            if not selected_items: return
            item_id = selected_items[0]
            item_info = tree.item(item_id)
            item_tags = item_info.get("tags", [])

            if "folder_item" in item_tags:
                 tree.item(item_id, open=not tree.item(item_id, 'open'))
                 return

            item_path = self._get_item_path_from_tree(tree, item_id, base_archive_dir) # Basisverzeichnis übergeben
            if not item_path:
                 logging.error(f"Konnte Pfad für Item ID {item_id} nicht ermitteln.")
                 messagebox.showerror("Fehler", "Konnte den Dateipfad nicht bestimmen.", parent=explorer_window)
                 return

            if os.path.isfile(item_path):
                logging.info(f"Explorer: Öffne Item: {item_path}")
                if "email_item" in item_tags: # E-Mail Datei öffnen (.eml)
                    self._display_email_content(item_path)
                elif "attachment_item" in item_tags: # Anhang öffnen (versuchen)
                    self._open_external_file(item_path, explorer_window)
            elif os.path.isdir(item_path):
                 # Doppelklick auf Ordner (bereits durch folder_item oben behandelt)
                 pass
            else:
                 logging.warning(f"Doppelklick auf ungültigen Pfad: {item_path}")
                 messagebox.showwarning("Pfad ungültig", f"Der Pfad '{item_path}' ist keine gültige Datei oder Verzeichnis.", parent=explorer_window)

        def handle_context_menu_callback(event):
            item_id = tree.identify_row(event.y)
            if not item_id: return

            tree.selection_set(item_id)
            tree.focus(item_id)

            item_info = tree.item(item_id)
            item_tags = item_info.get("tags", [])
            item_path = self._get_item_path_from_tree(tree, item_id, base_archive_dir)

            context_menu = tk.Menu(explorer_window, tearoff=0)
            action_added = False

            if not item_path: # Pfad konnte nicht ermittelt werden
                 context_menu.add_command(label="(Fehler: Pfad nicht gefunden)", state=tk.DISABLED)
                 action_added = True
            elif "email_item" in item_tags and os.path.isfile(item_path):
                context_menu.add_command(label="Anzeigen", command=lambda p=item_path: self._display_email_content(p))
                # Prüfen ob ein Konto zum Senden ausgewählt ist im Hauptfenster
                can_send = False
                send_account_info = "(Kein Sendekonto gewählt)"
                if self.selected_account_index is not None:
                     try: # Indexprüfung
                          if 0 <= self.selected_account_index < len(self.accounts):
                              acc = self.accounts[self.selected_account_index]
                              if acc.smtp_server and acc.smtp_port:
                                  can_send = True
                                  send_account_info = f"(via {acc.name})"
                          else:
                               logging.warning(f"Context Menu: Ungültiger selected_account_index ({self.selected_account_index})")
                     except Exception as e:
                          logging.error(f"Context Menu: Fehler beim Kontozugriff: {e}")

                reply_state = tk.NORMAL if can_send else tk.DISABLED
                forward_state = tk.NORMAL if can_send else tk.DISABLED
                context_menu.add_command(label=f"Antworten {send_account_info}", state=reply_state, command=lambda p=item_path: self._open_reply_email_window(filepath=p))
                context_menu.add_command(label=f"Weiterleiten {send_account_info}", state=forward_state, command=lambda p=item_path: self._open_forward_email_window(filepath=p))
                context_menu.add_separator()
                context_menu.add_command(label="Im Explorer öffnen", command=lambda p=item_path: self._open_file_location(p, explorer_window))
                action_added = True
            elif "attachment_item" in item_tags and os.path.isfile(item_path):
                 context_menu.add_command(label="Öffnen", command=lambda p=item_path: self._open_external_file(p, explorer_window))
                 context_menu.add_separator()
                 context_menu.add_command(label="Im Explorer öffnen", command=lambda p=item_path: self._open_file_location(p, explorer_window))
                 action_added = True
            elif "folder_item" in item_tags and os.path.isdir(item_path):
                 context_menu.add_command(label="Im Explorer öffnen", command=lambda p=item_path: self._open_file_location(p, explorer_window))
                 action_added = True

            if action_added:
                 context_menu.tk_popup(event.x_root, event.y_root)

        tree.bind("<Double-1>", open_email_or_attachment_callback)  # Doppelklick
        tree.bind("<Return>", open_email_or_attachment_callback)    # Enter-Taste
        tree.bind("<Button-3>", handle_context_menu_callback)       # Rechtsklick (Windows, Linux)
        tree.bind("<Button-2>", handle_context_menu_callback)       # Rechtsklick (macOS)


    def _open_external_file(self, filepath: str, parent_window: tk.Toplevel):
        """ Versucht, eine Datei mit dem Standard-Systemprogramm zu öffnen. """
        try:
            if sys.platform == "win32":
                os.startfile(filepath)
            elif sys.platform == "darwin": # macOS
                subprocess.run(['open', filepath], check=True)
            else: # Linux und andere Unix-like
                subprocess.run(['xdg-open', filepath], check=True)
            logging.info(f"Versuche externe Datei zu öffnen: {filepath}")
        except FileNotFoundError:
             messagebox.showerror("Fehler", f"Konnte das Öffnen-Programm nicht finden ('open' oder 'xdg-open').", parent=parent_window)
             logging.error(f"Öffnen-Programm nicht gefunden für: {filepath}")
        except subprocess.CalledProcessError as cpe:
             messagebox.showerror("Fehler", f"Fehler beim Öffnen der Datei '{os.path.basename(filepath)}': Das zugehörige Programm meldete einen Fehler.", parent=parent_window)
             logging.error(f"Fehler beim Öffnen von {filepath} mit externem Programm: {cpe}")
        except Exception as e:
             messagebox.showerror("Fehler", f"Datei '{os.path.basename(filepath)}' konnte nicht geöffnet werden: {e}", parent=parent_window)
             logging.error(f"Allgemeiner Fehler beim Öffnen von {filepath}: {e}")

    def _open_file_location(self, filepath: str, parent_window: tk.Toplevel):
        """ Öffnet den Ordner, der die Datei enthält, im System-Explorer. """
        folder_path = os.path.dirname(filepath)
        logging.info(f"Öffne Speicherort: {folder_path}")
        try:
            if sys.platform == "win32":
                # Prüfen ob es ein Verzeichnis oder eine Datei ist
                if os.path.isdir(filepath):
                     subprocess.run(['explorer', filepath], check=True)
                else:
                     # Öffnet Explorer und markiert die Datei
                     subprocess.run(['explorer', '/select,', filepath], check=True)
            elif sys.platform == "darwin": # macOS
                 # 'open -R' enthüllt die Datei im Finder
                 subprocess.run(['open', '-R', filepath], check=True)
            else: # Linux und andere Unix-like
                 # Öffnet den Ordner im Dateimanager
                 subprocess.run(['xdg-open', folder_path], check=True)
        except FileNotFoundError:
             messagebox.showerror("Fehler", f"Konnte den System-Explorer ('explorer', 'open' oder 'xdg-open') nicht finden.", parent=parent_window)
             logging.error(f"System-Explorer nicht gefunden für: {filepath}")
        except subprocess.CalledProcessError as cpe:
             messagebox.showerror("Fehler", f"Fehler beim Öffnen des Speicherorts für '{os.path.basename(filepath)}'.", parent=parent_window)
             logging.error(f"Fehler beim Öffnen des Speicherorts {folder_path}: {cpe}")
        except Exception as e:
             messagebox.showerror("Fehler", f"Speicherort für '{os.path.basename(filepath)}' konnte nicht geöffnet werden: {e}", parent=parent_window)
             logging.error(f"Allgemeiner Fehler beim Öffnen des Speicherorts {folder_path}: {e}")


    def _populate_tree_explorer(self, tree: ttk.Treeview, base_path: str, search_term: str | None) -> int:
        """
        Rekursive Helper Funktion um den TreeView Inhalt des Explorers zu befüllen.
        Durchsucht Verzeichnisse oder filtert .eml Dateien basierend auf dem Suchbegriff.
        Gibt die Anzahl der hinzugefügten Elemente zurück.
        """
        item_count = 0
        # Funktion, die rekursiv aufgerufen wird
        def populate_recursive(parent_node_id, current_path):
            nonlocal item_count
            try:
                # Sortiere Einträge: Ordner zuerst, dann Dateien, alphabetisch
                entries = os.listdir(current_path)
                entries.sort(key=lambda x: (not os.path.isdir(os.path.join(current_path, x)), x.lower()))

                for item_name in entries:
                    item_path = os.path.join(current_path, item_name)
                    node_id = None # ID des erstellten Knotens

                    if os.path.isdir(item_path):
                        # Ordner immer hinzufügen (nicht nach Inhalt filtern beim Browsen)
                        node_id = tree.insert(parent_node_id, 'end', text=item_name, values=('Ordner', '', ''), open=False, tags=("folder_item",))
                        # Rekursiv nur aufrufen, wenn keine Suche aktiv ist ODER der Ordner potenziell Treffer enthält
                        # (Diese Optimierung ist schwierig zuverlässig zu machen, daher hier weggelassen)
                        # Rufe immer rekursiv auf, die Filterung passiert bei den Dateien
                        child_count = populate_recursive(node_id, item_path)
                        # Wenn ein Ordner nach der Rekursion keine Kinder hat (wegen Filterung),
                        # und selbst nicht dem Suchbegriff entspricht (falls Ordnersuche implementiert wäre),
                        # könnte man ihn wieder entfernen.
                        if search_term and child_count == 0:
                             # Prüfen, ob der Ordnername selbst passt (optional)
                             # match_score = fuzz.partial_ratio(search_term.lower(), item_name.lower())
                             # if match_score < 60:
                             #      tree.delete(node_id)
                             #      node_id = None # Damit er nicht gezählt wird
                             pass # Vorerst Ordner immer drin lassen, auch wenn leer nach Suche

                    else: # Es ist eine Datei
                         try:
                             # Dateiinformationen sammeln
                             st = os.stat(item_path)
                             file_size = st.st_size
                             file_mod_time = datetime.datetime.fromtimestamp(st.st_mtime)
                             file_date_str = file_mod_time.strftime('%Y-%m-%d %H:%M:%S')
                             file_type = os.path.splitext(item_name)[1].lower()
                             display_type = file_type[1:].upper() if file_type else "Datei"

                             is_email_file = item_name.lower().endswith(".eml")
                             is_attachment = "anhänge" in item_path.lower().split(os.sep) and not is_email_file

                             # Prüfen, ob die Datei angezeigt werden soll
                             show_item = False
                             item_tag = "file_item"

                             if search_term and fuzz: # Suche ist aktiv
                                if is_email_file:
                                     # Nur .eml Dateien durchsuchen
                                     item_tag = "email_item"
                                     display_type = "E-Mail"
                                     if self._email_matches_search(item_path, search_term):
                                         show_item = True
                                         # Datum aus EML lesen (nur wenn Match, um Performance zu sparen)
                                         eml_date = self._read_eml_date(item_path)
                                         if eml_date: file_date_str = eml_date.strftime('%Y-%m-%d %H:%M:%S %Z').strip()
                                # Andere Dateien werden bei Suche ignoriert
                             else: # Keine Suche aktiv
                                show_item = True # Alle Dateien anzeigen
                                if is_email_file:
                                     item_tag = "email_item"
                                     display_type = "E-Mail"
                                     # Datum aus EML lesen
                                     eml_date = self._read_eml_date(item_path)
                                     if eml_date: file_date_str = eml_date.strftime('%Y-%m-%d %H:%M:%S %Z').strip()
                                elif is_attachment:
                                     item_tag = "attachment_item"
                                     display_type = "Anhang"

                             # Item einfügen, wenn es angezeigt werden soll
                             if show_item:
                                 node_id = tree.insert(parent_node_id, 'end', text=item_name,
                                             values=(display_type, self._format_size(file_size), file_date_str),
                                             tags=(item_tag,))

                         except OSError as e:
                              logging.warning(f"Explorer: Kein Zugriff auf Dateiinformationen für: {item_path}. Fehler: {e}. Übersprungen.")
                         except Exception as e:
                              logging.error(f"Explorer: Fehler bei der Verarbeitung der Datei: {item_path}. Fehler: {e}. Übersprungen.")

                    if node_id: # Wenn ein Knoten (Ordner oder Datei) hinzugefügt wurde
                         item_count += 1

            except OSError as e:
                logging.warning(f"Explorer: Kein Zugriff auf Verzeichnis: {current_path}. Fehler: {e}. Übersprungen.")
            except Exception as e:
                 logging.error(f"Explorer: Fehler beim Auflisten des Verzeichnisses: {current_path}. Fehler: {e}. Übersprungen.")

            return item_count # Anzahl der Kinder dieses Knotens zurückgeben

        # Starte die rekursive Befüllung vom Basispfad aus
        total_items = populate_recursive('', base_path) # '' ist die ID des Wurzelknotens
        return total_items


    def _email_matches_search(self, filepath: str, search_term: str) -> bool:
        """ Prüft, ob der Inhalt einer .eml Datei dem Suchbegriff entspricht (Fuzzy Search). """
        if not fuzz: return False # Fuzzywuzzy nicht verfügbar

        try:
            with open(filepath, 'rb') as infile:
                 # Lese nur Anfang für Performance (z.B. 15 KB)
                 content_sample = infile.read(15 * 1024)
            email_msg = email.message_from_bytes(content_sample)

            # Extrahiere Header
            from_header = self._decode_header(email_msg.get('From', ''))
            to_header = self._decode_header(email_msg.get('To', ''))
            subject_header = self._decode_header(email_msg.get('Subject', ''))

            # Extrahiere Text Body (Sample)
            body_content = ""
            if email_msg.is_multipart():
                for part in email_msg.walk():
                    ctype = part.get_content_type()
                    cdispo = str(part.get('Content-Disposition'))
                    if ctype == 'text/plain' and 'attachment' not in cdispo:
                        try:
                             payload = part.get_payload(decode=True)
                             body_content += payload.decode(part.get_content_charset() or 'utf-8', errors='ignore')
                             if len(body_content) > 2000: break # Limitiere Länge
                        except Exception: pass # Ignoriere Dekodierfehler im Sample
            else:
                if email_msg.get_content_type() == 'text/plain':
                     try:
                          payload = email_msg.get_payload(decode=True)
                          body_content = payload.decode(email_msg.get_content_charset() or 'utf-8', errors='ignore')[:2000]
                     except Exception: pass

            full_searchable_content = f"{from_header} {to_header} {subject_header} {body_content}"

            # Fuzzy Search (partial_ratio ist oft gut für "Begriff in Text")
            match_score = fuzz.partial_ratio(search_term.lower(), full_searchable_content.lower())
            search_threshold = 70 # Schwellenwert anpassen

            if match_score >= search_threshold:
                logging.debug(f"Suche '{search_term}' in '{os.path.basename(filepath)}': Score {match_score} >= {search_threshold}. Match!")
                return True
            # else:
            #      logging.debug(f"Suche '{search_term}' in '{os.path.basename(filepath)}': Score {match_score} < {search_threshold}.")

        except Exception as e:
            logging.error(f"Fehler beim Durchsuchen der E-Mail-Datei {filepath}: {e}")

        return False


    def _read_eml_date(self, filepath: str) -> datetime.datetime | None:
        """ Liest das Datum aus dem Header einer .eml Datei. """
        try:
            with open(filepath, 'rb') as infile:
                 # Lese nur Header (z.B. erste 4KB)
                 headers_part = infile.read(4 * 1024)
            # Finde das Ende des Header-Blocks (erste Leerzeile)
            header_end = headers_part.find(b'\r\n\r\n')
            if header_end != -1:
                 headers_bytes = headers_part[:header_end]
            else: # Keine Leerzeile gefunden, nimm alles
                 headers_bytes = headers_part

            # Parse nur die Header
            parser = email.parser.BytesHeaderParser()
            headers = parser.parsebytes(headers_bytes)
            return self._get_email_date(headers) # Nutze bestehende Datums-Extraktionslogik
        except Exception as e:
            logging.warning(f"Konnte Datum aus EML-Datei {filepath} nicht lesen: {e}")
            return None


    def _decode_header(self, header_value: str | None) -> str:
        """ Dekodiert einen E-Mail Header (Subject, From, To etc.). Gibt leeren String zurück bei None oder Fehler. """
        if not header_value:
            return ""
        try:
            parts = email.header.decode_header(header_value)
            decoded_parts = []
            for part, encoding in parts:
                if isinstance(part, bytes):
                    # Versuche Encoding, falle auf UTF-8 oder 'replace' zurück
                    try:
                         decoded_parts.append(part.decode(encoding or 'utf-8', errors='replace'))
                    except LookupError: # Unbekanntes Encoding
                          decoded_parts.append(part.decode('utf-8', errors='replace'))
                elif isinstance(part, str):
                    decoded_parts.append(part)
                # Ignoriere andere Typen
            return "".join(decoded_parts)
        except Exception as e:
            logging.warning(f"Konnte Header nicht dekodieren: '{header_value[:50]}...'. Fehler: {e}")
            # Gib einen Teil des Originals zurück, wenn Dekodierung fehlschlägt
            return str(header_value)[:100] if isinstance(header_value, str) else "Dekodierfehler"


    def _get_item_path_from_tree(self, tree: ttk.Treeview, item_id, base_dir: str) -> str | None:
        """
        Ermittelt den vollständigen Dateipfad eines Treeview Items, relativ zum base_dir.
        """
        try:
             path_parts = []
             current_id = item_id
             while current_id: # Gehe vom Item nach oben bis zur Wurzel
                 item_text = tree.item(current_id, "text")
                 path_parts.append(item_text)
                 current_id = tree.parent(current_id)

             # Pfadteile umdrehen und mit dem Basisverzeichnis verbinden
             # Wichtig: os.path.join behandelt führende Slashes korrekt
             relative_path = os.path.join(*reversed(path_parts))
             full_path = os.path.join(base_dir, relative_path)
             return os.path.abspath(full_path) # Normiere den Pfad
        except Exception as e:
             logging.error(f"Fehler beim Ermitteln des Pfades für Treeview Item ID {item_id}: {e}")
             return None


    def _format_size(self, num_bytes: int | None) -> str:
        """ Formatiert Bytes in eine lesbare Größe (B, KB, MB, GB). """
        if num_bytes is None: return ""
        try:
            num = int(num_bytes)
            if num < 1024:
                return f"{num} B"
            elif num < 1024**2:
                return f"{num / 1024:.1f} KB"
            elif num < 1024**3:
                return f"{num / 1024**2:.1f} MB"
            else:
                return f"{num / 1024**3:.1f} GB"
        except (ValueError, TypeError):
            logging.warning(f"Ungültiger Wert für _format_size: {num_bytes}")
            return ""


    def _display_email_content(self, filepath: str):
        """
        Zeigt den Inhalt einer E-Mail Datei (.eml) in einem neuen Fenster an.
        Parst die .eml Datei, um Header und Body übersichtlich darzustellen.
        """
        email_view_window = Toplevel(self)
        email_view_window.title(f"E-Mail - {os.path.basename(filepath)}")
        email_view_window.geometry("800x650") # Etwas höher für Buttons
        email_view_window.transient(self)

        # Button Frame oben
        button_frame_top = ttk.Frame(email_view_window)
        button_frame_top.pack(padx=10, pady=5, fill=X)

        # PanedWindow für Header/Body
        view_pane = ttk.PanedWindow(email_view_window, orient=tk.VERTICAL)
        view_pane.pack(fill=BOTH, expand=True, padx=10, pady=5)

        # --- Frame für Header ---
        header_outer_frame = ttk.Frame(view_pane, height=150) # Feste Höhe für Header-Bereich
        view_pane.add(header_outer_frame, weight=0) # Kein Expand für Header

        header_frame = ttk.LabelFrame(header_outer_frame, text="Header")
        header_frame.pack(fill=BOTH, expand=True)

        header_text = Text(header_frame, wrap="none", height=8, font=("Courier New", 9), background="#f0f0f0")
        header_vsb = ttk.Scrollbar(header_frame, orient=tk.VERTICAL, command=header_text.yview)
        header_hsb = ttk.Scrollbar(header_frame, orient=tk.HORIZONTAL, command=header_text.xview)
        header_text.config(yscrollcommand=header_vsb.set, xscrollcommand=header_hsb.set)

        header_vsb.pack(side=RIGHT, fill=Y)
        # KORREKTUR: Hier wird BOTTOM verwendet, das jetzt importiert ist
        header_hsb.pack(side=BOTTOM, fill=X)
        header_text.pack(fill=BOTH, expand=True, padx=5, pady=5)
        header_text.config(state='disabled')

        # --- Frame für Body ---
        body_outer_frame = ttk.Frame(view_pane)
        view_pane.add(body_outer_frame, weight=1) # Body soll expandieren

        body_frame = ttk.LabelFrame(body_outer_frame, text="Nachrichtentext")
        body_frame.pack(fill=BOTH, expand=True)

        body_text = Text(body_frame, wrap="word", font=("Segoe UI", 10), undo=True)
        body_vsb = ttk.Scrollbar(body_frame, orient=tk.VERTICAL, command=body_text.yview)
        body_text.config(yscrollcommand=body_vsb.set)
        body_vsb.pack(side=RIGHT, fill=Y)
        body_text.pack(fill=BOTH, expand=True, padx=5, pady=5)
        # Body initial editierbar machen, damit man Text kopieren kann
        body_text.config(state='normal')
        body_text.bind("<Key>", lambda e: "break") # Verhindert Tippen, aber erlaubt Kopieren

        # --- E-Mail Laden und Anzeigen ---
        email_msg = None # Variable für die geparste Nachricht
        try:
            with open(filepath, 'rb') as infile:
                email_msg = email.message_from_bytes(infile.read())

            # Header extrahieren und formatieren
            header_lines = []
            # Wichtige Header zuerst und dekodiert
            important_headers = ['From', 'To', 'Cc', 'Subject', 'Date']
            for key in important_headers:
                 value = email_msg.get(key)
                 if value:
                     header_lines.append(f"{key+':':<10} {self._decode_header(value)}")

            # Trenner
            header_lines.append("-" * 20)

            # Restliche Header (limitiert)
            other_headers_count = 0
            max_other_headers = 10
            for key, value in email_msg.items():
                 if key not in important_headers and other_headers_count < max_other_headers:
                     # Kurze Werte direkt, lange kürzen
                     display_value = value
                     if len(display_value) > 100: display_value = display_value[:97] + "..."
                     header_lines.append(f"{key+':':<10} {display_value}")
                     other_headers_count += 1
                 elif other_headers_count >= max_other_headers:
                      header_lines.append("...")
                      break

            header_text.config(state='normal')
            header_text.delete("1.0", END)
            header_text.insert(END, "\n".join(header_lines))
            header_text.config(state='disabled')

            # Body extrahieren (versuche Text/Plain zuerst, dann Text/HTML als Fallback)
            body_plain = ""
            body_html = ""
            for part in email_msg.walk():
                ctype = part.get_content_type()
                cdispo = str(part.get('Content-Disposition'))
                is_attachment = 'attachment' in cdispo.lower() or (part.get_filename() and 'inline' not in cdispo.lower())

                if not is_attachment and part.get_content_maintype() == 'text':
                     charset = part.get_content_charset() or 'utf-8'
                     payload = part.get_payload(decode=True)
                     if payload:
                          try:
                               decoded_payload = payload.decode(charset, errors='replace')
                               if ctype == 'text/plain' and not body_plain: # Nimm den ersten Plaintext
                                    body_plain = decoded_payload
                               elif ctype == 'text/html' and not body_html: # Nimm den ersten HTML
                                    body_html = decoded_payload
                          except Exception as decode_err:
                               logging.warning(f"Fehler beim Dekodieren von '{ctype}' Payload in E-Mail Ansicht: {decode_err}")


            # Wähle Plaintext bevorzugt, sonst HTML
            display_content = body_plain if body_plain else body_html
            if not display_content:
                 # Fallback, wenn kein Textteil gefunden wurde (z.B. nur Anhang)
                 if email_msg.is_multipart():
                      display_content = "<Kein lesbarer Nachrichtentext gefunden (möglicherweise nur Anhänge oder ungewöhnliches Format)>"
                 else: # Wenn Singlepart, versuche es direkt zu dekodieren
                      try:
                          payload = email_msg.get_payload(decode=True)
                          display_content = payload.decode(email_msg.get_content_charset() or 'utf-8', errors='replace')
                      except Exception:
                           display_content = "<Inhalt konnte nicht dekodiert werden>"


            body_text.config(state='normal')
            body_text.delete("1.0", END)
            body_text.insert(END, display_content)
            body_text.config(state='normal') # Lesbar/Kopierbar lassen
            body_text.bind("<Key>", lambda e: "break") # Tippen verhindern

        except FileNotFoundError:
             messagebox.showerror("Fehler", f"E-Mail Datei nicht gefunden: {filepath}", parent=email_view_window)
             email_view_window.destroy()
             return
        except Exception as e:
            logging.error(f"Fehler beim Lesen oder Parsen der E-Mail Datei '{filepath}': {e}\n{traceback.format_exc()}")
            messagebox.showerror("Fehler", f"Fehler beim Lesen der E-Mail Datei:\n{e}", parent=email_view_window)
            # Zeige rohen Inhalt als Fallback?
            try:
                 with open(filepath, 'r', encoding='utf-8', errors='ignore') as infile_raw:
                      raw_content = infile_raw.read()
                 body_text.config(state='normal')
                 body_text.delete("1.0", END)
                 body_text.insert(END, f"--- Fehler beim Parsen, zeige Rohinhalt: ---\n\n{raw_content}")
                 body_text.config(state='normal') # Lesbar/Kopierbar lassen
                 body_text.bind("<Key>", lambda e: "break") # Tippen verhindern
            except Exception as fallback_e:
                 logging.error(f"Fallback zum Anzeigen des Rohinhalts fehlgeschlagen: {fallback_e}")


        # --- Buttons oben hinzufügen (Reply, Forward) ---
        can_send = False
        send_account_info = "(Kein Sendekonto gewählt)"
        if self.selected_account_index is not None:
             try: # Zusätzliche Prüfung
                 if 0 <= self.selected_account_index < len(self.accounts):
                     acc = self.accounts[self.selected_account_index]
                     if acc.smtp_server and acc.smtp_port:
                          can_send = True
                          send_account_info = f"(via {acc.name})"
                 else:
                     logging.warning(f"_display_email_content: Ungültiger selected_account_index ({self.selected_account_index})")
             except Exception as idx_err:
                  logging.error(f"Fehler beim Zugriff auf Konto in _display_email_content: {idx_err}")


        reply_state = tk.NORMAL if can_send else tk.DISABLED
        forward_state = tk.NORMAL if can_send else tk.DISABLED

        # Verwende die bereits geparste `email_msg` für Reply/Forward (nur wenn sie existiert)
        reply_command = lambda: None # Default No-Op
        forward_command = lambda: None # Default No-Op
        if email_msg:
            reply_command=lambda msg=email_msg: self._open_compose_email_window(mode='reply', original_msg=msg)
            forward_command=lambda msg=email_msg: self._open_compose_email_window(mode='forward', original_msg=msg)

        reply_button = ttk.Button(button_frame_top, text=f"Antworten {send_account_info}", state=reply_state,
                                  command=reply_command)
        reply_button.pack(side=LEFT, padx=5)

        forward_button = ttk.Button(button_frame_top, text=f"Weiterleiten {send_account_info}", state=forward_state,
                                    command=forward_command)
        forward_button.pack(side=LEFT, padx=5)

        # Schließen Button
        close_button = ttk.Button(button_frame_top, text="Schließen", command=email_view_window.destroy)
        close_button.pack(side=RIGHT, padx=5)


    # --- Erweiterungen: E-Mail Verwaltung (Senden) ---

    def _open_compose_email_window(self, mode='compose', filepath=None, original_msg: email.message.Message = None):
        """
        Öffnet ein Fenster zum Verfassen ('compose'), Beantworten ('reply'),
        oder Weiterleiten ('forward') einer E-Mail.

        Args:
            mode (str): 'compose', 'reply', oder 'forward'.
            filepath (str, optional): Der Pfad zur .eml-Datei für Reply/Forward (wenn original_msg nicht übergeben).
            original_msg (email.message.Message, optional): Bereits geparste Originalnachricht (bevorzugt).
        """
        logging.info(f"Öffne E-Mail Fenster: Modus='{mode}'")

        # Prüfen ob Absenderkonto ausgewählt und konfiguriert ist
        sender_account = None
        if self.selected_account_index is not None:
             try:
                  # Sicherstellen, dass der Index gültig ist
                  if 0 <= self.selected_account_index < len(self.accounts):
                       sender_account = self.accounts[self.selected_account_index]
                       if not sender_account.smtp_server or not sender_account.smtp_port:
                            messagebox.showerror("Fehler", f"Für das ausgewählte Konto '{sender_account.name}' sind keine SMTP-Serverdaten konfiguriert. Senden nicht möglich.", parent=self)
                            return
                  else:
                      logging.error(f"Fehler in _open_compose_email_window: Ungültiger selected_account_index ({self.selected_account_index}) bei {len(self.accounts)} Konten.")
                      messagebox.showerror("Fehler", "Ausgewähltes Absenderkonto ist ungültig (Index-Problem).", parent=self)
                      # Auswahl zurücksetzen und UI neu laden?
                      if self.account_listbox: # Nur wenn Listbox existiert
                          self.account_listbox.selection_clear(0, END)
                          self._on_account_select()
                      return
             except IndexError: # Sollte durch obige Prüfung nicht mehr passieren, aber sicher ist sicher
                  messagebox.showerror("Fehler", "Ausgewähltes Absenderkonto ist ungültig (IndexError).", parent=self)
                  return
             except Exception as e: # Andere unerwartete Fehler beim Kontozugriff
                  logging.error(f"Unerwarteter Fehler beim Zugriff auf Konto für Senden: {e}", exc_info=True)
                  messagebox.showerror("Fehler", f"Fehler beim Zugriff auf Kontodaten: {e}", parent=self)
                  return
        else:
              messagebox.showerror("Fehler", "Bitte wählen Sie zuerst ein Absenderkonto im Hauptfenster aus.", parent=self)
              return

        # Jetzt sollte sender_account sicher gesetzt sein
        if not sender_account:
            logging.critical("Inkonsistenter Zustand: sender_account nicht gesetzt trotz Prüfung in _open_compose_email_window.")
            messagebox.showerror("Interner Fehler", "Absenderkonto konnte nicht bestimmt werden.", parent=self)
            return


        # --- Fenster erstellen ---
        compose_window = Toplevel(self)
        compose_window.title(f"E-Mail {mode.capitalize()}") # Titel wird später ggf. angepasst
        compose_window.geometry("750x650")
        compose_window.transient(self)
        compose_window.grab_set()

        compose_frame = ttk.Frame(compose_window, padding="10")
        compose_frame.pack(fill=BOTH, expand=True)
        compose_frame.grid_columnconfigure(1, weight=1) # Spalte der Eingabefelder soll sich ausdehnen

        row_num = 0

        # Absender (nur zur Info)
        ttk.Label(compose_frame, text="Von:").grid(row=row_num, column=0, padx=5, pady=2, sticky="e")
        ttk.Label(compose_frame, text=sender_account.email_address).grid(row=row_num, column=1, padx=5, pady=2, sticky="w")
        row_num += 1

        # Empfänger (An, CC, BCC)
        ttk.Label(compose_frame, text="An:").grid(row=row_num, column=0, padx=5, pady=2, sticky="e")
        to_entry = ttk.Entry(compose_frame)
        to_entry.grid(row=row_num, column=1, padx=5, pady=2, sticky="ew")
        row_num += 1

        ttk.Label(compose_frame, text="Cc:").grid(row=row_num, column=0, padx=5, pady=2, sticky="e")
        cc_entry = ttk.Entry(compose_frame)
        cc_entry.grid(row=row_num, column=1, padx=5, pady=2, sticky="ew")
        row_num += 1

        ttk.Label(compose_frame, text="Bcc:").grid(row=row_num, column=0, padx=5, pady=2, sticky="e")
        bcc_entry = ttk.Entry(compose_frame)
        bcc_entry.grid(row=row_num, column=1, padx=5, pady=2, sticky="ew")
        row_num += 1

        # Betreff
        ttk.Label(compose_frame, text="Betreff:").grid(row=row_num, column=0, padx=5, pady=2, sticky="e")
        subject_entry = ttk.Entry(compose_frame)
        subject_entry.grid(row=row_num, column=1, padx=5, pady=2, sticky="ew")
        row_num += 1

        # Nachrichtentext
        ttk.Label(compose_frame, text="Nachricht:").grid(row=row_num, column=0, padx=5, pady=5, sticky="ne")
        message_frame = ttk.Frame(compose_frame) # Frame für Text und Scrollbar
        message_frame.grid(row=row_num, column=1, padx=5, pady=5, sticky="nsew")
        message_frame.grid_rowconfigure(0, weight=1)
        message_frame.grid_columnconfigure(0, weight=1)
        compose_frame.grid_rowconfigure(row_num, weight=1) # Zeile des Textfelds soll sich ausdehnen

        message_text = Text(message_frame, wrap="word", height=15, undo=True)
        message_vsb = ttk.Scrollbar(message_frame, orient=tk.VERTICAL, command=message_text.yview)
        message_text.config(yscrollcommand=message_vsb.set)
        message_vsb.grid(row=0, column=1, sticky="ns")
        message_text.grid(row=0, column=0, sticky="nsew")
        row_num += 1

        # Anhänge
        attachments = [] # Liste speichert Tupel (display_name, filepath)
        attachment_frame = ttk.Frame(compose_frame)
        attachment_frame.grid(row=row_num, column=1, padx=5, pady=5, sticky="w")
        # Button zum Hinzufügen von Anhängen (vor dem Label platzieren)
        attach_button = ttk.Button(attachment_frame, text="Anhänge hinzufügen...", command=lambda: attach_file_callback())
        attach_button.pack(side=LEFT, padx=(0, 10))
        # Label zur Anzeige der Anhänge
        attachment_label = ttk.Label(attachment_frame, text="Keine Anhänge")
        attachment_label.pack(side=LEFT)
        row_num += 1

        # --- Vorbelegung für Reply/Forward ---
        original_subject = ""
        if mode in ('reply', 'forward'):
            if not original_msg and filepath: # Lade Nachricht, wenn nicht übergeben
                 logging.debug(f"Lade Originalnachricht für '{mode}' aus: {filepath}")
                 try:
                     with open(filepath, 'rb') as infile:
                         original_msg = email.message_from_bytes(infile.read())
                 except Exception as e:
                     logging.error(f"Fehler beim Laden der Original-E-Mail für '{mode}' aus {filepath}: {e}")
                     messagebox.showerror("Fehler", f"Konnte die Original-E-Mail nicht laden:\n{e}", parent=compose_window)
                     compose_window.destroy()
                     return

            if original_msg:
                 try:
                    logging.debug("Verarbeite Originalnachricht für Reply/Forward...")
                    # Extrahiere Daten aus Originalnachricht
                    original_from = self._decode_header(original_msg.get('From', ''))
                    original_to_header = self._decode_header(original_msg.get('To', ''))
                    original_cc_header = self._decode_header(original_msg.get('Cc', ''))
                    original_reply_to = self._decode_header(original_msg.get('Reply-To', '')) # Wichtig für Antworten
                    original_date_dt = self._get_email_date(original_msg)
                    original_date_str = original_date_dt.strftime('%a, %d %b %Y %H:%M:%S %z') if original_date_dt else "Unbekanntes Datum" # RFC Format
                    original_subject = self._decode_header(original_msg.get('Subject', ''))

                    # Body für Zitat extrahieren (Plaintext bevorzugt)
                    original_body_plain = ""
                    for part in original_msg.walk():
                         ctype = part.get_content_type()
                         cdispo = str(part.get('Content-Disposition'))
                         if ctype == 'text/plain' and 'attachment' not in cdispo.lower():
                             try:
                                 original_body_plain = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='ignore')
                                 break # Nimm den ersten Plaintext Teil
                             except Exception as e:
                                  logging.warning(f"Konnte text/plain Teil für Zitat nicht dekodieren: {e}")

                    # Zitat formatieren
                    quote_intro = f"Am {original_date_str} schrieb {original_from}:"
                    quoted_body = "\n".join([f"> {line}" for line in original_body_plain.splitlines()])
                    full_quote = f"\n\n{'--'*5} Originalnachricht {'--'*5}\n{quote_intro}\n{quoted_body}\n{'--'*18}\n"

                    # Felder vorbelegen
                    if mode == 'reply':
                        compose_window.title(f"Antwort auf: {original_subject[:40]}{'...' if len(original_subject)>40 else ''}")
                        # Empfänger setzen: Reply-To verwenden, wenn vorhanden, sonst From
                        reply_to_addr = ""
                        if original_reply_to:
                             reply_to_addr = parseaddr(original_reply_to)[1] # Nur Adresse
                        if not reply_to_addr and original_from:
                             reply_to_addr = parseaddr(original_from)[1]

                        to_entry.insert(0, reply_to_addr)

                        # Betreff setzen (mit "Re:")
                        prefix = "Re: "
                        if not original_subject.lower().startswith(prefix.lower()):
                            subject_entry.insert(0, prefix + original_subject)
                        else:
                            subject_entry.insert(0, original_subject)

                        # Zitierten Text einfügen
                        message_text.insert('1.0', full_quote) # Am Anfang einfügen
                        message_text.mark_set("insert", "1.0")
                        message_text.focus_set()

                    elif mode == 'forward':
                        compose_window.title(f"Weiterleiten: {original_subject[:40]}{'...' if len(original_subject)>40 else ''}")
                        # Empfänger bleibt leer

                        # Betreff setzen (mit "Fwd:")
                        prefix = "Fwd: "
                        # Prüfe auch auf deutsches "WG:"
                        if not (original_subject.lower().startswith(prefix.lower()) or original_subject.lower().startswith("wg:")):
                            subject_entry.insert(0, prefix + original_subject)
                        else:
                            subject_entry.insert(0, original_subject)

                        # Zitierten Text einfügen
                        message_text.insert('1.0', full_quote)
                        message_text.mark_set("insert", "1.0")
                        to_entry.focus_set()

                        # TODO: Option zum Weiterleiten von Anhängen?
                        # original_attachments = self._extract_attachments_for_forwarding(original_msg)
                        # attachments.extend(original_attachments)
                        # update_attachment_label()

                 except Exception as e:
                     logging.error(f"Fehler beim Vorbereiten der E-Mail für '{mode}': {e}\n{traceback.format_exc()}")
                     messagebox.showerror("Fehler", f"Fehler beim Vorbereiten der {mode}-Mail:\n{e}", parent=compose_window)


        # --- Funktionen für Buttons ---
        def update_attachment_label():
             if not attachments:
                 attachment_label.config(text="Keine Anhänge")
             else:
                 display_names = [name for name, path in attachments]
                 total_size = sum(os.path.getsize(path) for name, path in attachments if os.path.exists(path))
                 label_text = f"{len(display_names)} Anhang/Anhänge ({self._format_size(total_size)}): {', '.join(display_names)}"
                 # Kürzen für Anzeige
                 if len(label_text) > 100: label_text = label_text[:97] + "..."
                 attachment_label.config(text=label_text)
                 # Tooltip mit voller Liste? (Komplizierter)

        def attach_file_callback():
            filepaths = filedialog.askopenfilenames(title="Datei(en) anhängen", parent=compose_window)
            if filepaths:
                added_count = 0
                skipped_count = 0
                for filepath in filepaths:
                     # Prüfen ob Datei bereits angehängt ist (basierend auf Pfad)
                     if filepath not in [p for n, p in attachments]:
                         if os.path.exists(filepath):
                             display_name = os.path.basename(filepath)
                             attachments.append((display_name, filepath))
                             logging.info(f"Datei '{display_name}' zum Anhängen vorgemerkt.")
                             added_count += 1
                         else:
                              logging.warning(f"Ausgewählte Datei nicht gefunden: {filepath}")
                              skipped_count += 1
                     else:
                          logging.warning(f"Datei '{os.path.basename(filepath)}' ist bereits angehängt.")
                          skipped_count += 1

                if added_count > 0:
                     update_attachment_label()
                if skipped_count > 0:
                     messagebox.showwarning("Hinweis", f"{skipped_count} Datei(en) wurden übersprungen (nicht gefunden oder bereits angehängt).", parent=compose_window)


        def send_email_thread_worker():
             """ Führt den Sendevorgang aus. Gibt True bei Erfolg, False bei Fehler zurück. """
             recipient_to = to_entry.get().strip()
             recipient_cc = cc_entry.get().strip()
             recipient_bcc = bcc_entry.get().strip()
             subject = subject_entry.get() # Kein strip, Betreff kann Leerzeichen haben
             message_body = message_text.get("1.0", END).strip()

             # --- Validierung ---
             if not recipient_to and not recipient_cc and not recipient_bcc:
                  messagebox.showerror("Fehler", "Bitte geben Sie mindestens einen Empfänger (An, Cc oder Bcc) an.", parent=compose_window)
                  return False
             # Überprüfe E-Mail Format grob (optional, aber hilfreich)
             all_recipient_emails = []
             for r_field in [recipient_to, recipient_cc, recipient_bcc]:
                  if r_field:
                       emails_in_field = [r.strip() for r in r_field.replace(';', ',').split(',') if r.strip()]
                       for email_addr in emails_in_field:
                            if '@' not in email_addr or '.' not in email_addr.split('@')[-1]:
                                 messagebox.showerror("Fehler", f"Ungültige E-Mail Adresse gefunden: '{email_addr}'.", parent=compose_window)
                                 return False
                            all_recipient_emails.append(email_addr)

             if not all_recipient_emails: # Sollte nie passieren nach erster Prüfung
                  messagebox.showerror("Fehler", "Keine gültigen Empfängeradressen gefunden.", parent=compose_window)
                  return False

             if not subject and not messagebox.askyesno("Warnung", "Der Betreff ist leer. Trotzdem senden?", parent=compose_window):
                  return False # Abbruch durch Benutzer

             # --- E-Mail zusammenbauen ---
             try:
                 msg = MIMEMultipart()
                 # Absender formatieren (Name <adresse@domain.com>)
                 msg['From'] = formataddr((sender_account.name, sender_account.email_address))
                 msg['To'] = recipient_to
                 if recipient_cc: msg['Cc'] = recipient_cc
                 # BCC wird NICHT als Header hinzugefügt!
                 msg['Subject'] = subject
                 msg['Date'] = formatdate(localtime=True)
                 msg['Message-ID'] = make_msgid()
                 msg.preamble = 'This is a multi-part message in MIME format.\n' # Standard Preambel

                 # Nachrichtentext hinzufügen (als UTF-8)
                 msg.attach(MIMEText(message_body, 'plain', 'utf-8'))

                 # Anhänge hinzufügen
                 for display_name, filepath in attachments:
                     if not os.path.exists(filepath):
                          logging.warning(f"Anhang nicht gefunden beim Senden: {filepath}. Wird übersprungen.")
                          continue # Überspringe nicht gefundene Anhänge

                     # Content-Type erraten (optional, aber empfohlen)
                     # KORREKTUR: Verwende mimetypes.guess_type statt email.mime.guess_type
                     ctype, encoding = mimetypes.guess_type(filepath)
                     if ctype is None or encoding is not None:
                          # Kein Typ gefunden oder es ist ein Texttyp (wie .txt), behandle als 'octet-stream'
                          ctype = 'application/octet-stream'
                     maintype, subtype = ctype.split('/', 1)

                     try:
                          with open(filepath, "rb") as attachment_file:
                               part = MIMEBase(maintype, subtype)
                               part.set_payload(attachment_file.read())
                               encoders.encode_base64(part)
                               # Dateinamen korrekt kodieren (RFC 2231 für Sonderzeichen)
                               part.add_header('Content-Disposition', 'attachment', filename=display_name)
                               msg.attach(part)
                               logging.debug(f"Anhang '{display_name}' hinzugefügt (Typ: {ctype}).")
                     except FileNotFoundError: # Doppelte Prüfung, falls Datei inzwischen gelöscht wurde
                          logging.error(f"Anhangdatei nicht gefunden beim Lesen: {filepath}. Wird übersprungen.")
                     except Exception as attach_err:
                          logging.error(f"Fehler beim Lesen oder Anhängen der Datei {filepath}: {attach_err}")
                          messagebox.showerror("Anhangfehler", f"Fehler beim Verarbeiten des Anhangs:\n{display_name}\n\n{attach_err}", parent=compose_window)
                          return False # Senden abbrechen bei Anhangfehler? Oder trotzdem versuchen? -> Abbrechen ist sicherer.


                 # --- E-Mail senden via SMTP ---
                 smtp_host = sender_account.smtp_server
                 smtp_port = sender_account.smtp_port
                 smtp_user = sender_account.email_address
                 smtp_pass = sender_account.password
                 timeout_smtp = 30 # Sekunden

                 logging.info(f"Versende E-Mail an {all_recipient_emails} von {smtp_user} via {smtp_host}:{smtp_port}")
                 smtp_conn = None

                 # Verbindung mit SSL/TLS je nach Port aufbauen
                 if smtp_port == 465: # Implizites SSL
                      logging.debug("Verwende SMTP_SSL für Port 465.")
                      smtp_conn = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=timeout_smtp)
                 else: # Standard/Explizites TLS (STARTTLS)
                      logging.debug(f"Verwende SMTP für Port {smtp_port} (versuche STARTTLS).")
                      smtp_conn = smtplib.SMTP(smtp_host, smtp_port, timeout=timeout_smtp)
                      # EHLO senden (wichtig vor STARTTLS)
                      smtp_conn.ehlo()
                      # Versuche STARTTLS, wenn vom Server angeboten
                      if smtp_conn.has_extn('starttls'):
                           logging.debug("Server unterstützt STARTTLS. Starte TLS...")
                           try:
                               smtp_conn.starttls()
                               smtp_conn.ehlo() # Erneut EHLO nach TLS
                               logging.debug("STARTTLS erfolgreich.")
                           except smtplib.SMTPException as tls_err:
                                logging.warning(f"STARTTLS fehlgeschlagen (Server: {smtp_host}:{smtp_port}): {tls_err}. Versuche unverschlüsselt fortzufahren (nicht empfohlen).")
                                # Hier könnte man abbrechen oder weitermachen (Sicherheitsrisiko)
                                # messagebox.showwarning("Sicherheitswarnung", "STARTTLS fehlgeschlagen. E-Mail wird möglicherweise unverschlüsselt gesendet.", parent=compose_window)
                      else:
                           logging.debug("Server unterstützt STARTTLS nicht auf diesem Port.")

                 # Login und Senden
                 with smtp_conn:
                     try:
                          logging.debug("Versuche SMTP Login...")
                          smtp_conn.login(smtp_user, smtp_pass)
                          logging.info("SMTP Login erfolgreich.")
                     except smtplib.SMTPAuthenticationError as auth_err:
                          logging.error(f"SMTP Authentifizierung fehlgeschlagen: {auth_err}")
                          raise ValueError(f"Anmeldung am SMTP Server fehlgeschlagen. Prüfen Sie E-Mail/Passwort.\nServermeldung: {auth_err}") from auth_err
                     except smtplib.SMTPException as login_err:
                          logging.error(f"SMTP Login Fehler: {login_err}")
                          raise ValueError(f"Allgemeiner Fehler beim SMTP Login: {login_err}") from login_err

                     logging.debug(f"Sende E-Mail von {smtp_user} an {all_recipient_emails}...")
                     # sendmail braucht Liste der Empfänger (To, Cc, Bcc)
                     smtp_conn.sendmail(smtp_user, all_recipient_emails, msg.as_string())
                     logging.info(f"E-Mail erfolgreich an SMTP Server {smtp_host} übergeben.")

                 return True # Erfolg

             # --- Fehlerbehandlung für SMTP ---
             except (ValueError, smtplib.SMTPRecipientsRefused, smtplib.SMTPSenderRefused, smtplib.SMTPDataError) as e:
                  # Dies sind Fehler, die der Benutzer beheben kann oder spezifische SMTP Probleme
                  logging.error(f"Fehler beim Senden der E-Mail (Benutzer/SMTP-Protokoll): {e}")
                  messagebox.showerror("Fehler beim Senden", str(e), parent=compose_window)
                  return False
             except smtplib.SMTPConnectError as conn_err:
                  logging.error(f"SMTP Verbindungsfehler zu {smtp_host}:{smtp_port}: {conn_err}")
                  messagebox.showerror("Verbindungsfehler", f"Konnte keine Verbindung zum SMTP Server {smtp_host} herstellen:\n{conn_err}", parent=compose_window)
                  return False
             except TimeoutError: # Socket Timeout
                  logging.error(f"SMTP Timeout bei Verbindung/Senden zu {smtp_host}:{smtp_port}")
                  messagebox.showerror("Timeout", f"Zeitüberschreitung bei der Kommunikation mit dem SMTP Server {smtp_host}.", parent=compose_window)
                  return False
             except OSError as os_err: # Z.B. Netzwerk nicht erreichbar
                   logging.error(f"Netzwerkfehler beim Senden: {os_err}")
                   messagebox.showerror("Netzwerkfehler", f"Netzwerkfehler beim Senden der E-Mail:\n{os_err}", parent=compose_window)
                   return False
             except Exception as e:
                 # Alle anderen, unerwarteten Fehler
                 logging.critical(f"Kritischer Fehler beim Senden der E-Mail: {e}\n{traceback.format_exc()}")
                 messagebox.showerror("Schwerwiegender Fehler", f"Ein unerwarteter Fehler ist beim Senden aufgetreten:\n{e}", parent=compose_window)
                 return False

        # --- Threading Logik für den Senden Button ---
        def start_send_thread():
             # Deaktiviere Buttons
             send_button.config(state=tk.DISABLED)
             attach_button.config(state=tk.DISABLED)
             cancel_button.config(state=tk.DISABLED)
             status_label_compose.config(text="Sende E-Mail...")
             compose_window.update_idletasks()

             # Starte den Worker Thread
             thread = threading.Thread(target=send_email_thread_callback, daemon=True)
             thread.start()

        def send_email_thread_callback():
             # Führe die eigentliche Sendelogik aus und hole Ergebnis
             success = send_email_thread_worker()
             # Schedule GUI Update im Main Thread
             compose_window.after(0, handle_send_result, success)

        def handle_send_result(success):
             # Aktiviere Buttons wieder (nur wenn Fenster noch existiert)
             try:
                  if compose_window.winfo_exists():
                      send_button.config(state=tk.NORMAL)
                      attach_button.config(state=tk.NORMAL)
                      cancel_button.config(state=tk.NORMAL)
                  else: return # Fenster wurde bereits geschlossen
             except tk.TclError: return # Fenster existiert nicht mehr

             if success:
                 status_label_compose.config(text="E-Mail erfolgreich versendet!")
                 messagebox.showinfo("Erfolg", "E-Mail erfolgreich versendet!", parent=self) # Info im Hauptfenster
                 compose_window.destroy()
             else:
                 # Fehlermeldung wurde bereits angezeigt
                 status_label_compose.config(text="Fehler beim Senden. Bitte Details prüfen.")
                 # Fenster offen lassen, damit Benutzer korrigieren kann


        # --- Buttons und Statusleiste im Compose-Fenster ---
        button_frame = ttk.Frame(compose_frame)
        button_frame.grid(row=row_num, column=0, columnspan=2, pady=10, sticky="ew")

        # Send Button (startet den Thread)
        send_button = ttk.Button(button_frame, text="Senden", command=start_send_thread)
        send_button.pack(side=RIGHT, padx=5)

        cancel_button = ttk.Button(button_frame, text="Abbrechen", command=compose_window.destroy)
        cancel_button.pack(side=RIGHT, padx=5)

        # Spacer, um Buttons nach rechts zu schieben
        # button_frame.columnconfigure(0, weight=1) # Nicht nötig bei pack

        status_label_compose = ttk.Label(compose_frame, text="")
        status_label_compose.grid(row=row_num + 1, column=0, columnspan=2, sticky="w", padx=5)


    def _open_reply_email_window(self, filepath=None, original_msg=None):
        """ Öffnet das Fenster zum Beantworten einer E-Mail. """
        if not filepath and not original_msg: return
        self._open_compose_email_window(mode='reply', filepath=filepath, original_msg=original_msg)

    def _open_forward_email_window(self, filepath=None, original_msg=None):
        """ Öffnet das Fenster zum Weiterleiten einer E-Mail. """
        if not filepath and not original_msg: return
        self._open_compose_email_window(mode='forward', filepath=filepath, original_msg=original_msg)


    # --- Erweiterungen: CLI Steuerung ---

    def cli_archive_emails(self, account_name: str, folders: list[str] | None, age_days: int):
        """
        CLI Funktion zur automatischen Speicherung von E-Mails für ein bestimmtes Konto.
        Keine GUI Interaktion hier. Nur Logging und Konsolenausgabe.
        Speichert E-Mails älter als age_days in 'archiv', neuere in 'emails'.

        Args:
            account_name (str): Name des zu verwendenden Kontos (case-insensitive).
            folders (list[str] | None): Liste der zu prüfenden Ordner. Wenn None, wird ['inbox'] verwendet.
            age_days (int): Mindestalter der E-Mails in Tagen für die Archivierung.
        """
        start_time = datetime.datetime.now()
        logging.info(f"CLI Verarbeitung gestartet für Konto: '{account_name}', Ordner: {folders if folders else '[default: inbox]'}, Archiv > {age_days} Tage.")
        print(f"\n--- Starte CLI Verarbeitung für Konto: '{account_name}' ---")

        # Finde das Konto
        account = None
        for acc in self.accounts:
            if acc.name.lower() == account_name.lower():
                account = acc
                break

        if not account:
            logging.error(f"CLI Fehler: Konto mit Namen '{account_name}' nicht gefunden.")
            print(f"\nFEHLER: Konto mit Namen '{account_name}' nicht gefunden.")
            if self.accounts:
                print("Verfügbare Konten:")
                for acc_avail in self.accounts: print(f"- {acc_avail.name}")
            else:
                print("Keine Konten konfiguriert.")
            print("--------------------------------------------------")
            return

        print(f"Konto gefunden: {account.name} ({account.email_address}, {account.protocol.upper()})")

        # --- Ordner bestimmen ---
        folders_to_check = []
        if account.protocol == 'imap':
            if folders:
                 folders_to_check = folders
                 print(f"Zu prüfende IMAP Ordner: {', '.join(folders_to_check)}")
            else:
                 folders_to_check = ['INBOX'] # Sicherer Standard
                 print("Keine Ordner angegeben, prüfe Standard IMAP Ordner: INBOX")

        elif account.protocol == 'pop3':
              folders_to_check = ['inbox'] # POP3 hat nur Inbox (Name ist irrelevant)
              if folders and folders != ['inbox']: # Prüfe ob explizit 'inbox' angegeben wurde
                   print("WARNUNG: Ordner für POP3 ignoriert, nur Inbox wird geprüft.")
              print("Prüfe POP3 Ordner: inbox")

        if not folders_to_check:
             print("Keine Ordner zum Prüfen gefunden oder bestimmt.")
             print("--------------------------------------------------")
             return


        # --- E-Mail IDs abrufen ---
        print("\nSchritt 1: Rufe E-Mail IDs ab...")
        all_email_ids_with_folder = []
        total_ids_found = 0
        fetch_errors = 0
        mail_connection_cli = None # Verbindung für ID-Abruf (IMAP)

        try:
            # Verbindung nur für IMAP aufbauen und wiederverwenden
            if account.protocol == 'imap':
                 try:
                     print(f"- Verbinde mit IMAP Server {account.server}...", end='', flush=True)
                     mail_connection_cli = imaplib.IMAP4_SSL(account.server, account.port, timeout=20)
                     mail_connection_cli.login(account.email_address, account.password)
                     print(" Verbunden.")
                     logging.info(f"CLI: IMAP Verbindung für ID-Abruf für {account.email_address} hergestellt.")
                 except Exception as conn_err:
                     logging.error(f"CLI: IMAP Verbindungsfehler für {account.email_address}: {conn_err}")
                     print(f"\nFEHLER: Konnte keine Verbindung zum IMAP Server herstellen: {conn_err}")
                     return # Abbruch

            # IDs für jeden Ordner abrufen
            for folder in folders_to_check:
                print(f"- Prüfe Ordner '{folder}' ... ", end='', flush=True)
                email_ids = self._fetch_email_ids(account, folder, mail_connection_cli) # Reuse connection if IMAP

                if email_ids is not None: # Liste kann leer sein, aber None bedeutet Fehler
                    count = len(email_ids)
                    print(f"{count} E-Mails gefunden.")
                    total_ids_found += count
                    for email_id in email_ids:
                        all_email_ids_with_folder.append((email_id, folder))
                else:
                    print("FEHLER beim Abruf.")
                    fetch_errors += 1

            # ID-Abruf Verbindung schließen (nur wenn IMAP und lokal geöffnet)
            if mail_connection_cli and account.protocol == 'imap' and mail_connection_cli.state != 'LOGOUT':
                 try: mail_connection_cli.logout()
                 except: pass
                 logging.info("CLI: IMAP Verbindung für ID-Abruf geschlossen.")

            if fetch_errors > 0:
                 print(f"\nWARNUNG: Fehler beim Abrufen von IDs aus {fetch_errors} Ordner(n). Siehe Logdatei '{log_filename}'.")

            if not all_email_ids_with_folder:
                 print("\nKeine E-Mails in den überprüften Ordnern gefunden.")
                 logging.info("CLI: Keine E-Mails gefunden.")
                 print("--------------------------------------------------")
                 return

            print(f"\nInsgesamt {total_ids_found} E-Mail IDs gefunden.")

            # --- Download und Speichern/Archivieren ---
            print(f"\nSchritt 2: Beginne Download & Speichern (Archiv > {age_days} Tage)...")
            processed_count = 0
            archived_count = 0
            saved_new_count = 0 # Zähler für neuere Mails
            skipped_age_count = 0 # Zähler für übersprungene (sollte 0 sein jetzt)
            error_count = 0
            download_connection_cli = None

            try:
                 # Verbindung für Download aufbauen
                 print(f"- Verbinde mit {account.protocol.upper()} Server {account.server} für Download...", end='', flush=True)
                 if account.protocol == 'imap':
                     download_connection_cli = imaplib.IMAP4_SSL(account.server, account.port, timeout=20)
                     download_connection_cli.login(account.email_address, account.password)
                 elif account.protocol == 'pop3':
                      download_connection_cli = poplib.POP3_SSL(account.server, account.port, timeout=20)
                      download_connection_cli.user(account.email_address)
                      download_connection_cli.pass_(account.password)
                 print(" Verbunden.")
                 logging.info(f"CLI: {account.protocol.upper()} Verbindung für Download für {account.email_address} hergestellt.")

                 current_folder_imap = None # Für IMAP Select Optimierung
                 for i, (email_id, folder_name) in enumerate(all_email_ids_with_folder):
                     # Fortschrittsanzeige alle N Mails oder prozentual
                     if (i + 1) % 10 == 0 or i == total_ids_found - 1:
                          progress = (i + 1) / total_ids_found * 100
                          # Fortschrittsanzeige angepasst
                          print(f"\r- Verarbeite E-Mail {i+1}/{total_ids_found} [{progress:.0f}%] (Archiviert: {archived_count}, Neu gesp.: {saved_new_count}, Fehler: {error_count})", end='', flush=True)

                     email_id_str = email_id.decode('ascii', 'ignore')
                     logging.debug(f"CLI: Verarbeite ID {email_id_str} aus Ordner '{folder_name}'.")

                     try:
                         # Bei IMAP sicherstellen, dass der richtige Ordner ausgewählt ist
                         if account.protocol == 'imap':
                             if current_folder_imap != folder_name:
                                 try:
                                     logging.debug(f"CLI: Wähle IMAP Ordner '{folder_name}'")
                                     # Immer readonly für Verarbeitung
                                     encoded_folder = f'"{folder_name}"'
                                     status, _ = download_connection_cli.select(encoded_folder, readonly=True)
                                     if status != 'OK':
                                          status_alt, _ = download_connection_cli.select(folder_name, readonly=True)
                                          if status_alt != 'OK':
                                               raise imaplib.IMAP4.error(f"Konnte Ordner '{folder_name}' nicht auswählen (Status: {status}/{status_alt})")
                                     current_folder_imap = folder_name
                                 except Exception as select_err:
                                     logging.error(f"CLI: Fehler beim Auswählen des IMAP Ordners '{folder_name}': {select_err}")
                                     error_count += 1
                                     logging.warning(f"CLI: Überspringe E-Mail ID {email_id_str} wegen Ordnerauswahlfehler.")
                                     continue # Nächste E-Mail

                         # E-Mail herunterladen und verarbeiten (mit Altersprüfung)
                         result = self._process_single_email_cli(account, email_id, folder_name, age_days, download_connection_cli)
                         processed_count += 1
                         if result == "archived":
                             archived_count += 1
                         elif result == "saved_new": # Ergebnis von _process_single_email_cli
                             saved_new_count += 1
                         elif result == "skipped_age": # Sollte nicht mehr vorkommen
                              skipped_age_count +=1
                              logging.warning(f"CLI: Status 'skipped_age' für ID {email_id_str} erhalten, sollte nicht passieren.")
                         else: # "error"
                             error_count += 1

                     except Exception as proc_err:
                          # Schwerwiegender Fehler bei dieser E-Mail
                          logging.error(f"CLI: Unerwarteter Fehler bei Verarbeitung von Email ID {email_id_str} aus Ordner {folder_name}: {proc_err}\n{traceback.format_exc()}")
                          error_count += 1

                 print() # Zeilenumbruch nach Fortschrittsanzeige

            except (imaplib.IMAP4.error, poplib.error_proto, smtplib.SMTPException, ConnectionError, TimeoutError) as dl_conn_err:
                 logging.error(f"CLI: Kritischer Verbindungsfehler während Download/Verarbeitung: {dl_conn_err}")
                 print(f"\nFEHLER: Verbindungsproblem während der Verarbeitung: {dl_conn_err}")
                 error_count += (total_ids_found - processed_count) # Restliche als Fehler zählen
            except Exception as dl_loop_err:
                 logging.error(f"CLI: Kritischer Fehler in der Download/Verarbeitungsschleife: {dl_loop_err}\n{traceback.format_exc()}")
                 print(f"\nFEHLER: Unerwarteter Fehler während der Verarbeitung: {dl_loop_err}")
                 error_count += (total_ids_found - processed_count)
            finally:
                 # Download Verbindung immer schließen
                 if download_connection_cli:
                     try:
                         if account.protocol == 'imap' and download_connection_cli.state != 'LOGOUT': download_connection_cli.logout()
                         elif account.protocol == 'pop3': download_connection_cli.quit()
                         logging.info(f"CLI: {account.protocol.upper()} Download Verbindung für {account.email_address} geschlossen.")
                     except Exception as close_err:
                         logging.warning(f"CLI: Fehler beim Schließen der Download-Verbindung: {close_err}")


            # --- Abschlussmeldung ---
            end_time = datetime.datetime.now()
            duration = end_time - start_time
            print("\n--- CLI Verarbeitung Zusammenfassung ---")
            print(f"- Dauer: {str(duration).split('.')[0]}") # Ohne Mikrosekunden
            print(f"- Geprüfte Ordner: {len(folders_to_check)}")
            print(f"- E-Mails gefunden: {total_ids_found}")
            print(f"- Verarbeitet: {processed_count}")
            print(f"- Archiviert (älter {age_days} T.): {archived_count}")
            print(f"- Neuere gespeichert: {saved_new_count}")
            if skipped_age_count > 0: # Nur anzeigen wenn unerwartet aufgetreten
                 print(f"- Unerwartet übersprungen: {skipped_age_count}")
            print(f"- Fehler: {error_count}")
            if error_count > 0 or fetch_errors > 0:
                 print(f"-> Details zu Fehlern siehe Logdatei: {log_filename}")
            logging.info(f"CLI Verarbeitung beendet für Konto '{account_name}'. Dauer: {duration}. Gefunden: {total_ids_found}, Verarbeitet: {processed_count}, Archiviert: {archived_count}, Neu gesp.: {saved_new_count}, Fehler: {error_count + fetch_errors}.")
            print("--------------------------------------")


        except Exception as e:
             # Allgemeiner Fehler während des Setups oder ID-Abrufs
             logging.critical(f"CLI Kritischer Fehler bei der E-Mail-Verarbeitung für Konto '{account_name}': {e}\n{traceback.format_exc()}")
             print(f"\nFEHLER: Ein unerwarteter kritischer Fehler ist aufgetreten: {e}")
             print("--------------------------------------------------")


    def _process_single_email_cli(self, account: EmailAccount, email_id: bytes, folder_name: str, age_days: int, mail_connection) -> str:
        """
        CLI Version: Lädt E-Mail herunter, prüft Alter, speichert im 'archiv' (wenn alt)
        oder 'emails' Ordner (wenn neu).
        Keine GUI-Interaktion. Gibt Status zurück: 'archived', 'saved_new', 'error'.
        """
        email_id_str = email_id.decode('ascii', 'ignore')
        logging.debug(f"CLI Proc: Starte Verarbeitung für ID {email_id_str} aus '{folder_name}'.")
        try:
            raw_email = self._download_email(account, email_id, folder_name, mail_connection)
            if raw_email:
                logging.debug(f"CLI Proc: ID {email_id_str} heruntergeladen ({len(raw_email)} Bytes). Parse Nachricht...")
                try:
                     email_msg = email.message_from_bytes(raw_email)
                except Exception as parse_error:
                     logging.error(f"CLI Proc: Fehler beim Parsen von E-Mail ID {email_id_str}: {parse_error}")
                     return "error"

                email_date = self._get_email_date(email_msg)

                # Altersprüfung und Zielordner bestimmen
                if self._is_older_than_days(email_date, age_days):
                    target_folder_base = "archiv"
                    logging.debug(f"CLI Proc: ID {email_id_str} ist älter als {age_days} Tage. Ziel: '{target_folder_base}'.")
                else:
                    # E-Mail ist nicht alt genug oder Datum unbekannt -> 'emails' Ordner
                    target_folder_base = "emails"
                    if email_date:
                         logging.debug(f"CLI Proc: ID {email_id_str} ist nicht älter als {age_days} Tage. Ziel: '{target_folder_base}'.")
                    else:
                         logging.debug(f"CLI Proc: ID {email_id_str} hat kein Datum oder konnte nicht geparst werden. Ziel: '{target_folder_base}'.")


                # Zielordner erstellen (inkl. Konto, Typ, Originalordner, Datum)
                try:
                     account_base_path = self._create_account_folder(account)
                     full_target_dir = self._create_target_folder(account_base_path, target_folder_base, folder_name)
                except Exception as folder_err:
                     logging.error(f"CLI Proc: Fehler beim Erstellen des Zielordners für ID {email_id_str}: {folder_err}")
                     return "error"

                # E-Mail und Anhänge speichern
                saved_path = self._save_email(account, email_msg, full_target_dir)
                if saved_path:
                     # Anhänge nur verarbeiten, wenn E-Mail erfolgreich gespeichert wurde
                     self._process_attachments(email_msg, full_target_dir)
                     log_message_suffix = "archiviert" if target_folder_base == "archiv" else "gespeichert"
                     logging.info(f"CLI Proc: E-Mail ID {email_id_str} aus Ordner '{folder_name}' erfolgreich in '{target_folder_base}' {log_message_suffix}: {saved_path}")
                     return "archived" if target_folder_base == "archiv" else "saved_new"
                else:
                     logging.error(f"CLI Proc: Fehler beim Speichern der E-Mail ID {email_id_str} aus Ordner '{folder_name}'.")
                     return "error"
            else:
                # Download fehlgeschlagen (Fehler wurde bereits in _download_email geloggt)
                logging.warning(f"CLI Proc: Download für ID {email_id_str} fehlgeschlagen.")
                return "error"
        except Exception as e:
            logging.error(f"CLI Proc: Unerwarteter Fehler beim Verarbeiten der E-Mail ID {email_id_str} aus Ordner '{folder_name}': {e}\n{traceback.format_exc()}")
            return "error"


    def run_cli_archive(self, args: argparse.Namespace):
        """
        Öffentliche Methode, um die CLI Archivierung basierend auf den geparsten Argumenten zu starten.
        Wird von __main__ aufgerufen.
        """
        account_name = args.account_name # Wurde bereits in __main__ geprüft
        folders = None
        if args.folders:
             folders = [folder.strip() for folder in args.folders.split(',') if folder.strip()]
             if not folders: folders = None # Leere Liste -> None

        age_days = args.age_days
        if age_days < 0:
             print("FEHLER: --age_days muss eine nicht-negative Zahl sein.")
             logging.error("CLI Fehler: --age_days ist negativ.")
             return

        # Starte die eigentliche CLI Archivierungslogik
        try:
             self.cli_archive_emails(account_name, folders, age_days)
        except Exception as cli_e:
             # Fängt unerwartete Fehler in der Haupt-CLI-Funktion ab
             logging.critical(f"Kritischer Fehler in run_cli_archive: {cli_e}\n{traceback.format_exc()}")
             print(f"\nFEHLER: Ein unerwarteter kritischer Fehler ist aufgetreten: {cli_e}")


# --- Hauptteil ---
if __name__ == "__main__":
    # Argument Parser konfigurieren
    parser = argparse.ArgumentParser(
        description="CipherCore E-Mail Suite - GUI und CLI zur E-Mail Speicherung und Verwaltung.", # Beschreibung leicht angepasst
        formatter_class=argparse.RawTextHelpFormatter # Für bessere Formatierung der Hilfe
    )
    parser.add_argument(
        '--cli',
        action='store_true',
        help='Starte die Anwendung im CLI-Modus zur automatischen E-Mail Speicherung.' # Hilfe angepasst
    )
    parser.add_argument(
        '--account_name',
        metavar='NAME',
        type=str,
        help='(Nur CLI) Name des E-Mail Kontos (wie in der GUI hinzugefügt), das verarbeitet werden soll.' # Hilfe angepasst
    )
    parser.add_argument(
        '--folders',
        metavar='F1,F2,...',
        type=str,
        help='(Nur CLI, Optional) Komma-separierte Liste von IMAP-Ordnern, die geprüft werden sollen.\n' # Hilfe angepasst
             'Beispiel: --folders "INBOX,Gesendet,Spam"\n'
             'Standard für IMAP, wenn nicht angegeben: "INBOX".\n'
             'Für POP3 wird dies ignoriert (immer Inbox).'
    )
    parser.add_argument(
        '--age_days',
        metavar='TAGE',
        type=int,
        default=30,
        help='(Nur CLI, Optional) Mindestalter der E-Mails in Tagen, die in den Ordner "archiv" gespeichert werden sollen.\n' # Hilfe angepasst
             'E-Mails, die jünger sind oder deren Datum nicht bestimmt werden kann, werden in den Ordner "emails" gespeichert.\n' # Hilfe angepasst
             'Standard: 30'
    )

    # --- Start ---
    print("--- CipherCore E-Mail Suite ---")
    try:
        args = parser.parse_args()

        # GUI Applikation instanziieren (lädt Konten, etc.)
        # Wichtig: Fehler beim Initialisieren abfangen
        try:
             app = EmailArchiverGUI()
        except Exception as init_err:
             logging.critical(f"Kritischer Fehler beim Initialisieren der Anwendung: {init_err}", exc_info=True)
             print(f"\nFATALER FEHLER: Anwendung konnte nicht initialisiert werden.")
             print(f"Fehler: {init_err}")
             print(f"Siehe Logdatei '{log_filename}' für Details.")
             # Beenden, da die App nicht funktionsfähig ist
             sys.exit(1)


        if args.cli:
            # --- CLI Modus ---
            logging.info("Anwendung im CLI Modus gestartet.")
            # Überprüfen, ob notwendige Argumente für CLI vorhanden sind
            if not args.account_name:
                 parser.print_help()
                 print("\nFEHLER: --account_name ist im CLI Modus erforderlich.")
                 logging.error("CLI Modus gestartet, aber --account_name fehlt.")
                 sys.exit(1) # Beenden mit Fehlercode

            # Starte die CLI Verarbeitung
            app.run_cli_archive(args)
            logging.info("CLI Modus beendet.")
            # Kein app.mainloop() im CLI Modus
            sys.exit(0) # Erfolgreich beendet

        else:
            # --- GUI Modus ---
            logging.info("Anwendung im GUI Modus gestartet.")
            print("Starte Grafische Benutzeroberfläche (GUI)...")
            # Starte die Tkinter Hauptschleife
            app.mainloop()
            logging.info("GUI Modus beendet.")
            sys.exit(0) # Erfolgreich beendet

    except SystemExit as se:
         # Fängt sys.exit() ab, um sauberen Exit Code zu haben
         if se.code != 0:
              logging.warning(f"Anwendung mit Exit Code {se.code} beendet (vermutlich Fehler oder --help).")
         else:
              logging.info(f"Anwendung normal beendet (Exit Code {se.code}).")
         raise # Exit weiterleiten
    except Exception as main_err:
         # Fängt alle anderen unerwarteten Fehler im Hauptteil ab
         logging.critical(f"Unerwarteter Fehler auf oberster Ebene: {main_err}", exc_info=True)
         print("\nFATALER FEHLER: Ein unerwarteter Fehler ist aufgetreten.")
         print(f"Fehler: {main_err}")
         print(f"Siehe Logdatei '{log_filename}' für Details.")
         sys.exit(2) # Beenden mit anderem Fehlercode
