import re
from argparse import ArgumentParser
from datetime import date, datetime, timedelta
from typing import Tuple, List
import shift_exceptions as exceptions

import pandas as pd
import tabula


def transform_dce_dates(schedule_df: pd.DataFrame) -> pd.DataFrame:
    schedule_df['Begin'] = schedule_df.apply(lambda l: l['Date'] + ' ' + l['From time'], axis=1)
    schedule_df['Start_Date'] = pd.to_datetime(schedule_df['Begin'], infer_datetime_format=True)
    schedule_df['End'] = schedule_df.apply(lambda l: l['Date'] + ' ' + l['To time'], axis=1)
    schedule_df['End_Date'] = pd.to_datetime(schedule_df['End'], infer_datetime_format=True)
    schedule_df = schedule_df.drop(['Date', 'Begin', 'End', 'From time', 'To time'], axis=1)
    return schedule_df


def get_dce_shift_counts(schedule_df: pd.DataFrame) -> pd.DataFrame:
    shifts_minimal = schedule_df[['Start_Date', 'End_Date', 'Level']]
    shift_counts = shifts_minimal.groupby(['Start_Date', 'End_Date']).count()
    shift_counts.rename(columns={'Level': 'Green'}, inplace=True)
    return shift_counts


def load_and_summarize_dce_counts(file_name: str) -> pd.DataFrame:
    # Load level by name data
    dces = pd.read_excel(file_name, sheet_name=0)
    greens = dces[dces.LEVEL == 'GREEN-D']
    greens = greens.rename(columns={'First name Last name': 'Full Name', 'LEVEL': 'Level'})
    greens.set_index('Full Name', inplace=True)

    # Load the shift by name data
    sched = pd.read_excel(file_name, sheet_name=1)
    sched['Full Name'] = sched['First name'] + ' ' + sched['Last name']
    sched = sched.drop(columns=['First name', 'Last name', 'Note', 'Number'])
    sched.set_index('Full Name', inplace=True)

    # Add shift data for all Green DCEs
    greens_shift_df = greens.merge(left_on='Full Name', right=sched, right_on='Full Name')
    greens_shift_df = transform_dce_dates(greens_shift_df)

    return get_dce_shift_counts(greens_shift_df)
