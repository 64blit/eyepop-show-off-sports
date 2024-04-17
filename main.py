from eyepop import EyePopSdk

import os
import asyncio
import logging
import time
import person_tracker as pt
import json
import argparse as ap

import movie_maker as mm
import eyepop_manager as em


def main(video_file_path: str, target_jersey_number: str, analyze=False):

    def upload_video(video_path: str):

        #
        #  0. Obtain the EyePop inference data from the video
        #
        if analyze:
            em.get_inference_data(video_path)

        # The PersonTracker class is used to track people in the video
        person_tracker = pt.PersonTracker()

        time.sleep(5)

        # read the data.json files which contains the results of the eyepop inference
        json_data = open("data.json", "r")
        json_data = json.load(json_data)

        #
        #  1. iterate through the eyepop results and add the people to the person tracker
        #
        for result in json_data:

            source_width = result['source_width']
            source_height = result['source_height']

            sports_ball_location = {
                'x': -1, 'y': -1, 'width': -1, 'height': -1}

            # skip any empty results
            if 'objects' not in result:
                continue

            # find the sports ball location
            for obj in result['objects']:

                if obj['classLabel'] == 'sports ball':

                    sports_ball_location['x'] = obj['x']
                    sports_ball_location['y'] = obj['y']
                    sports_ball_location['width'] = obj['width']
                    sports_ball_location['height'] = obj['height']

            # iterate through the people in the video
            for obj in result['objects']:

                if obj['classLabel'] != 'person':
                    continue

                # Out primary data points for the players
                ball_distance = -1
                label = None
                trace_id = None

                # grab the first label from the person if it exists
                if 'objects' in obj:
                    for label in obj['objects']:
                        if label['classLabel'] == 'text' and 'labels' in label and len(label['labels']) > 0:
                            label = label['labels'][0]['label']

                # grab the trace id from the person if it exists
                if 'traceId' in obj:
                    trace_id = obj['traceId']

                # calculate the distance between the person and the ball in %
                if sports_ball_location['x'] != -1:
                    x1 = (
                        sports_ball_location['x'] + (sports_ball_location['width'] / 2)) / source_width
                    y1 = (
                        sports_ball_location['y'] + (sports_ball_location['height'] / 2)) / source_height

                    x2 = (obj['x'] + (obj['width'] / 2)) / source_width
                    y2 = (obj['y'] + (obj['height'] / 2)) / source_height

                    ball_distance = abs(((x1 - x2)**2 + (y1 - y2)**2)**0.5)

                # if there is no trace id, we ignore the person
                if (trace_id == None):
                    continue

                # if the ball distance is 50% or more of the screen width, we ignore the person
                if ball_distance > 0.5 or ball_distance == -1:
                    continue

                # add the person to the person tracker
                person_tracker.add_person(
                    label=label,
                    trace_id=trace_id,
                    frame_time=result['seconds'],
                    bounds=[obj['x'], obj['y'],
                            obj['width'], obj['height']]
                )

        # filter and consolidate the people in the person tracker
        person_tracker.filter_map()

        #
        #   2. create the output videos
        #
        for key in person_tracker.people.keys():
            person = person_tracker.people[key]

            # skip any people with no labels
            if len(person['labels']) <= 0:
                continue

            if target_jersey_number and target_jersey_number not in person['labels']:
                continue

            if len(person['seconds']) > (30):
                print(person['labels'], person['time_segments'])

                file_name = './player_'

                # we check if the person has any labels and the label is a single numeric digit
                if len(person['labels']) > 0:
                    # flatten the labels array to a string with _ between each label and remove special characters
                    file_name += '_'.join(person['labels'])
                    file_name = ''.join(
                        e for e in file_name if e.isalnum() or e == '_')
                else:
                    file_name += "____" + key

                file_name += '.mp4'

                print(video_file_path, file_name, person['time_segments'])

                mm.splice_video_with_dynamic_rectangles(
                    video_file_path, file_name, person['time_segments'], person['bounds'])

                time.sleep(10)

    t1 = time.time()
    upload_video(video_file_path)
    t2 = time.time()
    print("1x video async: ", t2 - t1)


# adds command line arguments allowing the user to specify the video file path
#  and a target jersey number that is compared against the detected labels
args = ap.ArgumentParser()
args.add_argument("--video", type=str, default='./Video.MOV')
args.add_argument("--target", type=str, default=None, nargs='?')
args.add_argument("--analyze", action="store_true")
args = args.parse_args()

print(args)

main(args.video, args.target, analyze=args.analyze)
