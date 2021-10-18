from __future__ import unicode_literals
from requests.auth import HTTPBasicAuth
from time import sleep
import asyncio
import subprocess
import requests
import aiohttp
from pprint import pprint
from pymongo import MongoClient
from datetime import datetime
import pytz
import logging
import youtube_dl

# define constants
# youtube channel to monitor
channel_url = "https://www.youtube.com/c/nithyanandatv"

# streaming server cloud IP address
CLOUD_SERVER_IP = '0.0.0.0'

# Following are nimble streamer constants to be copied from the rules.conf file of NimbleStreamer running on the server

# Nimble streamer application name
NIMBLE_STREAMER_APPLICATION = 'live'

# Nimble streamer stream key
NIMBLE_STREAMER_STREAM = 'stream'

# Nimble streamer application login username
NIMBLE_STREAMER_LOGIN = 'username'

# Nimble streamer application login password
NIMBLE_STREAMER_PWD = 'pwd'

# Restream.io developer account client ID
RESTREAMIO_CLIENT_ID = 'restream-client-id'

# Restream.io developer account client secret
RESTREAMIO_CLIENT_SECRET = 'restream-client-secret'

# Cloud MongoDB Atlas connection URI
MONGO_URI = 'mongodb+srv://....'

# Description for youtube video
LIVESTREAM_DESCRIPTION = """Enter video description here"""

# address of NimbleStreamer RTMP source stream along with authentication
rtmp_output = f"rtmp://{CLOUD_SERVER_IP}:1935/{NIMBLE_STREAMER_APPLICATION}?rtmpauth={NIMBLE_STREAMER_LOGIN}:{NIMBLE_STREAMER_PWD}/{NIMBLE_STREAMER_STREAM}"

# Create a log file for monitoring the process events - specify full path from root directory of the server
logging.basicConfig(
    filename='/path/to/log/file/monitor.log', level=logging.INFO)

# Set local timezone to IST
tz = pytz.timezone('Asia/Kolkata')

# create MongoDB client
client = MongoClient(MONGO_URI)

# specify MongoCloud Atlas database
db = db = client['MongoCloud Atlas Database Name']

# specify MongoCloud Atlas collection
users = db['MongoCloud Atlas Collection Name']


def infolog(text): # Function to add event to log file 
    logging.info(
        f" {datetime.now(tz).strftime('%d-%m-%Y %H:%M:%S')}  {text}")


def errorlog(text): # Function to add error to log file
    logging.warning(
        f" {datetime.now(tz).strftime('%d-%m-%Y %H:%M:%S')}  {text}")


# function to check if youtube channel is live and return result
def get_live_url(channel_url):

    # initialize empty result in case channel is not live
    result = {}

    # enter url of channel to monitor here
    url = f"{channel_url}/live"

    # youtube-dl options to not download the video and not print log to stdout
    youtube_dl_opts = {
        'simulate': 'true',
        'quiet': 'true',
        'cookiefile': '/path/to/cookies.txt'
    }

    with youtube_dl.YoutubeDL(youtube_dl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=False, process=False)

        if info_dict['_type'] == 'url':
            updated_info = ydl.extract_info(url, download=False)
            # video_url = updated_info.get("url", None)
            video_id = updated_info.get("id", None)
            video_title = updated_info.get('title', None)
            formats = updated_info.get('formats', None)

            video_url = ''

            # below section selects the quality for restreaming. Default is set to 720p or lower - whichever is available. To reduce default quality, comment out the highest quality. E.g. comment out the 720p block to use 480p or lower by default.

            for format in formats:
               if format['height'] == 720:
                   video_url = format['url']
                   break

            if video_url == '':
                for format in formats:
                    if format['height'] == 480:
                        video_url = format['url']
                        break

            if video_url == '':
                for format in formats:
                    if format['height'] == 360:
                        video_url = format['url']
                        break

            if video_url == '':
                for format in formats:
                    if format['height'] == 240:
                        video_url = format['url']
                        break

            result = {'video_id': video_id, 'video_title': video_title[:(
                len(video_title))-16], 'video_url': video_url}

    return result


