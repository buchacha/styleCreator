import os
import io
import warnings
import argparse
import time
import pathlib

from PIL import Image
from stability_sdk import client
import stability_sdk.interfaces.gooseai.generation.generation_pb2 as generation
import numpy as np


def setup_env():
    os.environ["STABILITY_HOST"] = "grpc.stability.ai:443"
    os.environ["STABILITY_KEY"] = "sk-Ov1yj78aUrbNgCKB19eYiTMC37BUgf9X6OQmDpbTTHViaACI"

    # Set up our connection to the API.
    stability_api = client.StabilityInference(
        key=os.environ["STABILITY_KEY"],  # API Key reference.
        verbose=True,  # Print debug messages.
        engine="stable-diffusion-xl-1024-v1-0",  # Set the engine to use for generation.
        # Available engines: stable-diffusion-v1 stable-diffusion-v1-5 stable-diffusion-512-v2-0 stable-diffusion-768-v2-0
        # stable-diffusion-512-v2-1 stable-diffusion-768-v2-1 stable-diffusion-xl-beta-v2-2-2 stable-inpainting-v1-0 stable-inpainting-512-v2-0
    )
    return stability_api


def create_box(mask):
    ar = np.array(mask)
    morphed_white_pixels = np.argwhere(ar == 0)

    min_y = min(morphed_white_pixels[:, 1])
    max_y = max(morphed_white_pixels[:, 1])
    min_x = min(morphed_white_pixels[:, 0])
    max_x = max(morphed_white_pixels[:, 0])

    padding = 20
    top_left = (min_y - padding, min_x - padding)
    bottom_right = (max_y + padding, max_x + padding)
    return top_left, bottom_right


def get_promt(image_path):
    base_prompt = []
    opt_additional_prompts = "photorealistic, best quality"
    opt_additional_prompts_weight = 1
    opt_antiprompts = "face, cartoon, nude, the clothes fit perfectly, tattoo"
    opt_antiprompts_weight = -1
    basename = os.path.basename(image_path)
    list_from_basename = basename[:-4].split(sep="_")
    prompt_list = list_from_basename[1:-1]
    prompt = " ".join(prompt_list)
    base_prompt = [
        generation.Prompt(
            text=f"{prompt}, {opt_additional_prompts}",
            parameters=generation.PromptParameters(
                weight=opt_additional_prompts_weight
            ),
        )
    ]
    base_prompt.append(
        generation.Prompt(
            text=f"{opt_antiprompts}",
            parameters=generation.PromptParameters(weight=opt_antiprompts_weight),
        )
    )
    return base_prompt


def create_request(api, prompt, image, mask):
    opt_sh = 0.8  # РЎС‚РµРїРµРЅСЊ РІР»РёСЏРЅРёСЏ РёСЃС…РѕРґРЅРѕР№ РєР°СЂС‚РёРЅРєРё РЅР° РЅР°С‡Р°Р»СЊРЅС‹С… С€Р°РіР°С… (0-1) (РјРµРЅСЊС€Рµ Р·РЅР°С‡РµРЅРёРµ - Р±РѕР»СЊС€Рµ РІР»РёСЏРЅРёРµ)
    opt_end_sh = 0.1  # РЎС‚РµРїРµРЅСЊ РІР»РёСЏРЅРёСЏ РёСЃС…РѕРґРЅРѕР№ РєР°СЂС‚РёРЅРєРё РЅР° РєРѕРЅРµС‡РЅС‹С… С€Р°РіР°С… (0-1) (РјРµРЅСЊС€Рµ Р·РЅР°С‡РµРЅРёРµ - Р±РѕР»СЊС€Рµ РІР»РёСЏРЅРёРµ)
    opt_cfg = 7  # (1-35) РќР°СЃРєРѕР»СЊРєРѕ СЃРёР»СЊРЅРѕ РјРѕРґРµР»СЊ СЃР»РµРґСѓРµС‚ РїСЂРѕРјС‚Сѓ
    opt_steps = 30  # РљРѕР»РёС‡РµСЃС‚РІРѕ С€Р°РіРѕРІ РіРµРЅРµСЂР°С†РёРё (10-150)
    opt_sampler = generation.SAMPLER_K_EULER_ANCESTRAL

    answers = api.generate(
        prompt=prompt,
        init_image=image,
        mask_image=mask,
        # mask_source='MASK_IMAGE_BLACK',
        start_schedule=opt_sh,
        end_schedule=opt_end_sh,
        samples=4,
        # If attempting to transform an image that was previously generated with our API,
        # initial images benefit from having their own distinct seed rather than using the seed of the original image generation.
        steps=opt_steps,  # Amount of inference steps performed on image generation. Defaults to 30.
        cfg_scale=opt_cfg,  # Influences how strongly your generation is guided to match your prompt.
        # Setting this value higher increases the strength in which it tries to match your prompt.
        # Defaults to 7.0 if not specified.
        width=mask.size[0],  # Generation width, defaults to 512 if not included.
        height=mask.size[1],  # Generation height, defaults to 512 if not included.
        sampler=opt_sampler  # Choose which sampler we want to denoise our generation with.
        # Defaults to k_lms if not specified. Clip Guidance only supports ancestral samplers.
        # (Available Samplers: ddim, plms, k_euler, k_euler_ancestral, k_heun, k_dpm_2, k_dpm_2_ancestral, k_dpmpp_2s_ancestral, k_lms, k_dpmpp_2m, k_dpmpp_sde)
    )
    return answers


