This repo holds the Python Module + a Service application to frequently poll a Windhager BioWin102 from 2018 which I run in my house.

This repo is in no means complete or bullet-proof! Just hacked it down to be able to monitor and somewhen also control this device.


# Windhager.py

Implements a basic module to get/set values via the HTTP API provided by the InfoWin Touch used in BioWin102.
The API is documented in <windhager-ip>/api-docs.
Most important are /api/1.0/lookup and /api/1.0/datapoint{s}

# windhager-influx.py

Simple service script which polls all datapoints and pushes them if a value is present into influxdb.

# undocumented-oids.txt

Unfortunately even after requesting information via the Windhager-Support several values in my case are not documented and only the OID's are known. This is "OK" for the Support and no real help was given here.

So I started to reverse-engineer a little here by just monitoring all unknown values and trying to match those.

Some are very easy because on the InfoWinTouch display some identical values are displayed.

Also when a value was found I searched VarIdentTexte_de.xml for similar entries and noted the number as (XML: xxx)
