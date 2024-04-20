from eyepop import EyePopSdk

import os
import asyncio
import logging
import time
import json
import aiofiles


def get_inference_data(location, timeout=None):
    """
    Perform inference on the given video using the EyePop SDK.

    Args:
        location (str): The location of the video to perform inference on.
        timeout (int, optional): The maximum seconds of prediction data. Defaults to None, which means process all frames data.

    Raises:
        Exception: If an error occurs during the inference process.

    Returns:
        None
    """
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('eyepop').setLevel(level=logging.DEBUG)

    # EyePop SDK configuration
    EYEPOP_POP_ID = '8d88113ee4814b6683eba5a69fba7454'
    EYEPOP_SECRET_KEY = open("eyepop_secret.env", "r").read()
    EYEPOP_URL = 'https://staging-api.eyepop.ai'

    with EyePopSdk.endpoint(pop_id=EYEPOP_POP_ID, secret_key=EYEPOP_SECRET_KEY, eyepop_url=EYEPOP_URL, is_async=False) as endpoint:

        manifest = endpoint.get_manifest()

        # set manifest for PARSeq
        manifest.append(
            {
                "authority": "PARSeq",
                "manifest": "https://s3.amazonaws.com/models.eyepop.ai/releases/PARSeq/1.0.2/manifest.json",
            }
        )

        # set manifest for eyepop-text
        manifest.append(
            {
                "authority": "eyepop-text",
                "manifest": "https://s3.amazonaws.com/models.eyepop.ai/releases/eptext/1.0.3/manifest.json",
            }
        )

        endpoint.set_manifest(manifest)

        # load PARSeq model
        inner_model_def = {
            'model_id': 'PARSeq:PARSeq',
            'dataset': 'TextDataset',
            'format': 'TorchScriptCuda',
            'type': 'float32'
        }
        endpoint.load_model(inner_model_def)

        # load eyepop-text model
        inner_model_def = {
            'model_id': 'eyepop-text:EPTextB1',
            'dataset': 'Text',
            'format': 'TorchScriptCuda',
            'type': 'float32'
        }
        endpoint.load_model(inner_model_def)

        endpoint.set_pop_comp(
            """
            ep_infer id=1
            model=eyepop-person:EPPersonB1_Person_TorchScriptCuda_float32 threshold=0.8
            ! ep_infer id=2
            tracing=deepsort
            model=legacy:reid-mobilenetv2_x1_4_ImageNet_TensorFlowLite_int8
            secondary-to-id=1
            secondary-for-class-ids=<0>
            ! ep_infer id=3  category-name="text"
            model=eyepop-text:EPTextB1_Text_TorchScriptCuda_float32 threshold=0.6
            secondary-to-id=1
            secondary-for-class-ids=<0>
            ! ep_infer id=4 category-name="text"
            secondary-to-id=3
            model=PARSeq:PARSeq_TextDataset_TorchScriptCuda_float32 threshold=0.1
            ! ep_infer id=5 category-name="sports equipment"
            model=eyepop-sports:EPSportsB1_Sports_TorchScriptCuda_float32 threshold=0.6
            """
        )

        with open("data.json", "w") as data_file:

            try:
                # Upload video for inference
                job = endpoint.upload(location)

                data_file.write("[")

                while result := job.predict():

                    # skip any empty results
                    if 'seconds' not in result:
                        continue

                    # write the result to the data.json file
                    data_file.write(json.dumps(
                        result, indent=4, sort_keys=True))

                    data_file.write(",")

                    #  stop job if timeout is reached
                    if timeout is not None and result['seconds'] > timeout:
                        job.cancel()

                    print(result['seconds'])

                # remove the last comma
                data_file.seek(data_file.tell() - 1, os.SEEK_SET)
                data_file.truncate()
                data_file.write("]")

                data_file.close()

            except Exception as e:
                print('\n\n\n\n\n\n\n\n')
                print(e)
                print('\n\n\n\n\n\n\n\n')
                data_file.close()
