# MsRun

|Name (Alias)|Type (Default)|Constraints|Description|
|---|---|----|----------|
id|<code>int</code>|-|
name|<code>str</code>|-|The msRun's name\.
location|<code>str</code>|**required**<br/>Validation type: **<code>error</code>**|The msRun's location URI\.
instrument_ref|<code>int</code>|-|Sample reference\.
format|<code>Parameter</code>|-|
id_format|<code>Parameter</code>|-|
fragmentation_method|List of <code>Parameter</code>|-|The fragmentation methods applied during this msRun\.
scan_polarity|List of <code>Parameter</code>|-|The scan polarity/polarities used during this msRun\.
hash|<code>str</code>|-|The file hash value of this msRun's data file\.
hash_method|<code>Parameter</code>|-|
