Dieses Projekt dient zum Monitoring und der Optimierung meiner BioWin2 von Windhager von 2018.

**Benutzung auf eigene Gefahr! Diese Skripte funktionieren für mich sind aber alles andere als gut getestet!**

Alle Features und Veränderungen welche ich in diesem Projekt vornehme nehmen keine Einfluss auf die BioWin2
bzw. wenn nur über zugängliche API's welche auch Dokumentiert sind.

# BioWin2

![BioWin2 Touch](screenshots/biowin2_touch.jpg)

## Zugangsdaten

Laut Anleitung, default:

* User: User ; Password: 123
* User: Service ; Password: 123

# Windhager.py

Implementiert ein paar get/set Befehle zur Benutzung der HTTP-API des InfoWin.
Die API ist unter <windhager-ip>/api-docs Dokumentiert.

Die wichtigsten Endpunkte sind /api/1.0/lookup und /api/1.0/datapoint{s}

Ich habe bisher davon abgesehen die weiteren APIs zu nutzen. Insbesondere alles was Werte ändern angeht habe ich gelassen.

# windhager-influx.py

Simples Skript welches die Datenpunkte welche in oids.txt (--oids) gelistet sind regelmäßig abfragt und in eine InfluxDB schreibt.
In meinem Fall werden die Daten per Grafana visualisiert:

![Grafana Beispiel](screenshots/20211129_grafana_beispiel.png)

# Undokummentierte Parameter im Webinterface

![Webinterface Unbekannte Parameter](screenshots/20211203_webif_unbekannt.png)

Im Web-Interface des InfoWin-Touch gibt es leider etliche Einträge "Unbekannte Ebene" bzw. "Unbekannter Wert" (siehe).
Leider konnte auch der Windhager-Support (technik@de.windhager.com) hier keine Abhilfe bieten da diesem hierzu selbst keine Dokumentation vorliegen würde. Es sei ein Feuerungsautomat verbaut welche in der Weboberfläche nicht eingepflegt wurde. Ganz wichtig: "Dei Funktion ist hier vollumfänglich gegeben" (das ist doch ein Kundenservice).

Aus diesem Grund wurden per windhager-influx.py für ein paar Wochen jedgliche Parameter aufgezeichnet und versucht deren Bedeutung heraus zu finden.

* Anzahl Werte gesamt: 144
* Anzahl Werte mit Namen: 111
* Anzahl Unbekannter Werte: 67

Auch sehr ärgerlich: Manche Parameter bei denen 'writeProtect' = False ist lassen sich nicht ändern. Stattdessen läuft der Request in einen Timeout mit Bad Gateway Error.

# Warmwasser / Brennerstarts Optimierung

Skript: ww-override.py

## Problem

Bei normalem Winter-Betrieb Zündet die Heizung bei uns (ohne Pufferspeicher) 3-6x pro Tag für lediglich 1-3h.
Die längste Zeit ist morgens wenn sowohl FBH als auch WW hochheizen. Aber insbeondere hier ist folgendes Verhalten festzustellen:

* Sobald die WW Ladung abgeschlossen ist kommt es fast immer zum Ausbrand, da die Wärme nicht abgeführt werden kann und die Kesseltemperatur >80° wird.
* Kurz darauf (<1h) wird wieder gezündet

![Bild](screenshots/20211205_default_windhager.PNG)

Auch durch anpassen der Parameter für WW (Zeiten, Höhe usw.) konnte die Situation zwar "verschoben" werden aber es wurde auch immer deutlich der Komfort verschlechert. Auch mit dem Techniker wurde das Thema durchgegangen welcher auf einen Pufferspeicher verwies.

## Lösungsansatz (Winter d.h. FBH aktiv)

Dieses Skript nutzt Werte der BioWin um ein Relais (Tasmota) zu steuern welches parallel die WW-Ladepumpe schalten kann (die BioWin kann dies weiterhin auch noch!).
Die Schaltung hierfür sollte selbsterklärend sein.

Die BioWin WW-Temperaturangaben habe ich etwas verringert - aber durch die eingestellte Hysterese in der Heizung von -8K musste hier nur minimal angepasst werden.
Die WW-Anforderung der BioWin ist irgenwann vorbei. Normal würde hier der Überschwinger kommen. Hier schreitet nun dieses Skript ein in dem es folgendes tut:

Eingeschaltet wird die WW-Ladepumpe wenn:
* WW-Temperatur < ww_on oder
* Kesseltemperatur > kessel_max oder
* Kesselleitung < leistung_min

Abgeschaltet wird die WW-Ladepumpe wenn:
* Kessel Aus oder
* WW-Temperatur > ww_off oder
* Kesseltemperatur < kessel_min oder
* Kesselleitung > leistung_max

Dies hat zusätzlich zu der längeren Laufzeit den sehr scharmanten Vorteil, dass der WW-Speicher immer wieder etwas nachgeladen wird. Wird nun unter Tag viel WW Verbraucht muss die Heizung nicht erst zünden sondern schiebt einfach etwas Energie nach die vermutlich sowieso gerade zuviel ist.

## Ergebnisse:

### Erste manuelle Experimente

Hier wurde nur nebenzu die WW-Ladepumpe manuell geschaltet um ein erstes Gefühl zu bekommen. Aktiv war dies zwischen 8:00 bis 11:00 wobei ich ich den letzten Peak leider etwas zuspät abgefangen hatte. Am Nachmittag zwischen 15 und 17:00 Uhr. Auch hier habe ich beim letzten Peak zu langsam reagiert und gleich eine Zündung wegen veränderung des WW-Soll hinter her bekommen.

![Erste manuelle Versuche](screenshots/20211203_wwoverride_manul_first_try.png)

### Erste 1,5 Tage mit dem Skript

Zu sehen sind vier Starts in zwei Tagen. Der Morgentliche ist natürlich länger (6 Stunden, maximum der BioWin wie es scheint). Der am Nachmittag wird wohl nutzungsabhängig sein.
Noch zu untersuchen ist wie der Pelletverbrauch sich im Vergleich zu vorher entwickelt. Hierfür muss das ganze aber erst einmal eine Weile laufen.

![Erste zwei Tage](screenshots/20211211_ww_override.png)



# Bekannte Probleme

## Zündung Ausbrand durch Brennstoffanforderung

System ist auf Brennstoffanforderung mit Vorgabezeit von 11:00 bis 15:00 Uhr eingestellt.
Zündet die Heizung kurz vor 15:00 (Ende der Freigabezeit) fällt ihr anscheinend kurz danach auf, dass sie noch Brennstoff braucht und geht direkt in den Ausbrand.

![Zündung Ausbrand](screenshots/20211212_ausbrand_bei_brennstoffanforderung.png)
