# MIT License
#
# 2024 Jim Maastricht
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# JimMaastricht5@gmail.com
# module controls all of the data handling and web page generation for the tweeters web app
# individual pages create the class and call the corresponding function to generate the page output
import pandas
import streamlit as st
import pandas as pd
import urllib.request
from urllib.error import HTTPError
from datetime import datetime
from datetime import timedelta
import pytz
import plotly.express as px
from plotly.express import colors
from st_aggrid import GridOptionsBuilder, AgGrid, GridUpdateMode, DataReturnMode

# list of birds to exclude that prior model displayed and are not valid results
FILTER_BIRD_NAMES = ['Rock Pigeon', 'Pine Grosbeak', 'Indigo Bunting', 'Eurasian Collared-Dove',
                     'White-crowned Sparrow', 'Lark Sparrow', 'Chipping Sparrow', 'Pine Siskin',
                     'Vesper Sparrow', 'White-throated Sparrow', 'Common Ground-Dove',
                     'Cedar Waxwing', "Lincoln's Sparrow", 'Evening Grosbeak', 'American Tree Sparrow',
                     "Harris's Sparrow", 'Field Sparrow']
# sample link format https://storage.googleapis.com/tweeterssp-web-site-contents/2022-12-29-11-57-29227.jpg


class WebPages:
    def __init__(self, min_hr: int = 6, max_hr: int = 18, num_image_cols: int = 5,
                 url_prefix: str = 'https://storage.googleapis.com/tweeterssp-web-site-contents/') -> None:
        """
        set up class to handle the creation of all the web pages along with the data
        :param min_hr: minimum hour value to display on chart
        :param max_hr: max hour value to display on chart.  0 to 24
        :param num_image_cols: number of cols to display in a row on the web page
        :param url_prefix: url prefix to retrieve contents from Google storage
        :return: None
        """
        # set default values
        self.min_hr = min_hr
        self.max_hr = max_hr
        self.url_prefix = url_prefix
        self.num_image_cols = num_image_cols
        # load date range for web data, currently 3 days of data retained
        self.dates = []
        self.Tz = pytz.timezone("America/Chicago")  # localize time to current madison wi cst bird feeder
        # grab today's date along with the two prior for the drop-down date list selector
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
        # self.last_gif_name = ''
        self.bird_color_map = {}
        self.common_names = []
        return

    def build_common_name(self, df: pandas.DataFrame, target_col: str) -> pandas.DataFrame:
        """
        builds common names for the birds from a target col, sets a common color palette for use in graphing
        across days, e.g., finches are always a yellow bar
        :param df: dataframe containing the data to parse
        :param target_col: column name to extract the common names from
        :return: new dataframe with common name column
        """
        df['Common Name'] = df[target_col]
        df['Common Name'] = [name[name.find(' ') + 1:] if name.find(' ') >= 0 else name
                             for name in df['Common Name']]
        df['Common Name'] = [name[name.find('(') + 1: name.find(')')] if name.find('(') >= 0 else name
                             for name in df['Common Name']]
        # build color map so each chart uses the same color for each species
        self.common_names = sorted(df['Common Name'].unique())
        self.common_names = [name for name in self.common_names if name not in FILTER_BIRD_NAMES]
        color_palette = colors.sequential.Viridis
        self.bird_color_map = dict(zip(self.common_names, color_palette))
        return df

    # @st.cache_data
    def load_message_stream(self) -> pandas.DataFrame:
        """
        builds an empty data frame, reads for csv for each date and merges them into on df
        :return: returns a dataframe with all messages for each day requested
        """
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
        df = self.build_common_name(df, 'Message')
        df = df.drop(['Unnamed: 0'], axis='columns')
        # reorder df
        new_col_order = ['Date Time', 'Common Name', 'Message', 'Feeder Name', 'Event Num', 'Message Type',
                         'Image Name']
        df = df.reindex(columns=new_col_order)
        self.feeders = list(df['Feeder Name'].unique())
        return df.sort_values('Date Time', ascending=False)

    # @st.cache_data
    def load_bird_occurrences(self, drop_old_model_species: bool = True) -> pandas.DataFrame:
        """
        setup df with birds spotted
        :param drop_old_model_species:
        :return: data frame with birds the feeder has seen
        """
        # setup df like file
        df = pd.DataFrame(data=None, columns=['Unnamed: 0', 'Feeder Name', 'Species',
                                              'Date Time', 'Hour'], dtype=None)
        df['Date Time'] = pd.to_datetime(df['Date Time'])
        for date in self.dates:
            try:  # read 3 days of files
                urllib.request.urlretrieve(self.url_prefix + date + 'web_occurrences.csv', 'web_occurrences.csv')
                df_read = pd.read_csv('web_occurrences.csv')
                df_read['Date Time'] = pd.to_datetime(df_read['Date Time'])
                df_read['Hour'] = pd.to_numeric(df_read['Date Time'].dt.strftime('%H')) + \
                    pd.to_numeric(df_read['Date Time'].dt.strftime('%M')) / 60
                df_read['Day.Hour'] = pd.to_numeric(df_read['Date Time'].dt.strftime('%d')) + \
                    pd.to_numeric(df_read['Date Time'].dt.strftime('%H')) / 100 + \
                    pd.to_numeric(df_read['Date Time'].dt.strftime('%M')) / 100 / 60
                df = pd.concat([df, df_read])
            except urllib.error.URLError as e:
                print(f'no web occurrences found for {date}')
                print(e)
                self.dates.remove(date)  # remove date if not found
        df = self.build_common_name(df, 'Species')  # build common name for merged df
        df = df.drop(['Unnamed: 0'], axis='columns')
        if drop_old_model_species:  # the old model made pred errors, this filter drops the more obvious errors
            df = df[~df['Common Name'].isin(FILTER_BIRD_NAMES)]  # get rid of species from old model
        return df

    def load_daily_history(self, drop_old_model_species: bool = True) -> pandas.DataFrame:
        """
        loads the history for all days and months with summarized counts by day
        :param drop_old_model_species:
        :return: df with daily history for line graph
        """
        df = None
        try:
            urllib.request.urlretrieve(self.url_prefix + 'daily_history.csv', 'daily_history.csv')
            df = pd.read_csv('daily_history.csv')
            df = df.drop(['Unnamed: 0'], axis='columns')
            df["Day_of_Year"] = df["Month"] * 30 + df["Day"]  # df["Year"] * 365
            if drop_old_model_species:
                df = df[~df['Common Name'].isin(FILTER_BIRD_NAMES)]  # get rid of species from old model
        except urllib.error.URLError as e:
            print(f'no daily history')
            print(e)
        return df

    def set_caption(self, current_image_num: int) -> str:
        """
        pulls the image file name and parses the name for the date and times, formats a string
        :param current_image_num: image offset in list to build caption for
        :return: the caption for this image
        """
        image_name = self.image_names[current_image_num]
        image_date_time = image_name[0:image_name.find('(')]
        image_date = image_date_time[5:7] + '/' + image_date_time[8:10] + '/' + image_date_time[0:4]
        image_time = image_date_time[11:-6].replace('-', ':')
        caption = f'date: {image_date}  time: {image_time}'
        return caption

    def publish_row_of_images(self, starting_col: int = 0) -> None:
        """
        publish a row of images with a set number of images per row in num_image_cols
        :param starting_col: starting position in list
        :return: None
        """
        try:  # catch error with less than X images for row
            cols = st.columns(self.num_image_cols)  # set web page with x number of images
            for col in range(0, self.num_image_cols):  # cols 0 to 5 for 5 columns
                try:  # catch missing image
                    urllib.request.urlretrieve(self.url_prefix + self.image_names[col+starting_col], 'imgfile')
                    # use alternative method below to open file to get animation instead of Pillow Image.open(url)
                    with cols[col]:
                        st.image(self.url_prefix + self.image_names[col+starting_col], use_column_width=True,
                                 caption=self.set_caption(starting_col+col))
                        st.write(f'{self.url_prefix + self.image_names[col+starting_col]}', unsafe_allow_html=True)
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

    def publish_first_image(self) -> None:
        """
        publishes the first image in the list to the web
        :return: None
        """
        for image_name in self.image_names:
            if image_name != '' and image_name != "<NA>":
                try:
                    urllib.request.urlretrieve(self.url_prefix + image_name, 'imgfile')
                    st.image(self.url_prefix + image_name, caption=f'Seed Check Image: {image_name}')
                    return  # only need the first image, fall out of function
                except FileNotFoundError:  # missing file
                    st.write(f'missing file {image_name}')
                except Exception as e:  # missing file
                    print(image_name)
                    print(e)
        return

    def filter_occurrences(self, feeder_options: list, date_options: list, bird_options: list) -> pandas.DataFrame:
        """
        filter down the bird occurrences df to include the desired selections
        :param feeder_options: which feeders to include in output
        :param date_options: which dates to include in output
        :param bird_options: which birds to include in output
        :return: df with filtered list of data
        """
        df = self.df_occurrences
        df = df[df['Feeder Name'].isin(feeder_options)]
        df = df[df['Date Time'].dt.strftime('%Y-%m-%d').isin(date_options)]  # compare y m d to date selection y m d
        if len(bird_options) > 0:
            df = df[df['Common Name'].isin(bird_options)]  # return birds if none selected
        return df

    def filter_message_stream(self, feeder_options: list, date_options: list, bird_options: list,
                              message_options: list) -> pandas.DataFrame:
        """
        filter the message stream to include the desired selections
        :param feeder_options: which feeders to include in output
        :param date_options: which dates to include in output
        :param bird_options: which birds to include in output
        :param message_options: which message types to include in ouput
        :return: filtered df
        """
        df = self.df_msg_stream[self.df_msg_stream['Message Type'].isin(message_options)]
        df = df[df['Feeder Name'].isin(feeder_options)]
        df = df[df['Date Time'].dt.strftime('%Y-%m-%d').isin(date_options)]  # compare y m d to date selection y m d
        if len(bird_options) > 0:
            df = df[df['Common Name'].isin(bird_options)]  # return all birds if none selected
        self.image_names = list(df["Image Name"])
        self.available_dates = list(df["Date Time"])
        # df = df['Image Link'] = self.url_prefix + df['Image Name']
        # self.last_gif_name = self.last_gif()  # uses self.image names
        return df

    # static page functions ######
    def main_page(self) -> None:
        """
        Renders the main page of the website
        :return: None
        """
        self.df_occurrences = self.load_bird_occurrences()  # test stream of bird occurrences for graph
        self.birds = self.df_occurrences['Common Name'].unique()
        self.df_msg_stream = self.load_message_stream()  # message stream from device
        # ****************** format page ********************
        st.set_page_config(layout="wide")
        st.header('Tweeters Web Page')
        # feeder multi select filters with expander
        with st.expander("Filters for Feeder, Dates, and Birds:"):
            st.write('Select values to include or exclude in the chart and information table.  '
                     'Empty list of birds is "all" birds.')
            dropdown_cols = st.columns(3)
            with dropdown_cols[0]:
                feeder_options = st.multiselect('Feeders:', self.feeders, self.feeders)  # feeders all selected
            with dropdown_cols[1]:   # dates available and first selected
                if len(self.dates) > 0:
                    date_options = st.multiselect('Dates:', self.dates, self.dates[0])
            with dropdown_cols[2]:
                bird_options = st.multiselect('Birds:', self.birds, [])  # all birds common names none selected
        # check for no data available
        if len(self.dates) == 0:
            st.write(f'Interactive Chart of Birds: No Data Available')
            return

        # data available text and graph
        st.write(f'Interactive Chart of Birds: {min(self.available_dates)} to {max(self.available_dates)}')
        # multi-day
        fig2 = px.histogram(self.filter_occurrences(feeder_options, date_options, bird_options),
                            x="Date Time", color='Common Name',
                            nbins=36, width=650, height=400,
                            color_discrete_map=self.bird_color_map,
                            category_orders={'Common Name': self.common_names})
        fig2['layout']['xaxis'].update(autorange=True)
        st.plotly_chart(fig2, use_container_width=True, sharing="streamlit", theme="streamlit")

        # image and message stream multi-select filters
        message_options = st.multiselect(
            'Prediction Certainty: \n "spotted" includes all of the observations above the confidence '
            'threshold of the model. "possible" includes the observations below the threshold',
            ['possible', 'spotted'],  # remove message type and display on own page later
            ['spotted'])

        st.dataframe(data=self.filter_message_stream(feeder_options, date_options, bird_options, message_options),
                     use_container_width=True, hide_index=True,
                     column_config={'Image Link': st.column_config.LinkColumn("Image Link", help='', max_chars=100,)})

        # write last 10 images from stream
        st.write('Last 25 Images: Most Recent to Least Recent')
        self.publish_row_of_images(starting_col=0)  # col 1 of 5
        self.publish_row_of_images(starting_col=(0 + self.num_image_cols))  # row 2 of 5 cols starts num_image_cols
        self.publish_row_of_images(starting_col=(self.num_image_cols * 2))  # row 3 of 5 cols starts num_image_cols * 2
        self.publish_row_of_images(starting_col=(self.num_image_cols * 3))  # row 4 of 5 cols starts num_image_cols * 3
        self.publish_row_of_images(starting_col=(self.num_image_cols * 4))  # row 5 of 5 cols starts num_image_cols * 5
        return

    def daily_charts_page(self) -> None:
        """
        renders the daily charts pages, display a bar chart of birds seen by hour for the selected days
        :return: None
        """
        self.df_occurrences = self.load_bird_occurrences()  # test stream of bird occurrences for graph
        self.birds = self.df_occurrences['Common Name'].unique()
        self.df_msg_stream = self.load_message_stream()  # message stream from device

        # ****************** format page ********************
        st.set_page_config(layout="wide")
        st.header('Tweeters Web Page: Daily Charts')

        # feeder multi select filters with expander
        with st.expander("Filters for Feeder, Dates, and Birds:"):
            st.write('Select values to include or exclude in the chart and information table.  '
                     'Empty list of birds is "all" birds.')
            dropdown_cols = st.columns(1)
            with dropdown_cols[0]:
                feeder_options = st.multiselect('Feeders:', self.feeders, self.feeders)  # feeders all selected

        # text and graph for a single day
        for date in self.available_dates:
            st.write(f'Interactive Chart of Birds: {date}')
            fig1 = px.histogram(self.filter_occurrences(feeder_options, [date], self.birds),
                                x="Hour", color='Common Name', range_x=[self.min_hr, self.max_hr],
                                nbins=36, width=650, height=400,
                                color_discrete_map=self.bird_color_map,
                                category_orders={'Common Name': self.common_names})
            fig1['layout']['xaxis'].update(autorange=True)
            st.plotly_chart(fig1, use_container_width=True, sharing="streamlit", theme="streamlit")

        return

    def daily_trends_page(self, filter_birds_cnt: int = 1) -> None:
        """
        creates the daily trends page, shows aggregated daily counts since inception on May 9th 2023
        :param filter_birds_cnt: min number of occurrences of bird to be displayed.  must be > 1 per the default
        :return: None
        """
        st.set_page_config(layout="wide")
        st.header(f'Daily History - May 9th 2023 to Present.  May 9th was day 159.  '
                  f'Dates in 2024 are presented as the day of the year + 365.')
        df = self.load_daily_history()
        df = df[df['counts'] > filter_birds_cnt]
        df['Year-Day'] = (df['Year'] - 2023) * 365 + df['Day_of_Year']
        st.write(f'Trend of Bird Visits by Day.  Data started being retained on May 9th 2023.')
        fig1 = px.line(data_frame=df, x="Year-Day", y="counts", color='Common Name', width=650, height=800,
                       color_discrete_map=self.bird_color_map,
                       category_orders={'Common Name': self.common_names})
        fig1['layout']['xaxis'].update(autorange=True)
        st.plotly_chart(fig1, use_container_width=True, sharing="streamlit", theme="streamlit")

        gb = GridOptionsBuilder.from_dataframe(df)
        gb.configure_pagination(paginationPageSize=50)  # Add pagination
        gb.configure_default_column(enablePivot=False, enableValue=False, enableRowGroup=False)
        gb.configure_side_bar()
        gridoptions = gb.build()

        _ = AgGrid(
            df,
            gridOptions=gridoptions,
            enable_enterprise_modules=True,
            update_mode=GridUpdateMode.MODEL_CHANGED,
            data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
            fit_columns_on_grid_load=False,
            header_checkbox_selection_filtered_only=True,
            # height=250,  # using height breaks multipage view
            use_checkbox=True
        )
        return

    def messages_page(self) -> None:
        """
        formats the messages page
        :return: None
        """
        self.df_msg_stream = self.load_message_stream()  # message stream from device
        # ****************** format page ********************
        st.set_page_config(layout="wide")
        st.header('Tweeters Web Page: Feeder Messages')
        # feeder multi select filters
        dropdown_cols = st.columns(2)
        with dropdown_cols[0]:
            feeder_options = st.multiselect('Feeders:', self.feeders, self.feeders)  # feeders available all selected
        with dropdown_cols[1]:
            date_options = st.multiselect('Dates:', self.dates, self.dates)  # dates available and all selected

        st.dataframe(data=self.filter_message_stream(feeder_options=feeder_options, date_options=date_options,
                                                     bird_options=[],
                                                     message_options=['message']).sort_values('Date Time',
                                                                                              ascending=True),
                     use_container_width=True)
        self.publish_first_image()  # just want one image
        return

    def about_page(self) -> None:
        """
        formats the about page that describes the app and the site
        :return: None
        """
        st.write('About Page')
        st.write(f'This site display data for the the days from '
                 f'{min(self.available_dates)} to {max(self.available_dates)}')
        st.write(f'Data is sent from a rasp pi 4 running custom motion detection and image recognition software. '
                 f'At sunrise an initial image is taken at the feeder.  The delta from this initial image is what the '
                 f'software uses to detect motion.  Once motion is detected a google Tensorflow object detection model '
                 f'is run to determine objects in the image.  If a bird is detected a second Tensorflow model is run '
                 f'to determine the species.  The species model detects 999 species, but the software provides feeder '
                 f'software provides the ability to exclude species, e.g., European Swallow that do not appear in '
                 f'the area.  '
                 f'\n'
                 f'Once a species is observed with a confidence above the threshold the feeder send a jpg to the cloud '
                 f'and takes a quick series '
                 f'of images to build an animated gif.  Species detection is run for each frame.  If there are enough '
                 f'frames an animated gif is written to the cloud.'
                 f'Select images are displayed on Twitter uses another algorithm to avoid tweeting out '
                 f'common species to frequently.  All images are available on this web site for three days.')
        st.write(f'Feel free to use any of the images you see on the site.  The code is publicly available and I am '
                 f'always happy to work with others to improve the feeder or web site.  ')

        st.write('Follow us on Twitter @TweetersSp https://twitter.com/TweetersSp')
        st.write(f'Code is publicly available at: '
                 f'https://github.com/JimMaastricht5/birdclassifier and'
                 f' https://github.com/JimMaastricht5/tweetersp')
        return
