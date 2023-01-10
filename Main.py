import streamlit as st
import pandas as pd
import urllib.request
from urllib.error import HTTPError
from datetime import datetime
from datetime import timedelta
import pytz
import plotly.express as px


# sample link format https://storage.googleapis.com/tweeterssp-web-site-contents/2022-12-29-11-57-29227.jpg
class MainWebPage:
    def __init__(self, min_hr=6, max_hr=18, num_image_cols=5,
                 url_prefix='https://storage.googleapis.com/tweeterssp-web-site-contents/'):
        # set default values
        self.min_hr = min_hr
        self.max_hr = max_hr
        self.url_prefix = url_prefix
        self.num_image_cols = num_image_cols

        # load date range for web data, currently 3 days of data retained
        self.dates = []
        self.Tz = pytz.timezone("America/Chicago")  # localize time to current madison wi cst bird feeder
        self.dates.append(datetime.now(self.Tz).strftime('%Y-%m-%d'))
        self.dates.append((datetime.now(self.Tz) - timedelta(days=1)).strftime('%Y-%m-%d'))
        self.dates.append((datetime.now(self.Tz) - timedelta(days=2)).strftime('%Y-%m-%d'))

        # init vars
        self.df_occurrences = pd.DataFrame()
        self.df_msg_stream = pd.DataFrame()
        self.birds = []
        self.image_names = []
        self.feeders = []
        self.available_dates = self.dates
        self.last_gif_name = ''

    def load_message_stream(self):
        # build empty df
        df = pd.DataFrame(data=None, columns=['Unnamed: 0', 'Feeder Name', 'Event Num', 'Message Type',
                                              'Date Time', 'Message', 'Image Name'], dtype=None)
        for date in self.dates:
            try:  # read csvs from web, 3 days and concat
                urllib.request.urlretrieve(self.url_prefix + date + 'webstream.csv', 'webstream.csv')
                df_read = pd.read_csv('webstream.csv')
                df = pd.concat([df, df_read])
            except urllib.error.URLError as e:
                print(f'no web stream found for {date}')
                print(e)
                self.dates.remove(date)  # remove date if not found
                pass
        df['Date Time'] = pd.to_datetime(df['Date Time'])
        df = df.drop(['Unnamed: 0'], axis='columns')
        self.feeders = list(df['Feeder Name'].unique())
        self.feeders.append('default')  # add default feeder name in case one was not provided, need until 1/11 or 1/12
        return df.sort_values('Date Time', ascending=False)

    def load_bird_occurrences(self):
        cname_list = []
        df = pd.DataFrame(data=None, columns=['Unnamed: 0', 'Feeder Name', 'Species',
                                              'Date Time', 'Hour'], dtype=None)
        df['Common Name'] = cname_list
        df['Date Time'] = pd.to_datetime(df['Date Time'])
        for date in self.dates:
            try:  # read 3 days of files
                urllib.request.urlretrieve(self.url_prefix + date + 'web_occurrences.csv', 'web_occurrences.csv')
                df_read = pd.read_csv('web_occurrences.csv')
                df_read['Date Time'] = pd.to_datetime(df_read['Date Time'])
                df_read['Hour'] = pd.to_numeric(df_read['Date Time'].dt.strftime('%H')) + \
                    pd.to_numeric(df_read['Date Time'].dt.strftime('%M')) / 60
                df_read['Common Name'] = df_read['Species']
                df_read['Common Name'] = [name[name.find(' ') + 1:] if name.find(' ') >= 0 else name
                                          for name in df_read['Common Name']]
                df_read['Common Name'] = [name[name.find('(') + 1: name.find(')')] if name.find('(') >= 0 else name
                                          for name in df_read['Common Name']]
                df = pd.concat([df, df_read])
            except urllib.error.URLError as e:
                print(f'no web occurences found for {date}')
                print(e)
                self.dates.remove(date)  # remove date if not found
        df = df.drop(['Unnamed: 0'], axis='columns')
        return df

    def last_gif(self):
        last_name = ''
        search_str = '.gif'
        for file_name in self.image_names:
            if isinstance(file_name, str) and file_name.find(search_str) != -1:
                last_name = file_name
                break
        return last_name

    def publish_row_of_images(self, starting_col=0):
        try:  # catch error with less than X images for row
            cols = st.columns(self.num_image_cols)  # set web page with x number of images
            for col in range(0, self.num_image_cols):  # cols 0 to 5 for 5 columns
                try:  # catch missing image
                    # print(f'{self.url_prefix + self.image_names[col+starting_col]}')
                    urllib.request.urlretrieve(self.url_prefix + self.image_names[col+starting_col], 'imgfile')
                    # use alternative method below to open file to get animation instead of Pillow Image.open(url)
                    cols[col].image(self.url_prefix + self.image_names[col+starting_col], use_column_width=True,
                                    caption=f'{str(self.available_dates[col+starting_col])[str(self.available_dates[col+starting_col]).find(",") + 1:]} '
                                            f'Image: {self.image_names[col+starting_col]}')
                except FileNotFoundError:  # missing file
                    cols[col].write(f'missing file {self.image_names[col+starting_col]}')
                except Exception as e:  # missing file
                    print(self.image_names[col+starting_col])
                    print(e)
        except IndexError:  # less than x images for row skip the error
            pass
        except Exception as e:
            print(e)
        return

    def filter_occurences(self, feeder_options, date_options):
        df = self.df_occurrences
        df = df[df['Feeder Name'].isin(feeder_options)]
        df = df[df['Date Time'].dt.strftime('%Y-%m-%d').isin(date_options)]  # compare y m d to date selection y m d
        return df

    def filter_message_stream(self, feeder_options, date_options, message_options):
        df = self.df_msg_stream[self.df_msg_stream['Message Type'].isin(message_options)]
        df = df[df['Feeder Name'].isin(feeder_options)]
        df = df[df['Date Time'].dt.strftime('%Y-%m-%d').isin(date_options)]  # compare y m d to date selection y m d
        self.image_names = list(df["Image Name"])
        self.available_dates = list(df["Date Time"])
        self.last_gif_name = self.last_gif()  # uses self.image names
        return df

    def main_page(self):
        self.df_occurrences = self.load_bird_occurrences()  # test stream of bird occurrences for graph
        self.birds = self.df_occurrences['Common Name'].unique()
        self.df_msg_stream = self.load_message_stream()  # message stream from device

        # ****************** format page ********************
        st.set_page_config(layout="wide")
        st.header('Tweeters Web Page')

        # feeder multi select filters
        dropdown_cols = st.columns(2)
        with dropdown_cols[0]:
            feeder_options = st.multiselect('Feeders:', self.feeders, self.feeders)  # feeders available all selected
        with dropdown_cols[1]:
            date_options = st.multiselect('Dates:', self.dates, self.dates)  # dates available and all selected

        # text and graph
        st.write(f'Interactive Chart of Birds: {min(self.available_dates)} to {max(self.available_dates)}')
        fig1 = px.histogram(self.filter_occurences(feeder_options, date_options),
                            x="Hour", color='Common Name', range_x=[self.min_hr, self.max_hr],
                            nbins=36, width=650, height=400)
        fig1['layout']['xaxis'].update(autorange=True)
        st.write(fig1)  # write out figure to web

        # image and message stream multi-select filters
        message_options = st.multiselect(
            'Message Types:',
            ['possible', 'spotted', 'message'],
            ['spotted'])

        st.write(self.filter_message_stream(feeder_options, date_options, message_options))  # keep org stream

        # write last 10 images from stream
        st.write('Last Ten Images: Most Recent to Least Recent')
        self.publish_row_of_images(starting_col=0)  # row 1 of 5
        self.publish_row_of_images(starting_col=0 + self.num_image_cols)  # row 2 of 5

        return


# init class and call main page
webpage = MainWebPage()
webpage.main_page()
