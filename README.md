# **CipherMailArchiver** 📩🔒  
_Effiziente & sichere E-Mail-Archivierung mit IMAP & POP3 – Open-Source & lokal speichernd._

---

### **📌 Überblick**  
**CipherMailArchiver** ist eine **leistungsstarke Open-Source-Anwendung** zur **sicheren E-Mail-Archivierung** mit **lokaler Speicherung**. Die Anwendung ermöglicht das **automatische Abrufen, Organisieren und Speichern von E-Mails und Anhängen**, unterstützt sowohl **IMAP als auch POP3** und schützt Passwörter mit **Keyring**.  

> **Kein Cloud-Zwang, keine fremden Server – Deine Daten bleiben lokal.**  

✔ **Ideal für Unternehmen & Privatanwender**  
✔ **Speichert E-Mails und Anhänge automatisch nach Datum & Kategorie**  
✔ **Funktioniert mit allen gängigen E-Mail-Anbietern**  

---

## **🚀 Features**  
🔹 **Automatische E-Mail-Archivierung** (lokal, strukturiert nach Datum)  
🔹 **IMAP & POP3 Unterstützung** für alle gängigen Mailserver  
🔹 **Passwortschutz mit Keyring** – Keine Klartext-Speicherung  
🔹 **GUI mit `tkinter`** für intuitive Benutzerführung  
🔹 **Anhangsverwaltung** – Speichert Anhänge separat & automatisch  
🔹 **Robuste Fehlerbehandlung & Logging** für zuverlässige Nutzung  

---

## **💾 Installation**  

### **🔹 Voraussetzung**  
✔ **Python 3.12** oder höher (kompatibel mit Linux, Windows, macOS)  
✔ **pip installiert** (Standard in Python enthalten)  

### **🔹 1️⃣ Repository klonen**  
```bash
git clone https://github.com/CipherCorePro/CipherMailArchiver.git
cd CipherMailArchiver
```

### **🔹 2️⃣ Abhängigkeiten installieren**  
```bash
pip install -r requirements.txt
```

### **🔹 3️⃣ Programm starten**  
```bash
python ciphermailarchiver.py
```

---

## **🛠️ Nutzung**  
1️⃣ **E-Mail-Konto hinzufügen** → Serverdaten eingeben (IMAP/POP3).  
2️⃣ **Passwort wird sicher gespeichert** (Keyring).  
3️⃣ **E-Mails abrufen & archivieren** → Programm speichert alle neuen E-Mails lokal.  
4️⃣ **Anhänge werden automatisch gespeichert** → In separaten Ordnern pro Datum.  

---

## **📂 Datei- & Verzeichnisstruktur**  
```
CipherMailArchiver/
│── ciphermailarchiver.py      # Hauptprogramm
│── README.md                  # Dokumentation
│── requirements.txt            # Abhängigkeiten
│── accounts.txt                # Gespeicherte E-Mail-Konten (ohne Passwörter)
│── logs/                       # Logdateien
│── emails/                     # Archivierte E-Mails
│── archiv/                     # Ältere E-Mails (älter als 5 Tage)
│── attachments/                 # Gespeicherte Anhänge
```

---

## **🔒 Sicherheit**  
- **Passwörter werden NICHT in Klartext gespeichert!**  
- **Verwendung von `keyring` zur sicheren Speicherung der Anmeldedaten.**  
- **E-Mails und Anhänge werden nur lokal gespeichert, keine Cloud-Speicherung.**  

---

## **💡 Beispiele & Screenshots**  

### **📜 GUI – Konto hinzufügen**  
➡️ **Einfaches Hinzufügen von E-Mail-Konten mit IMAP oder POP3.**  
![Konto Hinzufügen](https://example.com/gui-konto.png)

### **📥 Automatischer Abruf & Speicherung**  
➡️ **E-Mails werden automatisch heruntergeladen & organisiert.**  
![E-Mail Abruf](https://example.com/email-abruf.png)

### **📂 Strukturierte Speicherung**  
➡️ **E-Mails & Anhänge sauber nach Datum sortiert.**  
```
emails/
├── 2025-02-25/
│   ├── email_1.txt
│   ├── email_2.txt
│   ├── anhänge/
│   │   ├── file1.pdf
│   │   ├── file2.jpg
```

---

## **🤝 Mitwirken & Support**  
- 🛠 **Fehlermeldung oder Verbesserungsvorschlag?** → Öffne ein [Issue](https://github.com/CipherCorePro/CipherMailArchiver/issues).  
- 💡 **Feature-Idee?** → Starte eine Diskussion!  
- ⭐ **Hilfreich?** → **Starte & folge** dem Projekt auf GitHub!  

---

## **📜 Lizenz**  
Dieses Projekt ist unter der **MIT-Lizenz** veröffentlicht – **Open Source & frei nutzbar.**  

---

🎯 **CipherMailArchiver** ist die ideale Lösung für **alle, die E-Mails lokal & sicher speichern möchten.**  
**➡️ Starte jetzt mit `CipherMailArchiver`!** 🚀
