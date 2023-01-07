import streamlit as st
import pandas as pd
from PIL import Image
import urllib.request
from datetime import datetime
from datetime import timedelta
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
        # build empty df
        date = self.dates[0]  # init dates field for except processing
        df = pd.DataFrame({
            'Unnamed: 0': pd.series(dtype='str'),
            'Feeder Name': pd.series(dtype='str'),
            'Event Num': pd.Series(dtype='int'),
            'Message Type': pd.Series(dtype='str'),
            'Date Time': pd.Series(dtype='str'),
            'Message': pd.Series(dtype='str'),
            'Image Name': pd.Series(dtype='str')})
        try:  # read csvs from web, 3 days and concat
            for date in self.dates:
                urllib.request.urlretrieve(self.url_prefix + date + 'webstream.csv', 'webstream.csv')
                df_read = pd.read_csv('webstream.csv')
                df = pd.concat([df, df_read])
        except FileNotFoundError:
            print(f'No web stream found for {date}')
            pass

        return df

    def load_bird_occurrences(self):
        date = datetime.now()  # init for error handling
        cname_list = []
        df = pd.DataFrame({
            'Unnamed: 0': pd.series(dtype='str'),
            'Feeder Name': pd.series(dtype='str'),
            'Species': pd.Series(dtype='str'),
            'Date Time': pd.Series(dtype='str'),
            'Hour': pd.Series(dtype='int')})
        df['Common Name'] = cname_list
        df['Date Time'] = pd.to_datetime(df['Date Time'])

        try:  # read 3 days of files
            for date in self.dates:
                urllib.request.urlretrieve(self.url_prefix + date + 'web_occurrences.csv', 'web_occurrences.csv')
                df_read = pd.read_csv('web_occurrences.csv')
                df_read['Date Time'] = pd.to_datetime(df_read['Date Time'])
                df_read['Hour'] = pd.to_numeric(df_read['Date Time'].dt.strftime('%H')) + \
                    pd.to_numeric(df_read['Date Time'].dt.strftime('%M')) / 60
                for sname in df_read['Species']:
                    sname = sname[sname.find(' ') + 1:] if sname.find(' ') >= 0 else sname  # remove index number
                    cname = sname[sname.find('(') + 1: sname.find(')')] if sname.find('(') >= 0 else sname  # common nme
                    cname_list.append(cname)
                df_read['Common Name'] = cname_list

                df = df.concat([df, df_read])
        except FileNotFoundError:
            print(f'no web occurences found for {date}')

        return df

    def last_gif(self):
        last_name = ''
        search_str = '.gif'
        for file_name in self.image_names:
            if isinstance(file_name, str) and file_name.find(search_str) != -1:
                last_name = file_name
                break
        return last_name

    def filter_message_stream(self, message_options, date_options):
        self.df_msg_stream = self.df_msg_stream[self.df_msg_stream['Message Type'].isin(message_options)]
        return self.df_msg_stream

    def publish_row_of_images(self, starting_col=0):
        try:  # catch error with less than X images for row
            cols = st.columns(self.num_image_cols)  # set web page with x number of images
            for col in range(0, self.num_image_cols):  # cols 0 to 5 for 5 columns
                try:  # catch missing image
                    urllib.request.urlretrieve(self.url_prefix + self.image_names[col+starting_col], 'imgfile')
                    img = Image.open('imgfile')
                    cols[col].image(img, use_column_width=True,
                                    caption=f'Time: {self.dates[col][self.dates[col].find(",") + 1:]} '
                                            f'Image: {self.image_names[col+starting_col]}')
                except Exception as e:  # missing file
                    cols[col].write(f'missing file {self.image_names[col+starting_col]}')
                    print(self.image_names[col+starting_col])
                    print(e)
        except Exception as e:
            print(e)
        return

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
        date_options = st.multiselect(
            'Dates:', self.dates, self.dates)  # dates available and all selected

        message_options = st.multiselect(
            'Message Types:',
            ['possible', 'spotted', 'message'],
            ['spotted'])

        # write out contents of prediction stream
        self.df_msg_stream = self.filter_message_stream(message_options, date_options)
        self.image_names = list(self.df_msg_stream["Image Name"])
        self.available_dates = list(self.df_msg_stream["Date Time"])
        self.last_gif_name = self.last_gif()
        st.write(self.df_msg_stream)  # write out message table to web

        # write last 10 images from stream
        st.write('Last Ten Images: Most Recent to Least Recent')
        self.publish_row_of_images(starting_col=0)  # row 1 of 5
        self.publish_row_of_images(starting_col=0 + self.num_image_cols)  # row 2 of 5
        # try:
        #     # row 2 of images
        #     cols = st.columns(5)
        #     for col in range(0, 5):  # cols 0 to 4
        #         # cols[col].subheader(f'{DATES[col+5][DATES[col+5].find(",")+1:]}')
        #         try:  # catch missing image
        #             urllib.request.urlretrieve(self.url_prefix + self.image_names[col + 5], 'imgfile')
        #             img = Image.open('imgfile')
        #             cols[col].image(img, use_column_width=True,
        #                             caption=f'Time: {self.dates[col][self.dates[col].find(",") + 1:]} '
        #                                     f'Image: {self.image_names[col + 5]}')
        #         except Exception as e:  # likely missing file
        #             cols[col].write(f'Missing file {self.image_names[col + 5]}')
        #             print(self.image_names[col + 5])
        #             print(e)
        # except IndexError:
        #     pass  # web hasn't generated enough files to file all 10 spots
        # except Exception as e:
        #     print(e)
        #     pass

        return


# init class and call main page
webpage = MainWebPage()
webpage.main_page()
