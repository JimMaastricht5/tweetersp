import streamlit as st
import pandas as pd
from PIL import Image
import urllib.request
from datetime import datetime
from datetime import timedelta
import plotly.express as px


# sample link format https://storage.googleapis.com/tweeterssp-web-site-contents/2022-12-29-11-57-29227.jpg
class MainWebPage:
    def __init__(self, min_hr=6, max_hr=18, url_prefix='https://storage.googleapis.com/tweeterssp-web-site-contents/'):
        # set default values
        self.min_hr = min_hr
        self.max_hr = max_hr
        self.url_prefix = url_prefix

        # load date range for web data, currently 3 days of data retained
        self.dates = []
        self.dates.append(datetime.now().strftime('%Y-%m-%d'))
        self.dates.append((datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'))
        self.dates.append((datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d'))

        # init vars
        self.df_occurrences = pd.DataFrame()
        self.df_msg_stream = pd.DataFrame()
        self.birds = []
        self.image_names = []
        self.available_dates = []
        self.last_gif_name = ''

    def load_message_stream(self):
        try:
            urllib.request.urlretrieve(self.url_prefix + self.dates[0]+'webstream.csv', 'webstream.csv')
            df = pd.read_csv('webstream.csv')
            df = df[df['Event Num'] != 0]

            df = df.drop(['Unnamed: 0', 'Feeder Name'], axis="columns")
            df = df.reset_index(drop=True)
            df = df.sort_values(by='Date Time', ascending=False)
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

    def load_bird_occurrences(self):
        cname_list = []
        try:
            urllib.request.urlretrieve(self.url_prefix + self.dates[0] + 'web_occurrences.csv', 'web_occurrences.csv')
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

    def last_gif(self):
        last_name = ''
        search_str = '.gif'
        for file_name in self.image_names:
            if isinstance(file_name, str) and file_name.find(search_str) != -1:
                last_name = file_name
                break
        return last_name

    def filter_message_stream(self, df_msgs):
        df = df_msgs[df_msgs['Message Type'].isin(self.message_options)]
        return df

    def main_page(self):
        self.df_occurrences = self.load_bird_occurrences()  # test stream of bird occurrences for graph
        self.birds = self.df_occurrences['Common Name'].unique()
        self.df_msg_stream = self.load_message_stream()  # message stream from device

        # ****************** format page ********************
        st.header('Tweeters Web Page')

        # text and graph
        st.write(f'Interactive Chart: Birds Spotted as of {self.dates[0]}')
        fig1 = px.histogram(self.df_occurrences, x="Hour", color='Common Name', range_x=[self.min_hr, self.max_hr],
                            nbins=36, width=650, height=300)
        fig1['layout']['xaxis'].update(autorange=True)
        st.write(fig1)  # write out figure to web

        # multi select filters
        self.message_options = st.multiselect(
            'Message Types:',
            ['possible', 'spotted', 'message'],
            ['spotted'])

        # write out contents of prediction stream
        self.df_msg_stream = self.filter_message_stream(self.df_msg_stream)
        self.image_names = list(self.df_msg_stream["Image Name"])
        self.available_dates = list(self.df_msg_stream["Date Time"])
        self.last_gif_name = self.last_gif()
        st.write(self.df_msg_stream)  # write out message table to web

        # write last 10 images from stream
        st.write('Last Ten Images: Most Recent to Least Recent')
        try:  # catch error with less than 10 images for a day
            cols = st.columns(5)
            for col in range(0, 5):  # cols 0 to 4
                # cols[col].subheader(f'{DATES[col][DATES[col].find(",")+1:]}')
                try:  # catch missing image
                    urllib.request.urlretrieve(self.url_prefix + self.image_names[col], 'imgfile')
                    img = Image.open('imgfile')
                    cols[col].image(img, use_column_width=True,
                                    caption=f'Time: {self.dates[col][self.dates[col].find(",") + 1:]} '
                                            f'Image: {self.image_names[col]}')
                except Exception as e:  # likely missing file
                    cols[col].write(f'Missing file {self.image_names[col]}')
                    print(self.image_names[col])
                    print(e)

            # row 2 of images
            cols = st.columns(5)
            for col in range(0, 5):  # cols 0 to 4
                # cols[col].subheader(f'{DATES[col+5][DATES[col+5].find(",")+1:]}')
                try:  # catch missing image
                    urllib.request.urlretrieve(self.url_prefix + self.image_names[col + 5], 'imgfile')
                    img = Image.open('imgfile')
                    cols[col].image(img, use_column_width=True,
                                    caption=f'Time: {self.dates[col][self.dates[col].find(",") + 1:]} '
                                            f'Image: {self.image_names[col + 5]}')
                except Exception as e:  # likely missing file
                    cols[col].write(f'Missing file {self.image_names[col + 5]}')
                    print(self.image_names[col + 5])
                    print(e)
        except IndexError:
            pass  # web hasn't generated enough files to file all 10 spots
        except Exception as e:
            print(e)
            pass

        return


# init class and call main page
webpage = MainWebPage()
webpage.main_page()
