#!/usr/bin/env python3
import xml.dom.minidom
import datetime
import itertools
import sys
import calendar
import re
import argparse
from pathlib import Path

try:
    import holidays

    print('holidays is installed, enabling automatic import of german holidays.')
    add_auto_holidays = True
except ImportError as e:
    print('holidays is not installed, disabling automatic import of german holidays.')
    add_auto_holidays = False

# Constants
xml.dom.minidom.Element.addClass = lambda x, y: x.setAttribute('class', x.getAttribute('class') + ' ' + str(y))
german_weekdays = ('montag', 'dienstag', 'mittwoch', 'donnerstag', 'freitag', 'samstag', 'sonntag')
german_months = ('Januar', 'Februar', 'März', 'April', 'Mai', 'Juni',
                 'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember')
filename = './templates/kalender_fsce.svg'
stylefile = './templates/style1.css'


class Calendar:
    def __init__(self):
        self.title = 'FSI-Kalender'
        self.lecture_times = []
        self.exam_times = []
        self.holidays_times = []
        self.date_to_special_day = {}
        # The first month shown in the calendar
        self.start_time = datetime.date(datetime.date.today().year, 1, 1)
        # The last month shown in the calendar
        self.end_time = datetime.date(datetime.date.today().year, 12, 31)
        # How many months is this calendar offset?
        self.global_offset = 0

    def read_config(self, config: str):
        try:
            # Ignore empty lines and comments
            conf = open(config, 'r')
            config_iterator = itertools.filterfalse(lambda l: l[0] == '#' or l[0] == '\n' or len(l) == 0, conf)
            conf.readline = lambda: next(config_iterator)

            self.title = conf.readline().strip()
            self.start_time = self.to_datetime(conf.readline().strip())
            self.end_time = self.to_datetime(conf.readline().strip())
            self.end_time.replace(day=calendar.monthrange(self.end_time.year, self.end_time.month)[1])
            self.global_offset = self.start_time.month - 1

            self.lecture_times = self.line_to_datetimes(conf.readline().strip())
            lecture_free_times = self.line_to_datetimes(conf.readline().strip())
            self.lecture_times = [item for item in self.lecture_times if item not in lecture_free_times]

            self.exam_times = self.line_to_datetimes(conf.readline().strip())

            # ab hier nur noch sondertage, bis StopIteration
            while True:
                cur_special_days = [(self.to_datetime(date, return_as_list=True), title, category) for
                                    (date, title, category) in
                                    [conf.readline().strip().split(',')]]

                for csd in cur_special_days:
                    for csd_date in csd[0]:
                        if self.date_to_special_day.get(csd_date) is None:
                            self.date_to_special_day[csd_date] = []
                        self.date_to_special_day[csd_date].append((csd[1], csd[2]))
        except StopIteration:
            pass
        except Exception as e:
            print('Error while reading in the config')
            print(e)
            sys.exit()

    def add_holidays(self):
        if add_auto_holidays:
            de_holidays = holidays.country_holidays('DE', subdiv='BY', language='de')
            tmp_loop_date = self.start_time
            while tmp_loop_date <= self.end_time:
                tmp_loop_date += datetime.timedelta(days=1)
                if tmp_loop_date in de_holidays:
                    if self.date_to_special_day.get(tmp_loop_date) is None:
                        self.date_to_special_day[tmp_loop_date] = []
                    self.date_to_special_day[tmp_loop_date].append((de_holidays.get(tmp_loop_date), 'feiertag'))

    def handle_sched(self, match: re.Match, return_as_list: bool = False):
        output = []
        start_date = self.to_datetime(match.group('beg'))
        end_date = self.to_datetime(match.group('end'))
        try:
            sched_units = {
                'w': datetime.timedelta(days=7),
                'd': datetime.timedelta(days=1),
            }
            if match.group('sch_u') not in sched_units.keys():
                raise RuntimeError('Non-implemented schedule unit')
            sched_unit = sched_units[match.group('sch_u')]
            sched_amount = int(match.group('sch_a'))
            delta = sched_unit * sched_amount
        except IndexError as _:
            delta = datetime.timedelta(days=1)
        while start_date <= end_date:
            output.append(start_date)
            start_date += delta
        return output

    def handle_single_date(self, match: re.Match, return_as_list: bool = False):
        try:
            d = int(match.group('d'))
        except IndexError as _:
            d = 1
        m = int(match.group('m'))

        output = []
        try:
            y = int(match.group('y'))
            output.append(datetime.date(y, m, d))
        except IndexError as _:
            for year in range(self.start_time.year, self.end_time.year + 1):
                output.append(datetime.date(year, m, d))

        if not return_as_list and len(output) == 1:
            return output[0]
        else:
            return output

    # Converts DD.MM, MM/YYYY, DD.MM.YYYY, DD.MM.YYYY-DD.MM.YYYY and DD.MM.YYYY~\d\w~DD.MM.YYYY to datetime objects
    # If return_list is True, then return singular element as lists.
    def to_datetime(self, string: str, return_as_list: bool = False):
        # In order of execution, only for first match handler is called
        patterns = [
            (r'(?P<beg>\d?\d\.\d?\d\.\d\d\d\d)-(?P<end>\d\d\.\d?\d\.\d\d\d\d)',
             self.handle_sched),
            (r'(?P<beg>\d?\d\.\d?\d\.\d\d\d\d)~(?P<sch_a>\d+)(?P<sch_u>\w)~(?P<end>\d?\d\.\d?\d\.\d\d\d\d)',
             self.handle_sched),
            (r'(?P<d>\d?\d)\.(?P<m>\d\d)\.(?P<y>\d\d\d\d)',
             self.handle_single_date),
            (r'(?P<d>\d?\d)\.(?P<m>\d?\d)',
             self.handle_single_date),
            (r'(?P<m>\d?\d)/(?P<y>\d\d\d\d)',
             self.handle_single_date),
        ]

        for pattern in patterns:
            match = re.match(pattern[0], string)
            if match is not None:
                return pattern[1](match, return_as_list=return_as_list)

    # Parse line of format DT-DT, DT-DT to a list of individual date times
    def line_to_datetimes(self, string: str):
        output = []
        ranges = string.split(',')
        for entry in ranges:
            res = self.to_datetime(entry.strip())
            if isinstance(res, list):
                output.extend(res)
            else:
                output.append(res)
        return output

    # Returns None if id-string is of a non-existing date
    def date_from_id_string(self, id_string: str, offset: int = 0):
        month = (int(id_string[0:id_string.find('-')]) - 1 + offset) % 12 + 1
        day = int(id_string[id_string.find('-') + 1:])

        try:
            l_cur_date = datetime.date(self.start_time.year, month, day)
            if l_cur_date < self.start_time:
                year = self.start_time.year + 1
            else:
                year = self.start_time.year
            # That has to be done here because of friggn February 29th.
            l_cur_date = datetime.date(year, month, day)
        except ValueError:
            return None

        return l_cur_date

    def generate_calendar(self, template_file: str, style_file: str, outpupt_file: str):
        # vorlage oeffnen
        try:
            image = xml.dom.minidom.parse(filename)
        except IOError:
            print('No .svg data found under ' + filename)
            sys.exit(1)

        # css eintragen
        try:
            image.getElementsByTagName('style')[0].firstChild.replaceWholeText(open(stylefile).read())
        except IOError:
            print('Konnte CSS nicht oeffnen. Huh?!')
            sys.exit()

        # Add Title
        textElement = [t for t in image.getElementsByTagName('text') if t.getAttribute('id') == 'title']
        textElement[0].firstChild.replaceWholeText(self.title)

        # jedes rect anschauen
        for rect in image.getElementsByTagName('rect'):
            if 'title bar' in rect.getAttribute('class'):
                rect.addClass('titlebar')

            if 'day' in rect.getAttribute('class'):
                # tag und monat ausblenden
                cur_date = self.date_from_id_string(rect.getAttribute('id'), self.global_offset)

                # tage, die es im monat nicht gibt, ausblenden
                if cur_date is None:
                    rect.addClass('invisible')
                    rect.nextSibling.nextSibling.addClass('invisible')
                    continue

                wochentag = cur_date.weekday()
                rect.setAttribute('weekday', german_weekdays[wochentag])

                # wochennummer einfuegen
                offset = 0
                if wochentag == 0:
                    offset = 15  # 15=1/2 fontsize
                    rect.parentNode.insertBefore(xml.dom.minidom.parseString(
                        '''<text id='{}-{}-woy' class='weekday' style='font-size:30px' x='{}' y='{}'>{}</text>'''
                        .format(cur_date.month,
                                cur_date.day,
                                float(rect.getAttribute('x')) + 16,
                                float(rect.getAttribute('y')) + float(rect.getAttribute('height')) / 2 + 10 - offset,
                                cur_date.isocalendar().week)).firstChild, rect.nextSibling)

                # ferien und feiertage faerben
                if cur_date not in self.lecture_times or cur_date in self.holidays_times:
                    rect.addClass('holiday')

                if wochentag == 5 or wochentag == 6:
                    rect.addClass('weekend')

                # besondere tage (geburtstage etc.) kennzeichnen
                if cur_date in self.date_to_special_day:
                    for i, sondertag in enumerate(self.date_to_special_day[cur_date]):
                        rect.addClass(sondertag[1])

                if cur_date in self.date_to_special_day:
                    # pro eintrag an diesem tag klasse setzen, bezeichnung einfuegen
                    for i, sondertag in enumerate(self.date_to_special_day[cur_date]):
                        if 'birthday' in sondertag[1]:
                            # rect.addClass(sondertag[1])
                            rect.parentNode.insertBefore(xml.dom.minidom.parseString(
                                '''<text id='{}-{}-special' class='birthdaytext' style='font-size:{}px;' x='{}' y='{}'>{}</text>'''
                                .format(cur_date.month,
                                        cur_date.day,
                                        # textgroesse haengt von anzahl der eintraege ab
                                        float(rect.getAttribute('height')) / 2.2,
                                        float(rect.getAttribute('x')) + 60,
                                        # y mit magischer formel bestimmen, die auch die anzahl der eintraege mit einbezieht
                                        float(rect.getAttribute('y')) + float(rect.getAttribute('height')) / len(
                                            self.date_to_special_day[cur_date]) * (i + 1) - 0.3 * (
                                                float(rect.getAttribute('height')) / (
                                                0.7 + 0.7 * len(self.date_to_special_day[cur_date]))),
                                        sondertag[0])).firstChild, rect.nextSibling)
                        else:
                            if 'feiertag' in rect.getAttribute('class'):
                                rect.addClass('weekend')
                            # rect.addClass(sondertag[1])
                            rect.parentNode.insertBefore(xml.dom.minidom.parseString(
                                '''<text id='{}-{}-special' class='feiertagstext' style='font-size:{}px;' x='{}' y='{}'>{}</text>'''
                                .format(cur_date.month,
                                        cur_date.day,
                                        # textgroesse haengt von anzahl der eintraege ab
                                        float(rect.getAttribute('height')) / 3.3,
                                        float(rect.getAttribute('x')) + 58,
                                        # y mit magischer formel bestimmen, die auch die anzahl der eintraege mit einbezieht
                                        float(rect.getAttribute('y')) + float(rect.getAttribute('height')) / len(
                                            self.date_to_special_day[cur_date]) * (i + 1) - 0.3 * (
                                                float(rect.getAttribute('height')) / (
                                                0.7 + 0.7 * len(self.date_to_special_day[cur_date]))),
                                        sondertag[0])).firstChild, rect.nextSibling)

                # wochentag einfuegen
                rect.parentNode.insertBefore(
                    xml.dom.minidom.parseString(
                        '''<text id='{}-{}-weekday' style='font-size:25px;' x='{}' y='{}'>{}</text>'''
                        .format(cur_date.month,
                                cur_date.day,
                                float(rect.getAttribute('x')) + 16,
                                float(rect.getAttribute('y')) + float(
                                    rect.getAttribute('height')) / 2 + 10 + offset,
                                german_weekdays[wochentag][0:2])).firstChild, rect.nextSibling)

            if 'mark' in rect.getAttribute('class'):
                # tag und monat ausblenden
                cur_date = self.date_from_id_string(rect.getAttribute('id'), self.global_offset)

                if cur_date is None:
                    rect.addClass('invisible')
                    continue

                # besondere tage (geburtstage, ccc) kennzeichnen
                if cur_date in self.date_to_special_day:
                    for i, sondertag in enumerate(self.date_to_special_day[cur_date]):
                        rect.addClass(sondertag[1])

                if cur_date in self.exam_times:
                    rect.addClass('pruefungmark')

                if cur_date in self.date_to_special_day:
                    for i, sondertag in enumerate(self.date_to_special_day[cur_date]):
                        if 'berg' in rect.getAttribute('class'):
                            rect.addClass('bergmark')
                        if 'sonstiges' in rect.getAttribute('class'):
                            rect.addClass('sonstigesmark')
                        if 'fsi' in rect.getAttribute('class'):
                            rect.addClass('fsimark')
                        if 'birthday' in rect.getAttribute('class'):
                            rect.addClass('birthdaymark')

                if cur_date in self.holidays_times:
                    if 'birthday' not in rect.getAttribute('class') and 'berg' not in rect.getAttribute(
                            'class') and 'sonstiges' not in rect.getAttribute('class'):
                        rect.addClass('holidaymark')

                if 'berg' not in rect.getAttribute('class') and 'sonstiges' not in rect.getAttribute(
                        'class') and 'pruefung' not in rect.getAttribute('class'):
                    rect.addClass('invisible')

            if 'frame' in rect.getAttribute('class'):
                # tag und monat ausblenden
                cur_date = self.date_from_id_string(rect.getAttribute('id'), self.global_offset)

                if cur_date is None:
                    rect.addClass('invisible')
                    continue

                rect.addClass('nofill')

        # Update month names
        month_count = 0
        txt_node_0 = None
        for txt in image.getElementsByTagName('text'):
            if 'monthname' in txt.getAttribute('class'):
                cur_mon = (month_count + self.global_offset) % 12
                if cur_mon == 0:
                    txt_node_0 = txt
                txt.childNodes[0].data = german_months[cur_mon]
                month_count += 1
        txt_node_0.parentNode.insertBefore(xml.dom.minidom.parseString(
            '''<text id='y_dvd' class='monthname' x='{}' y='{}'>{}</text>'''
            .format(float(txt_node_0.getAttribute('x')),
                    float(txt_node_0.getAttribute('y')) - 60.0,
                    str(self.end_time.year))).firstChild, txt_node_0.nextSibling)
        txt_node_0.parentNode.insertBefore(xml.dom.minidom.parseString(
            '''<text id='y_dvd' class='monthname' x='{}' y='{}'>{}</text>'''
            .format(204.02109,
                    float(txt_node_0.getAttribute('y')) - 60.0,
                    str(self.start_time.year))).firstChild, txt_node_0.nextSibling)

        f = open(outpupt_file, 'w')

        image.writexml(f)
        f.close()


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Generate a calendar')
    parser.add_argument('config', metavar='config', type=Path, help='Path to config file')
    parser.add_argument('-o', '--output', type=Path, help='Path to write output file',
                        default='./outputCalendar.svg', required=False, nargs='?')
    args = parser.parse_args()

    cal = Calendar()
    cal.read_config(args.config)
    cal.add_holidays()
    cal.generate_calendar(template_file=filename, style_file=stylefile, outpupt_file=args.output)

    print('Warning: When printing, convert to cmyk first (inkscape->png; convert mycal.png -colorspace cmyk mycal.jpg)')
