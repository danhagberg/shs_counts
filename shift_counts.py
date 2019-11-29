import re
from argparse import ArgumentParser
from datetime import date, datetime, timedelta
from typing import Tuple

import pandas as pd
import tabula

shift_times = {
    1: (((7, 30), (10, 30)), ((13, 0), (16, 0)), ((16, 0), (18, 0))),
    2: (((7, 30), (10, 30)), ((13, 0), (16, 0)), ((16, 0), (18, 0))),
    3: (((7, 30), (10, 30)), ((13, 0), (16, 0)), ((16, 0), (18, 0))),
    4: (((7, 30), (10, 30)), ((13, 0), (16, 0)), ((16, 0), (19, 30))),
    5: (((7, 30), (10, 30)), ((13, 0), (16, 0)), ((16, 0), (19, 30))),
    6: (((8, 0), (11, 0)), ((16, 0), (19, 30))),
    7: (((7, 30), (10, 30)), ((15, 0), (18, 0)))
}


def etl_shift_schedule(file_name: str) -> pd.DataFrame:
    schedule_df = tabula.read_pdf(file_name, pages='all', pandas_options={'header': [1]}, lattice=True)
    schedule_df = schedule_df[(schedule_df.Volunteer != 'Volunteer')]  # Remove repeated header rows
    schedule_df = schedule_df.fillna(method='ffill')
    schedule_df = schedule_df[(schedule_df.Volunteer != 'Open')]
    return schedule_df


def set_level_indicator_vars(schedule_df: pd.DataFrame) -> pd.DataFrame:
    schedule_df['Blue'] = schedule_df.LEVEL.apply(lambda l: 'BLUE' in l.upper())
    schedule_df['Purple'] = schedule_df.LEVEL.apply(lambda l: 'PURPLE' in l.upper())
    return schedule_df


def transform_dates(schedule_df: pd.DataFrame) -> pd.DataFrame:
    schedule_df['Begin'] = schedule_df.apply(lambda l: re.sub(' \(.*\)', '', l['Date']) + ' ' + l['From'], axis=1)
    schedule_df['Start_Date'] = pd.to_datetime(schedule_df['Begin'], infer_datetime_format=True)
    schedule_df['End'] = schedule_df.apply(lambda l: re.sub(' \(.*\)', '', l['Date']) + ' ' + l['To'], axis=1)
    schedule_df['End_Date'] = pd.to_datetime(schedule_df['End'], infer_datetime_format=True)
    schedule_df = schedule_df.drop(['Begin', 'From', 'End'], axis=1)
    return schedule_df


def get_shift_counts(schedule_df: pd.DataFrame) -> pd.DataFrame:
    shifts_minimal = schedule_df[['Start_Date', 'End_Date', 'Blue', 'Purple']]
    shift_counts = shifts_minimal.groupby(['Start_Date', 'End_Date']).sum()
    return shift_counts