# function to add given restream.io streamkey to local NimbleStreamer as RTMP Republish Rule
async def add_republish_rule(restream_stream_key):

    # compose required format rule data with given stream key
    rule_data = {"src_app": "live", "src_stream": "stream", "dest_addr": "live.restream.io", "dest_port": 1935, "dest_app": "live",
                 "dest_stream": restream_stream_key, "ssl": False}

    async with aiohttp.ClientSession() as session:
        async with session.post("http://127.0.0.1:8086/manage/rtmp/republish?salt=640261&hash=//caJS3uOqiy6N/9SHsqgQ==", json=rule_data) as resp:
            result = await resp.json()
            return result


# function to delete specified RTMP republish rule in local NimbleStreamer
async def delete_nimble_rule(rule_id):
    async with aiohttp.ClientSession() as session:
        async with session.delete(f"http://127.0.0.1:8086/manage/rtmp/republish/{rule_id}?salt=640261&hash=//caJS3uOqiy6N/9SHsqgQ==") as resp:
            result = await resp.json()


# function to iterate over all RTMP republish rules and delete all Restream.io destinations
async def delete_nimble_restream_rules():
    async with aiohttp.ClientSession() as session:
        async with session.get(f"http://127.0.0.1:8086/manage/rtmp/republish?salt=640261&hash=//caJS3uOqiy6N/9SHsqgQ==") as resp:
            result = await resp.json()

    for entry in result['rules']:
        if entry['dest_addr'] == 'live.restream.io':
            await delete_nimble_rule(entry['id'])


# function to update MongoDB with newly retrieved Restream.io access token
async def update_db(id, access_token, refresh_token):

    query = {"userID": id}
    newvalues = {"$set": {"accessToken": access_token, "refreshToken": refresh_token,
                          "lastModified": datetime.now().strftime('%Y-%m-%dT%H:%M:%S+00:00')}}

    # pymongo command to update one document
    users.update_one(query, newvalues)


# function to update MongoDB with newly retrieved Restream.io streamkey
async def update_db_streamKey(id, streamKey):

    query = {"userID": id}
    newvalues = {"$set": {"streamKey": streamKey,
                          "lastModified": datetime.now().strftime('%Y-%m-%dT%H:%M:%S+00:00')}}

    # pymongo command to update one document
    users.update_one(query, newvalues)


# function to retrieve new Restream.io access token using long term refresh token using Restream API
async def refresh_access_token(refresh_token):

    resp = requests.post("https://api.restream.io/oauth/token", auth=HTTPBasicAuth(RESTREAMIO_CLIENT_ID,
                         RESTREAMIO_CLIENT_SECRET), data={"grant_type": "refresh_token", "refresh_token": refresh_token})
    result = resp.json()
    return {'status': resp.status_code, 'result': result}


# function to update a Restream channel's title and description using Restream API
async def update_meta(access_token, channel_id, title):

    headers = {
        'authorization': 'Bearer '+access_token,
        'Content-Type': 'application/json'
    }

    async with aiohttp.ClientSession() as session:
        async with session.patch(f"https://api.restream.io/v2/user/channel-meta/{channel_id}", json={"title": title, "description": LIVESTREAM_DESCRIPTION}, headers=headers) as resp:
            return {'status': resp.status}


