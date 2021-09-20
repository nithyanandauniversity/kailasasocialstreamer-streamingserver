from __future__ import unicode_literals
import subprocess
from datetime import datetime
import pytz
import asyncio
import aiohttp
from time import sleep
from youtube_live import get_live_url
from facebook_api import start_fb_live, check_live_status
from restream import init_restream
from log import infolog, errorlog
# from twitch import init_twitch

# Set local timezone to IST
tz = pytz.timezone('Asia/Kolkata')

# define constants
# youtube channel to monitor
channel_url = "https://www.youtube.com/c/CHANNEL-T0-MONITOR"

# address of NimbleStreamer RTMP source stream along with authentication
rtmp_output = "NIMBLE-STREAMER-RTMP-STREAM-URL"

infolog(f"Channel URL: {channel_url}")


# function to run a docker container from datarhei/restreamer image; passing arguments to set input stream as youtube HLS pull url, output stream as NimbleStreamer RTMP source
async def create_restreamer(hls_url, video_id):

    # run shell command using subprocess and return stdout
    return subprocess.check_output(
        [
            f'docker run -d --restart always jrottenberg/ffmpeg -nostdin -loglevel error -nostats -i {hls_url} -map 0 -flags +global_header -c:v libx264 -preset ultrafast -r 30 -g 60 -b:v 800k -maxrate 800k -bufsize 800k   -c:a aac -threads 6 -ar 44100 -b:a 128k -flags +global_header -bsf:a aac_adtstoasc -pix_fmt yuv420p   -flags +global_header   -f fifo -fifo_format  tee   -drop_pkts_on_overflow 1 -attempt_recovery 1 -recovery_wait_time 1 "[f=flv:onfail=ignore]{rtmp_output}" &'
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

    # intitialize flag values
    fb_live_status = False
    fb_broadcast_id = ''

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

                # call function to add all twitch and twitter rules to nimble streamer
                # await init_twitch()

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

                    # wait for 10 seconds till outgoing stream starts, then start Facebook live
                    sleep(5)

                    # below workflow for facebook live is to accommodate for small breaks in input stream
                    # if a break in stream occurs, this loop function will iterate again
                    # since facebook livestreams have a higher tolerance of time for breaks in input stream, the facebook post may still be live
                    # in case the facebook post is still live, we do not want to end it and start a new facebook live

                    if fb_broadcast_id != '':  # check if facebook broadcast ID is not empty i.e. an earlier Facebook Live Post has already been created / this function is running for the first time

                        # If an earlier facebook broadcast has been created already, then check its current status
                        fb_live_status = await check_live_status(fb_broadcast_id)
                        infolog(f"Facebook Live Status: {fb_live_status}")

                    if not fb_live_status:  # if earlier created facebook broadcast is not live anymore, call function to create a new live
                        fb_broadcast_id = await start_fb_live(video_title)

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
                            # if input stream is still broken after 10 seconds, initialize destruction of docker restreamer container

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