def apply_exceptions(schedule_df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply a hard coded group of exceptions to the schedule attributes
    Example: Remove from schedule persistent no-shows
    :param schedule_df: Current schedule
    :return: updated schedule dataframe with exceptions applied
    """
    return schedule_df


def color_need(value):
    high_need = value > 7
    highlight = 'color: red;font-weight: bold'
    return [highlight if h else '' for h in high_need]


def color_purples(value):
    high_need = value < 4
    highlight = 'color: purple;font-weight: bold'
    return [highlight if h else '' for h in high_need]


def get_shift_counts_as_html(shift_counts_df: pd.DataFrame) -> str:
    styles = [
        dict(selector="tr", props=[('text-align', 'right')]),
        dict(selector='th', props=[('text-align', 'right')])
    ]
    styled = shift_counts_df.style \
        .set_table_styles(styles) \
        .hide_index() \
        .apply(color_need, subset=['Need']) \
        .apply(color_purples, subset=['Purple'])

    return styled.render()


def format_shift_counts(assigned: pd.DataFrame) -> pd.DataFrame:
    a_df = pd.DataFrame(assigned.to_records())  # Flatten out multi index
    a_df['Date'] = a_df['shift'].apply(shift_date_str)
    a_df['Time'] = a_df['shift'].apply(shift_time_str)
    # Drop unneeded columns and reorder
    a_out = a_df[['Date', 'Time', 'Blue', 'Purple', 'Need']]
    return a_out


def load_and_summarize_counts(file_name: str) -> pd.DataFrame:
    shifts_df = etl_shift_schedule(file_name)
    shifts_df = set_level_indicator_vars(shifts_df)
    shifts_df.to_csv('./bad_data.csv')
    # print(shifts_df)
    shifts_df = apply_exceptions(shifts_df)
    shifts_df = transform_dates(shifts_df)
    return get_shift_counts(shifts_df)


def save_shift_counts_as_html(shift_counts_df: pd.DataFrame, output_file: str):
    html_text = get_shift_counts_as_html(shift_counts_df)
    with open(output_file, 'w') as html_out:
        html_out.write(html_text)


def save_shift_counts_as_csv(shift_counts_df: pd.DataFrame, output_file: str):
    shift_counts_df.to_csv(output_file, index=False)


def get_shift_schedule(for_date: date, start: tuple, end: tuple) -> tuple:
    hour, minute = start
    start_shift = datetime(for_date.year, for_date.month, for_date.day, hour, minute)
    hour, minute = end
    end_shift = datetime(for_date.year, for_date.month, for_date.day, hour, minute)
    return start_shift, end_shift


def generate_schedule(start_date: date, num_of_days=14):
    schedule = list()
    for day in range(num_of_days):
        curr_date = start_date + timedelta(day)
        shifts = shift_times[curr_date.isoweekday()]
        for shift in shifts:
            schedule.append(get_shift_schedule(curr_date, shift[0], shift[1]))
    return schedule


def is_within_timeframe(timeframe: Tuple[datetime, datetime], time: datetime):
    return timeframe[0] <= time <= timeframe[1]


def is_within_or_overlap(timeframe: Tuple[datetime, datetime], shift: Tuple[datetime, datetime]):
    return is_within_timeframe(timeframe, shift[0]) or is_within_timeframe(timeframe, shift[1])


def get_shift_overlap(timeframe: Tuple[datetime, datetime], shift: Tuple[datetime, datetime]) -> float:
    if not is_within_or_overlap(timeframe, shift):
        return 0.0

    shift_start, shift_end = shift
    tf_start, tf_end = timeframe
    in_start = max(shift_start, tf_start)
    in_end = min(shift_end, tf_end)
    tf_duration = tf_end - tf_start
    in_duration = in_end - in_start
    overlap = in_duration / tf_duration
    return overlap


def shift_date_str(shift: Tuple[datetime, datetime]) -> str:
    return shift[0].strftime('%a %-m/%-d')


def shift_time_str(shift: Tuple[datetime, datetime]) -> str:
    return '{} - {}'.format(shift[0].strftime('%-I:%M'), shift[1].strftime('%-I:%M %p'))


def assign_to_shift(shift_counts_df: pd.DataFrame, schedule: dict):
    # Create datafame for standard shifts
    assigned_counts = shift_counts_df.reset_index()
    assigned_counts['shift'] = assigned_counts.apply(
        lambda row: get_shift((row['Start_Date'], row['End_Date']), schedule), axis=1)
    assigned_counts = assigned_counts.groupby(['shift']).sum()
    assigned_counts['Need'] = assigned_counts.apply(lambda r: 15 - r['Blue'] - r['Purple'], axis=1)
    return assigned_counts


def get_shift(shift_time: tuple, schedule: list) -> tuple:
    for slot in schedule:
        if get_shift_overlap(shift_time, slot) >= .5:
            return slot
    else:
        return None


def assign_to_schedule(shift_counts: pd.DataFrame) -> pd.DataFrame:
    start = shift_counts.index[0][0]
    end = shift_counts.index[-1][0]
    num_days = (end - start).days + 1
    schedule = generate_schedule(start, num_days)
    return assign_to_shift(shift_counts, schedule)


def main():
    parser = ArgumentParser()
    parser.add_argument('filename', help='File containing DBS Shift report PDF', metavar='dbs_file')
    parser.add_argument('--html', help='Output as html', required=False, action='store_true')
    parser.add_argument('--csv', help='Output as csv', required=False, action='store_true')
    args = parser.parse_args()
    shift_counts_df = load_and_summarize_counts(args.filename)
    assigned = assign_to_schedule(shift_counts_df)
    assigned_fmt = format_shift_counts(assigned)
    output_html = args.html
    output_csv = args.csv
    if output_html:
        print('<h2>DBS Shift Counts</h2>')
        print(get_shift_counts_as_html(assigned_fmt))
    if output_csv:
        save_shift_counts_as_csv(assigned_fmt, 'DBS_Shift_Counts.csv')
    if not output_html and not output_csv:
        print('DBS Shift Counts')
        print(assigned_fmt)


if __name__ == '__main__':
    main()
