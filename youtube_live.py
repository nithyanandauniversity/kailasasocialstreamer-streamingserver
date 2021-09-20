import youtube_dl


# function to check if youtube channel is live and return result
def get_live_url(channel_url):

    # initialize empty result in case channel is not live
    result = {}

    # enter url of channel to monitor here
    url = f"{channel_url}/live"

    # youtube-dl options to not download the video and not print log to stdout
    youtube_dl_opts = {
        'simulate': 'true',
        'quiet': 'true'
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

            # for format in formats:
            #    if format['height'] == 720:
            #        video_url = format['url']
            #        break

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