# function to fetch list of all channels configured for a Restream account using Restream API
async def get_channels(access_token):
    headers = {
        'authorization': 'Bearer '+access_token,
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.restream.io/v2/user/channel/all", headers=headers) as resp:
            result = await resp.json()
            return {'status': resp.status, 'result': result}


# function to fetch streamkey of configured channel for a Restream account using Restream API
async def get_streamKey(access_token):
    headers = {
        'authorization': 'Bearer '+access_token,
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.restream.io/v2/user/streamKey", headers=headers) as resp:
            result = await resp.json()
            return {'status': resp.status, 'streamKey': result}


# function to manage overall process-flow of updating metadata of all channels in a Restream account
async def update_meta_flow(auth, title):

    # call function to fetch all channels belonging to Restream account
    restream_channels = await get_channels(auth['access_token'])

    if restream_channels['status'] == 200:  # if fetch is successful

        # iterate over each channel configured in the Restream account
        for channel in restream_channels['result']:

            infolog(f"Updating channel: {channel['id']}")

            # call function to update title and description of one channel
            meta_update = await update_meta(auth['access_token'], channel['id'], title)
            infolog(
                f"Meta update status for channel {channel['id']}: {meta_update['status']}")

        # return success status to initializing function
        return {'status': 1, 'result': 'Success'}

    # if fetch of channels fails due to invalid access token
    elif restream_channels['status'] == 401:

        errorlog(
            "Getting channels failed with 401 - token expired - refreshing token")

        # call function to retrieve new access token using refresh token
        refresh_token_result = await refresh_access_token(auth['refresh_token'])

        # if new token is retrieved successfully
        if refresh_token_result['status'] == 200:
            # return message to initializing function indicating restart of entire process with newly retrieved access token
            return {'status': 2, 'access_token': refresh_token_result['result']['access_token'], 'refresh_token': refresh_token_result['result']['refresh_token']}

        # if retrieval of new access token fails, send error message to initializing function
        return {'status': 3, 'error': refresh_token_result['result']}

    else:  # if fetch of channels fails due to some other error
        errorlog(
            f"Metadata update failed with some other error - {restream_channels['status']}")
        errorlog(str(restream_channels['status']))
        # send other error status to intializing function
        return {'status': 0}


# function to initialize process of updating Metadata for all connected Restream channels
async def init_restream(title):

    try:  # delete all old Restream.io Republish destinations from NimbleStreamer since they have expired and we create a new destination for each Facebook Live post
        infolog("Deleting pre-existing Restream rules")
        await delete_nimble_restream_rules()
    except:
        errorlog("Error in deleting pre-existing Restream rules")

    for user in users.find():  # iterate over each connected Restream channel

        infolog(
            f"Updating restream metadata for user {user['channelName']} – {user['email']}")

        # setting 2 attempts for updating metadata in case first attempt fails due to expired access token
        retries = 2

        # set auth values
        auth = {'access_token': user['accessToken'],
                'refresh_token': user['refreshToken']}

        while retries > 0:  # try updating metadata up to 2 times. 1st try using the stored access token. 2nd try using the refreshed access token. If 2nd try fails, some other error has occured.

            retries -= 1

            # call function to manage updating flow
            result = await update_meta_flow(auth, title)

            if result['status'] == 1:  # if updating metadata for Restream channel is successfull

                infolog(
                    f"Meta updated successfully for {user['channelName']} – {user['email']}")

                try:
                    streamKey = await get_streamKey(auth['access_token'])
                    addresult = await add_republish_rule(streamKey['streamKey']['streamKey'])
                except Exception as e:
                    errorlog(str(e))
                else:
                    infolog(
                        f"Added {user['channelName']} – {user['email']} as republish rule to NimbleStreamer")
                    # call function to update newly retrieved streamkey in mongoDB
                    await update_db_streamKey(user['userID'], streamKey['streamKey']['streamKey'])

                break

            elif result['status'] == 2:  # if access token is refresh successfully

                infolog("Refreshed token successfully")

                # call function to update value of new access token in MongoDB
                await update_db(user['userID'], result['access_token'], result['refresh_token'])

                # replace value of currently used access token with newly retrieved value
                auth['access_token'] = result['access_token']
                auth['refresh_token'] = result['refresh_token']

                # try the entire process again till retries are exhausted
                continue

            elif result['status'] == 3:  # if access token refresh fails

                errorlog(
                    f"Refreshing process failed for user {user['channelName']} – {user['email']}")

                errorlog(str(result['error']))

                break

            else:  # if updating metadata process fails for some other unknown reason

                errorlog("FAILED")

                break


infolog(f"Channel URL: {channel_url}")


# function to run a docker container from jrottenberg/ffmpeg image; passing arguments to set input stream as youtube HLS pull url, output stream as NimbleStreamer RTMP source
async def create_restreamer(hls_url, video_id):

    # run shell command using subprocess and return stdout
    # This command also specifies streaming quality settings for our platform
    # Main values to configure here are "-b:v 1500k" which specifies avg. video bitrate to 1500kbps; "-maxrate 2000k" specifies maximum video bitrate to 2000kbps; "-bufsize 1500k" sets the buffer size to 1500kbps. Adjust these values based on the performance of the cloud streaming server. Higher port speed will allow higher values.
    return subprocess.check_output(
        [
            f'docker run -d --restart always jrottenberg/ffmpeg -nostdin -loglevel error -nostats -i {hls_url} -map 0 -flags +global_header -c:v libx264 -preset ultrafast -r 30 -g 60 -b:v 1500k -maxrate 2000k -bufsize 1500k   -c:a aac -threads 6 -ar 44100 -b:a 128k -flags +global_header -bsf:a aac_adtstoasc -pix_fmt yuv420p   -flags +global_header   -f fifo -fifo_format  tee   -drop_pkts_on_overflow 1 -attempt_recovery 1 -recovery_wait_time 1 "[f=flv:onfail=ignore]{rtmp_output}" &'
        ],
        shell=True,
        text=True,
    )


async def stop_all_containers():  # function to stop all currently running docker containers on the system
    return subprocess.check_output(
        [f"docker stop $(docker ps -a -q)"], shell=True, text=True)


async def delete_all_containers():  # function to delete all docker containers on the system
    return subprocess.check_output(
        [f"docker rm $(docker ps -a -q)"], shell=True, text=True)


async def restreamer_status():  # function to check and return status of input stream of restreamer docker container
    async with aiohttp.ClientSession() as session:

        async with session.get('http://127.0.0.1:8086/manage/rtmp/republish/stats?salt=640261&hash=//caJS3uOqiy6N/9SHsqgQ==') as resp:
            result = await resp.json()
            return result


async def main():

    while True:  # start infinite loop for periodically monitoring a youtube channel

        try:  # call function to check status of youtube channel and fetch the metadata
            live_details = get_live_url(channel_url)

        except Exception as e:
            errorlog(e)
            break

        else:  # if no error occurs in above try

            # if live_details returned value is not empty i.e. youtube channel is live and return value contains live video metadata
            if live_details != {}:
                infolog(
                    f"Found live at {datetime.now(tz).strftime('%d-%m-%Y %H:%M:%S')}")

                # extract live video metadata

                # hls pull url for the restreamer
                hls_url = live_details['video_url']

                # id of video
                video_id = live_details['video_id']

                # title of video
                video_title = live_details['video_title']

                infolog(f"Video ID: {video_id}")
                infolog(f"Video Title: {video_title}")

                infolog('Clearing any pre-existing restreamers')
                try:  # stop and delete any previously running restreamer docker containers, since we are using the same port and database location for creating a new instance

                    # call function to stop all docker containers
                    await stop_all_containers()

                    # call function to delete all docker containers
                    await delete_all_containers()

                except:  # if no dockers are running, an exception will be thrown
                    infolog('No restreamers found running')

                # call function to update title and description of all connected restream.io accounts' channels with latest live video metadata
                await init_restream(video_title)

                infolog('Starting restream process')
                try:
                    # call function to run docker container of restreamer; pass live video hls pull url and video id as arguments
                    restreamer = await create_restreamer(hls_url, video_id)

                except Exception as e:
                    errorlog(e)
                    break

                else:

                    infolog(
                        f"Restreamer created: {str(restreamer)}\nMonitoring stream every 10 seconds")

                    # wait for 10 seconds till outgoing stream starts, then start monitoring the restream
                    sleep(5)

                    # set default flag value for monitoring incoming youtube live stream
                    input_stream_broken = False

                    while True:  # start a second infinite loop to periodically monitor incoming youtube live stream

                        # call function to monitor input stream status of restreamer docker container using its API
                        response = await restreamer_status()

                        # if input stream is connected
                        if len(response['stats']) > 0:

                            # wait for 10 seconds and check the status again
                            await asyncio.sleep(10)
                            continue

                        else:  # if input stream is disconnected

                            # check stream broken flag value for temporary breaks in input stream
                            # i.e. if input stream is broken, wait for 10 seconds and check again
                            # if input stream is still broken after 10 seconds, initialize destruction of docker ffmpeg container

                            # if input stream was not previously broken, set broken stream flag, wait for 10 seconds and go through the check loop again
                            if not input_stream_broken:
                                input_stream_broken = True
                                sleep(20)
                                continue

                            # if input stream was previously broken i.e. it is not just a short break in input stream
                            errorlog('Incoming HLS stream broken at ' +
                                     datetime.now(tz).strftime('%d-%m-%Y %H:%M:%S'))

                            infolog('Stopping all running restreamers')

                            try:

                                # call function to stop all docker containers
                                await stop_all_containers()

                                # call function to delete all docker containers
                                await delete_all_containers()

                            except:  # if no restreamers are running, an exception will be thrown
                                infolog('No restreamers found running')

                            finally:  # exit from infinite loop which is monitoring the input stream
                                break

            else:  # if live_details returned value is empty i.e. youtube channel is not live

                infolog('Channel not live at ' +
                        datetime.now(tz).strftime('%d-%m-%Y %H:%M:%S'))

                infolog('Sleeping for 10 minutes')

                # wait 10 minutes and check again
                await asyncio.sleep(600)
                continue

# call main function
asyncio.run(main())
