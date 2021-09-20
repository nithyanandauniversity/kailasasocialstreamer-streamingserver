from pymongo import MongoClient
from pprint import pprint
from datetime import datetime
import aiohttp
import requests
from requests.auth import HTTPBasicAuth
import smtplib
from log import infolog, errorlog

CLIENT_ID = 'RESTREAM-IO-DEVELOPER-ACCOUNT-CLIENT-ID'
CLIENT_SECRET = 'RESTREAM-IO-DEVELOPER-ACCOUNT-CLIENT-SECRET'
MONGO_URI = 'MONGO-DB-CLOUD-ATLAS-CONNECTION-URI'
LIVESTREAM_DESCRIPTION = """VIDEO DESCRIPTION FOR YOUTUBE LIVE"""

# create MongoDB client
client = MongoClient(MONGO_URI)

# specify MongoCloud Atlas database
db = db = client['nimbledb']

# specify MongoCloud Atlas collection
users = db['restream_user']


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


# function to iterate over all RTMP republish rules and delete all Facebook destinations
async def delete_nimble_restream_rules():
    async with aiohttp.ClientSession() as session:
        async with session.get(f"http://127.0.0.1:8086/manage/rtmp/republish?salt=640261&hash=//caJS3uOqiy6N/9SHsqgQ==") as resp:
            result = await resp.json()

    for entry in result['rules']:
        if entry['dest_addr'] == 'live.restream.io':
            await delete_nimble_rule(entry['id'])


# function to update MongoDB with newly retrieved access token
async def update_db(id, access_token, refresh_token):

    query = {"userID": id}
    newvalues = {"$set": {"accessToken": access_token, "refreshToken": refresh_token,
                          "lastModified": datetime.now().strftime('%Y-%m-%dT%H:%M:%S+00:00')}}

    # pymongo command to update one document
    users.update_one(query, newvalues)


# function to update MongoDB with newly retrieved streamkey
async def update_db_streamKey(id, streamKey):

    query = {"userID": id}
    newvalues = {"$set": {"streamKey": streamKey,
                          "lastModified": datetime.now().strftime('%Y-%m-%dT%H:%M:%S+00:00')}}

    # pymongo command to update one document
    users.update_one(query, newvalues)


# function to retrieve new access token using long term refresh token using Restream API
async def refresh_access_token(refresh_token):

    resp = requests.post("https://api.restream.io/oauth/token", auth=HTTPBasicAuth(CLIENT_ID,
                         CLIENT_SECRET), data={"grant_type": "refresh_token", "refresh_token": refresh_token})
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
async def start_process(auth, title):

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

    try:  # delete all old Facebook Republish destinations from NimbleStreamer since they have expired and we create a new destination for each Facebook Live post
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

        while retries > 0:  # try updating metadata up to 2 times

            retries -= 1

            # call function to manage updating flow
            result = await start_process(auth, title)

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

# call to run this file independently
# asyncio.run(init_restream())
