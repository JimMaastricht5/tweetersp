import streamlit as st
import pandas as pd
import urllib.request
from urllib.error import HTTPError
from datetime import datetime
from datetime import timedelta
import pytz
import plotly.express as px
from st_aggrid import GridOptionsBuilder, AgGrid, GridUpdateMode, DataReturnMode


# sample link format https://storage.googleapis.com/tweeterssp-web-site-contents/2022-12-29-11-57-29227.jpg
class WebPages:
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

    def build_common_name(self, df, target_col):
        df['Common Name'] = df[target_col]
        df['Common Name'] = [name[name.find(' ') + 1:] if name.find(' ') >= 0 else name
                             for name in df['Common Name']]
        df['Common Name'] = [name[name.find('(') + 1: name.find(')')] if name.find('(') >= 0 else name
                             for name in df['Common Name']]
        return df

    # @st.cache_data
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
        df = self.build_common_name(df, 'Message')
        df = df.drop(['Unnamed: 0'], axis='columns')

        # reorder df
        new_col_order = ['Date Time', 'Common Name', 'Message', 'Feeder Name', 'Event Num', 'Message Type',
                         'Image Name']
        df = df.reindex(columns=new_col_order)

        self.feeders = list(df['Feeder Name'].unique())
        return df.sort_values('Date Time', ascending=False)

    # @st.cache_data
    def load_bird_occurrences(self):
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
                print(f'no web occurences found for {date}')
                print(e)
                self.dates.remove(date)  # remove date if not found
        df = self.build_common_name(df, 'Species')  # build common name for merged df
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

    def publish_first_image(self):
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

    def filter_occurences(self, feeder_options, date_options, bird_options):
        df = self.df_occurrences
        df = df[df['Feeder Name'].isin(feeder_options)]
        df = df[df['Date Time'].dt.strftime('%Y-%m-%d').isin(date_options)]  # compare y m d to date selection y m d
        if len(bird_options) > 0:
            df = df[df['Common Name'].isin(bird_options)]  # return birds if none selected
        return df

    def filter_message_stream(self, feeder_options, date_options, bird_options, message_options):
        df = self.df_msg_stream[self.df_msg_stream['Message Type'].isin(message_options)]
        df = df[df['Feeder Name'].isin(feeder_options)]
        df = df[df['Date Time'].dt.strftime('%Y-%m-%d').isin(date_options)]  # compare y m d to date selection y m d
        if len(bird_options) > 0:
            df = df[df['Common Name'].isin(bird_options)]  # return all birds if none selected
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

        # feeder multi select filters with expander
        with st.expander("Filters for Feeder, Dates, and Birds:"):
            st.write('Select values to include or exclude in the chart and information table.  '
                     'Empty list of birds is "all" birds.')
            dropdown_cols = st.columns(3)
            with dropdown_cols[0]:
                feeder_options = st.multiselect('Feeders:', self.feeders, self.feeders)  # feeders all selected
            with dropdown_cols[1]:
                date_options = st.multiselect('Dates:', self.dates, self.dates)  # dates available and all selected
            with dropdown_cols[2]:
                bird_options = st.multiselect('Birds:', self.birds, [])  # all birds common names none selected

        # text and graph
        st.write(f'Interactive Chart of Birds: {min(self.available_dates)} to {max(self.available_dates)}')
        # single day
        # fig1 = px.histogram(self.filter_occurences(feeder_options, date_options, bird_options),
        #                     x="Hour", color='Common Name', range_x=[self.min_hr, self.max_hr],
        #                     nbins=36, width=650, height=400)
        # fig1['layout']['xaxis'].update(autorange=True)
        # st.plotly_chart(fig1, use_container_width=True, sharing="streamlit", theme="streamlit")

        # multi-day
        fig2 = px.histogram(self.filter_occurences(feeder_options, date_options, bird_options),
                            x="Date Time", color='Common Name',
                            nbins=36, width=650, height=400)
        fig2['layout']['xaxis'].update(autorange=True)
        st.plotly_chart(fig2, use_container_width=True, sharing="streamlit", theme="streamlit")

        # image and message stream multi-select filters
        message_options = st.multiselect(
            'Prediction Certainty: \n "spotted" includes all of the observations above the confidence '
            'threshold of the model. "possible" includes the observations below the threshold',
            ['possible', 'spotted'],  # remove message type and display on own page later
            ['spotted'])

        st.dataframe(data=self.filter_message_stream(feeder_options, date_options, bird_options, message_options),
                     use_container_width=True)

        # write last 10 images from stream
        st.write('Last Ten Images: Most Recent to Least Recent')
        self.publish_row_of_images(starting_col=0)  # row 1 of 5
        self.publish_row_of_images(starting_col=0 + self.num_image_cols)  # row 2 of 5

        return

    def daily_charts_page(self):
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
            fig1 = px.histogram(self.filter_occurences(feeder_options, [date], self.birds),
                                x="Hour", color='Common Name', range_x=[self.min_hr, self.max_hr],
                                nbins=36, width=650, height=400)
            fig1['layout']['xaxis'].update(autorange=True)
            st.plotly_chart(fig1, use_container_width=True, sharing="streamlit", theme="streamlit")

        return

    def messages_page(self):
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
        # self.publish_row_of_images()
        self.publish_first_image()
        return

    def about_page(self):
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


    def test_df_page(self):
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
            with dropdown_cols[1]:
                date_options = st.multiselect('Dates:', self.dates, self.dates)  # dates available and all selected
            with dropdown_cols[2]:
                bird_options = st.multiselect('Birds:', self.birds, [])  # all birds common names none selected

        # text and graph
        st.write(f'Interactive Chart of Birds: {min(self.available_dates)} to {max(self.available_dates)}')
        # single day
        # fig1 = px.histogram(self.filter_occurences(feeder_options, date_options, bird_options),
        #                     x="Hour", color='Common Name', range_x=[self.min_hr, self.max_hr],
        #                     nbins=36, width=650, height=400)
        # fig1['layout']['xaxis'].update(autorange=True)
        # st.plotly_chart(fig1, use_container_width=True, sharing="streamlit", theme="streamlit")

        # multi-day
        fig2 = px.histogram(self.filter_occurences(feeder_options, date_options, bird_options),
                            x="Date Time", color='Common Name',
                            nbins=36, width=650, height=400)
        fig2['layout']['xaxis'].update(autorange=True)
        st.plotly_chart(fig2, use_container_width=True, sharing="streamlit", theme="streamlit")

        # image and message stream multi-select filters
        message_options = st.multiselect(
            'Prediction Certainty: \n "spotted" includes all of the observations above the confidence '
            'threshold of the model. "possible" includes the observations below the threshold',
            ['possible', 'spotted'],  # remove message type and display on own page later
            ['spotted'])

        # st.dataframe(data=self.filter_message_stream(feeder_options, date_options, bird_options, message_options),
        #              use_container_width=True)
        # AgGrid(self.filter_message_stream(feeder_options, date_options, bird_options, message_options))

        df = self.filter_message_stream(feeder_options, date_options, bird_options, message_options)
        gb = GridOptionsBuilder.from_dataframe(df)
        gb.configure_pagination(enabled=True, paginationPageSize=20)  # Add pagination
        gb.configure_default_column(enablePivot=False, enableValue=True, enableRowGroup=False)
        # gb.configure_selection(selection_mode="single", use_checkbox=True)
        gb.configure_selection('multiple', use_checkbox=True,
                               groupSelectsChildren="Group checkbox select children")  # Enable multi-row selection
        gb.configure_side_bar()
        gridoptions = gb.build()

        response = AgGrid(
            df,
            gridOptions=gridoptions,
            enable_enterprise_modules=True,
            update_mode=GridUpdateMode.MODEL_CHANGED,
            data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
            fit_columns_on_grid_load=True,
            header_checkbox_selection_filtered_only=True,
            height=1000,
            use_checkbox=True)
        # gb = GridOptionsBuilder.from_dataframe(data)
        # gb.configure_pagination(paginationAutoPageSize=True)  # Add pagination
        # gb.configure_side_bar()  # Add a sidebar
        # gb.configure_selection('multiple', use_checkbox=True,
        #                        groupSelectsChildren="Group checkbox select children")  # Enable multi-row selection
        # gridOptions = gb.build()
        #
        # grid_response = AgGrid(
        #     data,
        #     gridOptions=gridOptions,
        #     data_return_mode='AS_INPUT',
        #     update_mode='MODEL_CHANGED',
        #     fit_columns_on_grid_load=False,
        #     # theme='blue',  # Add theme color to the table
        #     enable_enterprise_modules=True,
        #     height=350,
        #     width='100%',
        #     reload_data=True
        # )
        #
        df = response['data']
        selected = response['selected_rows']
        df2 = pd.DataFrame(selected)  # Pass the selected rows to a new dataframe df
        # write last 10 images from stream
        # st.write('Last Ten Images: Most Recent to Least Recent')
        # self.publish_row_of_images(starting_col=0)  # row 1 of 5
        # self.publish_row_of_images(starting_col=0 + self.num_image_cols)  # row 2 of 5
        return
