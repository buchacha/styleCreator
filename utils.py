import requests
import base64
import config
import os, glob
import aiohttp
# from imgbbpy.aio import Client
import asyncio

from aiogram import types
from serpapi import GoogleSearch

import params_dict


def remove(file_name):
    while os.path.isfile(file_name):
        print('rem')
        os.remove(file_name)


def remove_prefix(prefix_file_name):
    print("FDSFSDF")
    for filename in glob.glob(prefix_file_name + '*'):
        print('filename ', filename)
        os.remove(filename)
    # while os.path.isfile(file_name + '*'):
    #     print('rem')
    #     os.remove(file_name + '*')


def upload_image_old(image_path):
    url = "https://api.imgbb.com/1/upload"
    api_key = "0fed957c70c9bd1193587969d205dd2b"
    print('uploading...')

    with open(image_path, "rb") as file:
        payload = {
            "key": api_key,
            "image": base64.b64encode(file.read()),
        }

    print('ok')
    response = requests.post(url, payload)
    print('get')
    json_response = response.json()

    print(json_response)
    
    if 'success' in json_response and json_response['success']:
        image_url = json_response['data']['url']
        return image_url
        print("Image uploaded successfully. URL:", image_url)
    else:
        return ''
        print("Image upload failed.")


async def upload_image(image_path):
    print('uploading...')
    url = "https://api.imgbb.com/1/upload"
    api_key = "0fed957c70c9bd1193587969d205dd2b"
    async with aiohttp.ClientSession() as session:
        with open(image_path, "rb") as file:
            payload = {
                "key": api_key, 
                "image": file.read(),
            }
            async with session.post(url, data=payload) as response:
                json_response = await response.json(content_type=None)
                # json_response = json.load(response)

            print('json', json_response)
            
            if 'success' in json_response and json_response['success']:
                image_url = json_response['data']['url']
                print("Image uploaded successfully. URL:", image_url)
                return image_url
    # client = Client(api_key)
    # image = await client.upload(file=image_path)
    # print(image.url)
    
    # await client.close()
    # return image.url


def get_reply_kb(key):
    kb = []
    for text in params_dict.buttons[key]:
        kb.append([types.KeyboardButton(text=text)])
    return types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


async def get_info_from_api(image_path, test=False):
    try:
        img_url = await upload_image(image_path)

        params = {
            "engine": "google_lens",
            "url": img_url,
            "api_key": config.api_token
        }

        search = GoogleSearch(params)
        results = search.get_dict()
        print(results)
        # if 'knowledge_graph' in results:
        #     knowledge_graph = results["knowledge_graph"][0]

        #     result = []
        #     title = knowledge_graph['title']

        #     link = knowledge_graph['images'][0]['source']
        #     params = link.split("?")[1].split("&")
        #     img = ''
        #     for param in params:
        #         key, value = param.split("=")
        #         if key == "imgurl":
        #             img = value
            
        #     for item in knowledge_graph['shopping_results']:
        #         result.append({
        #             'url': img,
        #             'text': (
        #                 title + '\n' + \
        #                 'Источник: ' + item['source'] + '\n' + \
        #                 'Цена: ' + item['price'] + '\n' + \
        #                 'Ссылка: ' + item['link']
        #             )
        #         })
            
        #     return result
        # else:
        visual_matches = results["visual_matches"]

        result = []
        i = 0
        while i < len(visual_matches) and len(result) < 3:
            item = visual_matches[i]
            try:
                result.append({
                    'url_img': item['thumbnail'],
                    'url_shop': item['link'],
                    'text': (
                        item['title'] + '\n' + \
                        'Источник: ' + item['source'] + '\n' + \
                        'Цена: ' + item['price']['value']
                    )
                })
            except Exception as e:
                print(e)
            i += 1

        return result
    except Exception as e:
        print(e)

        return ''


import json

async def send_event_to_amplitude(user_id, state, event_type):
    user_data = await state.get_data()

    headers = {
        'Content-Type': 'application/json',
        'Accept': '*/*'
    }

    event = {
        "user_id": str(user_id),
        "event_type": event_type,
        'user_properties': {
            "Balance": user_data['count'],
            "App_version": config.app_version
        }
    }
    if 'sex' in user_data:
        event['user_properties']["Sex"] = user_data['sex']

    if event_type in ['param_apply_press', 'looks_generation_finish', 'looks_look_choose']:
        event['event_properties'] = {'prompt': user_data['join_parameters']}

    data = {
        "api_key": config.amplitude_dev,
        "events": [event]
    }

    response = requests.post('https://api2.amplitude.com/2/httpapi',
                                headers=headers, data=json.dumps(data))

    if response.status_code == 200:
        print("Success:", response.json())
    else:
        print("Error:", response.text)