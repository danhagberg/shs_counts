import re
from collections import Counter
from datetime import datetime

import bs4
import pandas as pd


def extract_month_year(sched) -> tuple:
    month = int(sched.find('input', {"name": "SDM"}).get('value'))
    year = int(sched.find('input', {"name": "SDY"}).get('value'))
    return month, year


def find_sched_rows(sched) -> list:
    sched_table = sched.find('table', id='P2_29')
    sched_rows = sched_table.find_all('tr', class_='vicnet229')
    return sched_rows


def extract_day(sched_col) -> int:
    sched_day = sched_col.find('span', {'class': 'e'})
    if sched_day:
        day_text = sched_day.text
        if re.fullmatch(r'\d{1,2}', day_text):
            return int(day_text)

    return -1


def get_shift_counts_for_day(sched_entries) -> Counter:
    shift_counts = Counter()
    rx = re.compile(r'GREEN-D')
    time_extract = re.compile(r'(.*)Dog Care.*')
    for se in sched_entries:
        elem = se.find('', text=rx)
        if elem:
            text = elem.parent.get_text()
            text = text.replace("\n", "")
            time_match = time_extract.match(text)
            if time_match:
                shift = time_match.group(1)
                shift = shift.replace(u"\xa0", u" ")
                shift = shift.replace("a", "am")
                shift = shift.replace("p", "pm")
                begin, end = shift.split('-')
                begin = begin.strip()
                end = end.strip()
                shift_time = (begin, end)
                shift_counts[shift_time] += 1
    return shift_counts


def map_shift_counts(sched_rows, year, month) -> dict:
    counts_by_shift = {}
    for sched_row in sched_rows:
        for sched_col in sched_row.find_all('td', class_='a', recursive=False):
            day = extract_day(sched_col)
            if day < 1:
                continue
            sched_entries_table = sched_col.find('table', id='P2_31')
            if not sched_entries_table:
                continue
            sched_entries = sched_entries_table.find_all('tr', class_='vicnet228')
            counts_by_shift[(year, month, day)] = get_shift_counts_for_day(sched_entries)
    return counts_by_shift


def process_dce_html_file(file_name) -> dict:
    with open(file_name, 'rb') as dce_html:
        sched = bs4.BeautifulSoup(dce_html.read(), 'html5lib')
    month, year = extract_month_year(sched)
    sched_rows = find_sched_rows(sched)
    shift_counts = map_shift_counts(sched_rows, year, month)
    return shift_counts


def get_time_component(time: str) -> tuple:
    period_adjust = {'am': 0, 'pm': 12}
    time_pat = re.compile('[: ]')
    h, m, period = time_pat.split(time)
    hour = int(h) % 12
    minute = int(m)
    adj = period_adjust.get(period.lower()) or 0
    hour += adj
    return hour, minute


def get_counts_by_shift(shift_counts: dict) -> dict:
    counts_by_shift = []
    for day, counts in shift_counts.items():
        for time, count in counts.items():
            s_time = get_time_component(time[0])
            e_time = get_time_component(time[1])
            start = datetime(*day, *s_time)
            end = datetime(*day, *e_time)
            counts_by_shift.append({'Start_Date': start, 'End_Date': end, 'Green': count})
    counts_df = pd.DataFrame.from_dict(counts_by_shift)
    return counts_df.groupby(['Start_Date', 'End_Date']).sum()


def load_and_summarize_dce_counts(file_name: str) -> pd.DataFrame:
    shift_counts = process_dce_html_file('/Users/dhagberg/Desktop/DCE2.html')
    shift_counts_df = get_counts_by_shift(shift_counts)
    return shift_counts_df


def main():
    shift_counts_df = load_and_summarize_dce_counts('/Users/dhagberg/Desktop/DCE2.html')

    print(shift_counts_df)


if __name__ == '__main__':
    main()
