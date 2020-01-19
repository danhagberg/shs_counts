import csv
import re
from argparse import ArgumentParser
from datetime import datetime

import numpy as np
import pandas as pd


def get_age_in_months(in_text):
    match = re.search(r'.*/(\d\d)y (\d\d)m', in_text, flags=re.IGNORECASE)
    age = match.groups() if match else ('0', '0')
    age_in_months = int(age[0]) * 12 + int(age[1])
    return age_in_months


def get_name(in_text):
    name = in_text.split(',')[0]
    name = name.split('-')[0]
    name = name.split('*')[0]
    return name


def get_weight(in_text):
    if len(in_text.strip()) > 0:
        weight = int(in_text.split()[0])
    else:
        weight = 0
    return weight


def get_level(row):
    level = row[4].split()[0].lower() if len(row[4]) > 0 else None
    if level in ['green', 'blue', 'purple', 'red', 'orange']:
        level = level.capitalize()
        if level == 'Red':
            if re.match(r'.*No Handling Level.*', row[5], re.IGNORECASE):
                level = 'Red - Default'
            elif re.match(r'.*Team.*', row[5], re.IGNORECASE):
                level = 'Red - Team'
    else:
        level = None
    return level


def extract_report_time(rpt_title):
    title_parts = rpt_title.split('-')
    rpt_time_str = title_parts[1].strip()
    rpt_time = datetime.strptime(rpt_time_str, '%m/%d/%Y %I:%M %p')
    return rpt_time


def get_dogs(file_loc):
    dogs = {}
    with open(file_loc, 'r') as dogs_csv:
        current_dog = None
        k_reader = csv.reader(dogs_csv)
        for row in k_reader:
            row = row[8:]
            if 'Dog Exercise List' in row[0]:
                report_time = extract_report_time(row[0])
            elif row[0] == 'AM':
                name = get_name(row[5])
                weight = get_weight(row[7])
                loc = row[3]
                age = get_age_in_months(row[6])
                id = row[8]
                current_dog = name
                dogs[current_dog] = {
                    'id': id,
                    'weight': weight,
                    'location': loc,
                    'age': age,
                    'holder': False,
                    'kc': False,
                    'bite': False,
                    'Level': None,
                    'team': False,
                    'diet': [],
                    'notes': []
                }
            elif row[0] == 'DIET':
                dogs[current_dog]['diet'].append(row[5])
            elif len(row) < 2:
                # End of dog notes
                current_dog = None
            elif re.match(r'(.*intake.*|.*incident.*)',
                          row[4],
                          flags=re.IGNORECASE):
                # Intake notes. Skip
                pass
            elif row[0] == 'H':
                dogs[current_dog]['holder'] = True
            elif 'Bite Quarantine' in row[4]:
                dogs[current_dog]['bite'] = True
            elif 'Kennel Cough' in row[4]:
                dogs[current_dog]['kc'] = True
            elif row[0] in ['RDR']:
                # Run dog run.  Skip
                pass
            else:
                level = get_level(row)
                if level:
                    dogs[current_dog]['Level'] = level if dogs[current_dog]['bite'] is False else 'Red - BQ'
                elif current_dog and len(row[5]) > 0:
                    dogs[current_dog]['notes'].append(row[5])

    dogs = {k: v for k, v in dogs.items() if 'DELETE' not in k}

    return dogs, report_time


def get_dog_counts_dataframe(dogs_df):
    aggFunc = {'Level': np.count_nonzero,
               'holder': sum,
               'kc': sum
               }

    dog_counts = dogs_df.groupby(['Level']).agg(aggFunc)

    dog_counts = dog_counts.rename(columns={'Level': 'All', 'holder': 'Holder', 'kc': 'KC'})
    dog_counts = dog_counts.astype('int32')

    row_total = dog_counts.sum()
    row_total.name = 'Total'
    dog_counts = dog_counts.append(row_total)
    return dog_counts


def get_dog_counts_as_html(dogs_df):
    dog_counts_df = get_dog_counts_dataframe(dogs_df)
    dc_out = dog_counts_df.rename(
        index={'Blue': '3 - Blue', 'Green': '2 - Green', 'Orange': '9 - Orange', 'Purple': '4 - Purple',
               'Red': '8 - Red', 'Red - BQ': '6 - Red - BQ', 'Red - Default': '7 - Red - Default',
               'Red - Team': '5 - Red - Team', 'Total': 'Total'}).sort_index()
    styles = [
        dict(selector="tr", props=[('text-align', 'right')]),
        dict(selector='th', props=[('text-align', 'right')])
    ]
    styled = dc_out.style.set_table_styles(styles)
    return styled.render()


def get_dog_info_as_html(dogs_df):
    return dogs_df[['holder', 'Level', 'location', 'kc', 'id']].rename_axis('name') \
        .sort_values(['holder', 'name'], ascending=[False, True]) \
        .to_html()


def get_dog_dataframe(dogs):
    dogs_df = pd.DataFrame.from_dict(dogs, orient='index')
    dogs_df['dbs'] = dogs_df.Level.apply(lambda l: l in ['Green', 'Blue', 'Purple', 'Red - Team'])
    return dogs_df


def filter_for_dbs(dogs_df):
    return dogs_df[(dogs_df['dbs'] == True)]


def filter_for_non_dbs(dogs_df):
    return dogs_df[(dogs_df['dbs'] == False)]


def main():
    parser = ArgumentParser()
    parser.add_argument('filename', help='File containing dog exercise csv', metavar='dog_file')
    parser.add_argument('--html', help='Output as html', required=False, action='store_true')
    args = parser.parse_args()
    dogs, report_time = get_dogs(args.filename)
    output_html = args.html
    dogs_df = get_dog_dataframe(dogs)
    if output_html:
        print(f"<h3>{datetime.strftime(report_time, '%A, %b %d, %Y at %I:%M %p ')}</h3>")
        print('<h2>DBS Dog Counts</h2>')
        print(get_dog_counts_as_html(filter_for_dbs(dogs_df)))
        print('<br><br>')
        print('<h2>Staff/BPA Dog Counts</h2>')
        print(get_dog_counts_as_html(filter_for_non_dbs(dogs_df)))
        print('<br><br>')
        print('<h2>Dog Locations</h2>')
        print(get_dog_info_as_html(dogs_df))
    else:
        print(datetime.strftime(report_time, '%A, %b %d, %Y at %I:%M %p '))
        print('DBS Dog Counts')
        print(get_dog_counts_dataframe(filter_for_dbs(dogs_df)))
        print('Staff/BPA Dog Counts')
        print(get_dog_counts_dataframe(filter_for_non_dbs(dogs_df)))


if __name__ == "__main__":
    main()