def save_cropped(img, img_name, search_path, top_left, bottom_right):
    res_im = img.crop((top_left[0], top_left[1], bottom_right[0], bottom_right[1]))
    res_im.save(os.path.join(search_path, img_name))
    return res_im


def save_answer(
    answers, img_name, save_path, search_path, left_top, right_bottom, attempt=0
):
    i = 0
    try:
        images = []
        search = []
        for resp in answers:
            for artifact in resp.artifacts:
                if artifact.finish_reason == generation.FILTER:
                    warnings.warn(
                        "Your request activated the API's safety filters and could not be processed."
                        "Please modify the prompt and try again."
                    )
                if (artifact.type == generation.ARTIFACT_IMAGE) and (artifact.finish_reason != generation.FILTER):
                    global img
                    img = Image.open(io.BytesIO(artifact.binary))
                    img.save(os.path.join(save_path, img_name[:-4] + f"_{i}.png"))
                    search_img = save_cropped(
                        img,
                        img_name[:-4] + f"_{i}.png",
                        search_path,
                        left_top,
                        right_bottom,
                    )
                    images.append(np.array(img))
                    search.append(np.array(search_img))
                    i = i + 1

    except:
        if attempt < 3:
            return save_answer(
                answers,
                img_name,
                save_path,
                search_path,
                left_top,
                right_bottom,
                attempt + 1,
            )
        else:
            return False
    return True


def create_request_func(img_name, current_path):
    """
    Creates a request function to process an image.

    Args:
        img_name (str): The name of the image file.
        current_path (str): The current path where the image and directories are located.

    Returns:
        bool: The success of the request.

    Raises:
        FileExistsError: If there is a file with the same name in the container generation directory.

    """

    input_dir = os.path.join(current_path, "cont_segmentation")
    cont = os.path.join(current_path, "container_generation")
    mask_dir = os.path.join(current_path, "output_segmentation")
    output_dir = os.path.join(current_path, "output_generation")
    search = os.path.join(current_path, "search")

    if not os.path.exists(cont):
        os.makedirs(cont)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    if not os.path.exists(search):
        os.makedirs(search)

    api = setup_env()

    prompt = get_promt(img_name)
    image = Image.open(os.path.join(input_dir, img_name))
    mask = Image.open(os.path.join(mask_dir, img_name)).convert("L")
    left_top, right_bottom = create_box(mask)
    answers = create_request(api, prompt, image, mask)
    try:
        os.rename(
            os.path.join(input_dir, img_name),
            os.path.join(cont, img_name),
        )
    except FileExistsError:
        os.remove(os.path.join(input_dir, img_name))
    comleted = save_answer(
        answers,
        img_name,
        output_dir,
        search,
        left_top,
        right_bottom,
    )
    return comleted