import streamlit as st
import pandas as pd
from PIL import Image
import urllib.request
from datetime import datetime
import plotly.express as px


def load_message_stream(min_hr=6, max_hr=18, ):
    # https://storage.googleapis.com/tweeterssp-web-site-contents/2022-12-29-11-57-29227.jpg
    try:
        urllib.request.urlretrieve(URL_PREFIX + DATES[0]+'webstream.csv', 'webstream.csv')
        df = pd.read_csv('webstream.csv')
        df = df[df['Event Num'] != 0]

        df = df.drop(['Unnamed: 0', 'Feeder Name'], axis="columns")
        df = df.reset_index(drop=True)
        df = df.sort_values(by='Date Time', ascending=False)
        # df = df
    except FileNotFoundError:
        print('No web stream found, creating empty stream')
        df = pd.DataFrame({
            # 'Feeder Name': pd.series(dtype='str'),
            'Event Num': pd.Series(dtype='int'),
            # 'Message Type': pd.Series(dtype='str'),
            'Date Time': pd.Series(dtype='str'),
            'Message': pd.Series(dtype='str'),
            'Image Name': pd.Series(dtype='str')})
        pass
    return df


def load_bird_occurrences():
    cname_list = []
    try:
        urllib.request.urlretrieve(URL_PREFIX + DATES[0] + 'web_occurrences.csv', 'web_occurrences.csv')
        df = pd.read_csv('web_occurrences.csv')
        df['Date Time'] = pd.to_datetime(df['Date Time'])
        df['Hour'] = pd.to_numeric(df['Date Time'].dt.strftime('%H')) + \
            pd.to_numeric(df['Date Time'].dt.strftime('%M')) / 60
        for sname in df['Species']:
            sname = sname[sname.find(' ') + 1:] if sname.find(' ') >= 0 else sname  # remove index number
            cname = sname[sname.find('(') + 1: sname.find(')')] if sname.find('(') >= 0 else sname  # common name
            cname_list.append(cname)
        df['Common Name'] = cname_list
    except FileNotFoundError:
        print('no web occurences found, loading empty occurences')
        df = pd.DataFrame({
            'Species': pd.Series(dtype='str'),
            'Date Time': pd.Series(dtype='str'),
            'Hour': pd.Series(dtype='int')})
        df['Common Name'] = cname_list  # null list
    return df


def find_last(file_name_list, search_str):
    last_name = ''
    for file_name in file_name_list:
        if isinstance(file_name, str) and file_name.find(search_str) != -1:
            last_name = file_name
            break
    return last_name


def filter_message_stream(df, message_options):
    df = df[df['Message Type'].isin(message_options)]
    return df

# ******************** start main app *****************
URL_PREFIX = 'https://storage.googleapis.com/tweeterssp-web-site-contents/'
DATES = []
DATES.append(datetime.now().strftime('%Y-%m-%d'))

DF = load_bird_occurrences()  # test stream of bird occurrences for graph
BIRDS = DF['Common Name'].unique()
DF_STREAM = load_message_stream(BIRDS)  # message stream from device


MIN_HR = 6
MAX_HR = 18

# ****************** format page ********************
st.header('Tweeters Web Page')

st.write(f'Interactive Chart: Birds Spotted as of {DATES[0]}')
fig1 = px.histogram(DF, x="Hour", color='Common Name', range_x=[MIN_HR, MAX_HR], nbins=36, width=650, height=300)
fig1['layout']['xaxis'].update(autorange = True)
fig1

# write out contents of prediction stream
message_options = st.multiselect(
    'Message Types:',
    ['possible', 'spotted', 'message'],
    ['spotted'])

DF_STREAM = filter_message_stream(DF_STREAM, message_options)
IMAGE_NAMES = list(DF_STREAM["Image Name"])
DATES = list(DF_STREAM["Date Time"])
LAST_GIF_NAME = find_last(IMAGE_NAMES, '.gif')
DF_STREAM

# write last 10 images from stream
st.write('Last Ten Images: Most Recent to Least Recent')
try:  # catch error with less than 10 images for a day
    cols = st.columns(5)
    for col in range(0, 5):  # cols 0 to 4
        # cols[col].subheader(f'{DATES[col][DATES[col].find(",")+1:]}')
        try:  # catch missing image
            urllib.request.urlretrieve(URL_PREFIX + IMAGE_NAMES[col], 'imgfile')
            img = Image.open('imgfile')
            cols[col].image(img, use_column_width=True,
                            caption=f'Time: {DATES[col][DATES[col].find(",")+1:]} '
                                    f'Image: {IMAGE_NAMES[col]}')
        except Exception as e:  # likely missing file
            cols[col].write(f'Missing file {IMAGE_NAMES[col]}')
            print(IMAGE_NAMES[col])
            print(e)

    # row 2 of images
    cols = st.columns(5)
    for col in range(0, 5):  # cols 0 to 4
        # cols[col].subheader(f'{DATES[col+5][DATES[col+5].find(",")+1:]}')
        try:  # catch missing image
            urllib.request.urlretrieve(URL_PREFIX + IMAGE_NAMES[col+5], 'imgfile')
            img = Image.open('imgfile')
            cols[col].image(img, use_column_width=True, caption=f'Time: {DATES[col][DATES[col].find(",")+1:]} '
                                    f'Image: {IMAGE_NAMES[col+5]}')
        except Exception as e:  # likely missing file
            cols[col].write(f'Missing file {IMAGE_NAMES[col+5]}')
            print(IMAGE_NAMES[col+5])
            print(e)
except Exception as e:
    pass