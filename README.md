# efestoclient

EfestoClient provides controlling Efesto heat devices

# Usage

`heater = EfestoClient(url, username, password, deviceid)`

where as (for example):

- url = https://evastampaggi.efesto.web2app.it
- username = john_diggle
- password = MySup8rS3cretP@ssword
- deviceid = AA11BB22CC33

# Methods

All methods return JSON output and there is always a 'status' field present.

- If status = 0 => OK
- If status > 0 => FAILED

**Get system modes**

`heater.get_system_modes()`

example output:

`['OFF', 'START', 'LOAD PELLETS', 'FLAME LIGHT', 'ON', 'CLEANING FIRE-POT', 'CLEANING FINAL', 'ECO-STOP', '?', 'NO FIRE?', '?', '?', '?', '?', '?', '?', '?', '?', '?', '?']`

----------

**Get heater status**

`heater.get_status()`

example output:

`{'status': 0, 'deviceStatus': 7, 'smokeTemperature': 60, 'airTemperature': 24, 'deviceStatusTranslated': 'CLEANING FINAL', 'lastSetPower': 5, 'realPower': 2, 'lastSetAirTemperature': 20}`

----------

**Turn heater off**

`heater.set_off()`

example output:

`{'status': 0, 'message': 'ok'}`

----------

**Turn heater on**

`heater.set_on()`

example output:

`{'status': 0, 'message': 'ok'}`

----------

**Set temperature**

`heater.set_temperature(value)`

**value** = number that represents temperature value

example output:

`{'status': 0, 'message': 'ok'}`

**Set power**

`heater.set_power(value)`

**value** = number that represents the power level (fan operation)

example output:

`{'status': 0, 'message': 'ok'}`