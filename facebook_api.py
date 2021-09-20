import aiohttp
import re
import json
from time import sleep
from log import infolog, errorlog

# define constants
fb_access_token = 'FACEBOOK-PAGE-LONG-LIVED-ACCESS-TOKEN'
page_id = 'FACEBOOK-PAGE-ID'

crosspost_pages = []
crosspost_pages_names = []


# function to delete specified RTMP republish rule in local NimbleStreamer
async def delete_nimble_rule(rule_id):
    async with aiohttp.ClientSession() as session:
        async with session.delete(f"http://127.0.0.1:8086/manage/rtmp/republish/{rule_id}?salt=640261&hash=//caJS3uOqiy6N/9SHsqgQ==") as resp:
            result = await resp.json()
            try:
                if result['status'] == "Ok":
                    infolog(f"Deleted rule {rule_id}")
            except:
                errorlog(f"Error in deleting rule {rule_id}")


async def delete_nimble_fb_rules():  # function to iterate over all RTMP republish rules and delete all Facebook destinations
    async with aiohttp.ClientSession() as session:
        async with session.get(f"http://127.0.0.1:8086/manage/rtmp/republish?salt=640261&hash=//caJS3uOqiy6N/9SHsqgQ==") as resp:
            result = await resp.json()

    for entry in result['rules']:
        if entry['dest_addr'] == 'live-api-s.facebook.com':
            await delete_nimble_rule(entry['id'])


# function to create a Facebook live post with specified title using Facebook API
async def create_broadcast(title):
    async with aiohttp.ClientSession() as session:
        async with session.post(f"https://graph.facebook.com/{page_id}/live_videos?status=LIVE_NOW&title={title}&description={title}&access_token={fb_access_token}") as resp:
            result = await resp.json()
            return result

# function to retrieve list of available crosspost destinations for a Facebook page


async def get_available_crossposts():

    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://graph.facebook.com/v11.0/{page_id}/crosspost_whitelisted_pages?fields=id%2Cname%2Callows_live_crossposts&limit=2&access_token={fb_access_token}") as resp:
            result = await resp.json()
            if 'data' in result:
                for item in result['data']:
                    crosspost_pages.append(
                        {'id': item['id'], 'name': item['name']})

    while 'paging' in result:
        after = result['paging']['cursors']['after']
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://graph.facebook.com/v11.0/{page_id}/crosspost_whitelisted_pages?fields=id%2Cname%2Callows_live_crossposts&limit=2&access_token={fb_access_token}&after={after}") as resp:
                result = await resp.json()
                if 'data' in result:
                    for item in result['data']:
                        crosspost_pages.append(
                            {'id': item['id'], 'name': item['name']})


# function to crosspost a Facebook Live post to list of destination pages
async def crosspost_actions(broadcast_id):

    # break up the crosspost request into multiple requests containing small groups of crosspost destinations, since a single request with large no. of crosspost destinaton fails due to large data size of request
    # no. of crosspost destinations in one request
    n = 10
    # segment a list into groups of n
    segmented_list_crossposts = [crosspost_pages[i:i + n]
                                 for i in range(0, len(crosspost_pages), n)]

    for group in segmented_list_crossposts:  # iterate over each segmented group of n in the full list

        # compose the data format required for sending the request
        crosspost_data = {"crossposting_actions": []}
        for entry in group:
            crosspost_data['crossposting_actions'].append(
                {"page_id": entry['id'], "action": "enable_crossposting_and_create_post"})
            infolog(f"Facebook crossposting attempt to: {entry['name']}")

        # send the request for this one group
        async with aiohttp.ClientSession() as session:
            async with session.post(f"https://graph.facebook.com/v10.0/{broadcast_id}?fields=crossposted_broadcasts%7Bstatus,from%7Bname%7D%7D&access_token={fb_access_token}", json=crosspost_data) as resp:
                result = await resp.json()


# function to check if Facebook Live post with given ID is live or expired
async def check_live_status(broadcast_id):

    is_live = False

    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://graph.facebook.com/{page_id}/live_videos?limit=3&fields=status&access_token={fb_access_token}") as resp:
            result = await resp.json()
            try:
                for entry in result['data']:
                    if entry['status'] != "LIVE":
                        continue
                    if entry['id'] == broadcast_id:
                        is_live = True
                    break
            except Exception as e:
                errorlog(str(e))

    # return status of Facebook live post
    return is_live


# function to add newly created Facebook live post's stream details to local NimbleStreamer as RTMP Republish Rule
async def add_republish_rule(fb_stream_key):

    # compose required format rule data with given stream key
    rule_data = {"src_app": "live", "src_stream": "stream", "dest_addr": "live-api-s.facebook.com", "dest_port": 443, "dest_app": "rtmp",
                 "dest_stream": fb_stream_key, "ssl": True}

    async with aiohttp.ClientSession() as session:
        async with session.post("http://107.152.41.191:8086/manage/rtmp/republish?salt=640261&hash=//caJS3uOqiy6N/9SHsqgQ==", json=rule_data) as resp:
            result = await resp.json()
            return result


# function to initialize process of creating a Facebook Live post with given title
async def start_fb_live(title):

    try:  # delete all old Facebook Republish destinations from NimbleStreamer since they have expired and we create a new destination for each Facebook Live post
        infolog("Deleting pre-existing FB rules")
        await delete_nimble_fb_rules()
    except:
        errorlog("Error in deleting pre-existing FB rules")

    try:  # Call function to create Facebook Live post with given title; function returns stream URL and key for newly created Facebook live event

        result = await create_broadcast(title)

        # store ID of newly created Facebook Live broadcast
        broadcast_id = result['id']

        # use Regex to extract stream key from composite stream URL
        fb_stream_key = re.findall(
            "\/rtmp\/(.+)", result['secure_stream_url'])[0]

    except Exception as e:
        errorlog(str(e))

    else:  # if no error occurs in above try

        # call function to add newly created Facebook Live broadcast to the local NimbleStreamer; pass stream key value as argument
        await add_republish_rule(fb_stream_key)

        infolog(f"Facebook broadcast {broadcast_id} started")

        # Wait for 10 seconds for NimbleStreamer to successfully start sending the stream to the Facebook Live Broadcast; upon receiving the stream, a Facebook Live post will be created
        sleep(10)

        # call function to crosspost above created Facebook Live broadcast to primary group of crosspost destinations
        await get_available_crossposts()

        # call function to crosspost above created Facebook Live broadcast to primary group of crosspost destinations
        await crosspost_actions(broadcast_id)
        infolog(f"Facebook crossposts started")

        # return broadcast ID to calling function
        return broadcast_id
