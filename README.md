Dieses Projekt dient zum Monitoring und der Optimierung meiner BioWin2 von Windhager.

**Benutzung auf eigene Gefahr! Diese Skripte funktionieren für mich sind aber alles andere als gut getestet!**

# Windhager.py

Implementierung von ein paar get/set Befehlen zur Benutzung der HTTP-API des InfoWin-Touch von Windhager.
Die API ist unter <windhager-ip>/api-docs Dokumentiert.

Die wichtigsten Endpunkte sind /api/1.0/lookup und /api/1.0/datapoint{s}

# windhager-influx.py

Simples Skript welches alle verfügbaren Datenpunkte abfragt und diese in eine InlufxDB schiebt.
Geeignet um alle Datenpunkte zu analysieren und auch zu sehen was die Unbekannten Einträge sein könnten.

# undocumented-oids.txt

![Bild](screenshots/20211203_webif_unbekannt.png)

Im Web-Interface des InfoWin-Touch gibt es leider etliche Einträge "Unbekannte Ebene" bzw. "Unbekannter Wert" (siehe).
Leider konnte auch der Windhager-Support (technik@de.windhager.com) hier keine Abhilfe bieten da diesem hierzu selbst keine Dokumentation vorliegen würde. Es sei ein Feuerungsautomat verbaut welche in der Weboberfläche nicht eingepflegt wurde. Ganz wichtig: "Dei Funktion ist hier vollumfänglich gegeben" (das ist doch ein Kundenservice).

Aus diesem Grund wurden per windhager-influx.py für ein paar Wochen jedgliche Parameter aufgezeichnet und versucht deren Bedeutung heraus zu finden.

* Anzahl Werte gesamt: 144
* Anzahl Werte mit Namen: 111
* Anzahl Unbekannter Werte: 67


# Warmwasser / Brennerstarts Optimierung

Skript: ww-override.py

## Problem

Bei normalem Winter-Betrieb Zündet die Heizung bei uns (ohne Pufferspeicher) 3-6x pro Tag für lediglich 1-3h.
Die längste Zeit ist morgens wenn sowohl FBH als auch WW hochheizen. Aber insbeondere hier ist folgendes Verhalten festzustellen:

* Sobald die WW Ladung abgeschlossen ist kommt es fast immer zum Ausbrand, da die Wärme nicht abgeführt werden kann und die Kesseltemperatur >80° wird.
* Kurz darauf (<1h) wird wieder gezündet
* Siehe [Bild](screenshots/20211205_default_windhager.png)

Auch durch anpassen der Parameter für WW (Zeiten, Höhe usw.) konnte die Situation zwar "verschoben" werden aber es wurde auch immer deutlich der Komfort verschlechert.

## Lösungsansatz (Winter d.h. FBH aktiv)

Dieses Skript nutzt Werte der BioWin um ein Relais (Tasmota) zu steuern welches parallel die WW-Ladepumpe schalten kann (die BioWin kann dies weiterhin auch noch!).
Die Schaltung hierfür sollte selbsterklärend sein.

Die Steuerung der BioWin selbst hat nun tagsüber eine WW-Temperatur-Einstellung von 42° und nachts für 32°. Dies führt dazu, dass in Kombination mit diesem Skript keine WW-Anforderungen mehr durch die BioWin erzeugt werden.

Um nun dennoch WW zu haben wird die WW-Ladepumpe von diesem Skript und folgenden Bedingungen zugeschaltet (Kesselleistung > 0):

* WW-Temperatur < 45 oder
* Kesseltemperatur > 77 oder
* Kesselleitung < 50%

Abgeschaltet wird die WW-Ladepumpe wenn:
* Kessel Aus oder
* WW-Temperatur > 65 oder
* Kesseltemperatur < 65 oder
* Kesselleitung > 95%

Somit ist über den Tag gesehen immer WW verfügbar und der Brenner kann deutlich längere und weniger Zyklen fahren. Die recht frühe Abschaltung der Pumpe ist nötig damit der Kessel die Leistung nicht erhöht. Leider regelt diese nur sehr ungern runter (was verständlich ist).

## Ergebnisse:

* [Erste manuelle Versuche](screenshots/20211203_wwoverride_manul_first_try.png)
  Hier wurde nur nebenzu die WW-Ladepumpe manuell geschaltet um ein erstes Gefühl zu bekommen. Aktiv war dies zwischen 8:00 bis 11:00 wobei ich ich den letzten Peak leider etwas zuspät abgefangen hatte. Am Nachmittag zwischen 15 und 17:00 Uhr. Auch hier habe ich beim letzten Peak zu langsam reagiert und gleich eine Zündung wegen veränderung des WW-Soll hinter her bekommen.

