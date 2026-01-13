# CRCR

CalendrCreatr is a python script for fast creation of simple-styled calendars in svg format. 
This is a fork from t-animal/CRCR.

## Features
- Automatic Import of german holidays if `holidays` package is installed.
- Creates a calendar for any period of 12 months
- Write periodic dates in the calendar

## Quick Execution Guide

On Linux:
```
python -m venv ./venv
source venv/bin/activate
# following line optional
pip install holidays
python calendrcreatr.py ./calendar_2024_2025_temp.conf
```

On Windows:
```
python -m venv .\venv
.\venv\bin\activate
# following line optional
pip install holidays
python calendrcreatr.py .\calendar_2024_2025_temp.conf
```

## Config Structure

See `calendar_2024_2025_temp.conf` for an example of a config file.

Empty lines and lines starting with `#` are ignored.
Single dates can be given in den format `DD.MM.YYYY`, a range can be also given by `DD.MM.YYYY-DD.MM.YYYY`.
Weekly dates can be written by `DD.MM.YYYY~1w~DD.MM.YYYY`. The given number can be adjusted to `2` for biweekly schedules.

## License

This software is released under CC-BY-SA-NC 3.
(yes I know that this is technically not a software license. So use it for personal use, ask if you want to make money from that and retain a notice of this license. Use your common sense.)

### Contributors
- t-animal
- FS CE
- Timm638