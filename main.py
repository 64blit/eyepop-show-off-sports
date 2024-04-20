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


def main(video_file_path: str, target_jersey_number: str, analyze=False, smoothing=20, draw_bounds=False, debug=False):

    def upload_video(video_path: str):
        #
        #  0. Obtain the EyePop inference data from the video
        #
        if analyze:
            print("Analyzing video")
            em.get_inference_data(video_path)

        # The PersonTracker class is used to track people in the video
        person_tracker = pt.PersonTracker(smoothing=smoothing)

        time.sleep(1)

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
                labels = []
                trace_id = None

                # grab the labels from the person if it exists
                if 'objects' in obj:
                    for child in obj['objects']:
                        if child['classLabel'] == 'text' and 'labels' in child and len(child['labels']) > 0:
                            # flattens the labels objects into a list of strings from child['labels'][i]['label]
                            child_labels = [label['label']
                                            for label in child['labels']]
                            labels.extend(child_labels)

                # grab the trace id from the person if it exists
                if 'traceId' in obj:
                    trace_id = obj['traceId']

                # expand the bounds of the person to contain the sports ball location
                if sports_ball_location['x'] != -1:
                    diff_x = abs(sports_ball_location['x'] + obj['x'])
                    diff_y = abs(sports_ball_location['y'] + obj['y'])

                    obj['x'] = min(obj['x'], sports_ball_location['x'])
                    obj['y'] = min(obj['y'], sports_ball_location['y'])

                    obj['width'] = obj['width'] + \
                        sports_ball_location['width'] + \
                        diff_x

                    obj['height'] = obj['height'] + \
                        sports_ball_location['height'] + \
                        diff_y

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

                # # if the ball distance is 20% or more of the screen width, we ignore the person
                # if ball_distance > 0.6 or ball_distance == -1:
                #     continue

                # add the person to the person tracker
                person_tracker.add_person(
                    labels=labels,
                    trace_id=trace_id,
                    frame_time=result['seconds'],
                    bounds=[obj['x'], obj['y'],
                            obj['width'], obj['height']]
                )

        # filter and consolidate the people in the person tracker
        person_tracker.filter_map()

        if (debug):
            # print all the keys in the person tracker
            for key in person_tracker.people.keys():
                if len(person_tracker.people[key]['seconds']) > 30:
                    print('Player found:', key,  ' frames detected: ',
                          len(person_tracker.people[key]['seconds']))
            return

        #
        #   2. create the output videos
        #
        for key in person_tracker.people.keys():
            person = person_tracker.people[key]

            if target_jersey_number and target_jersey_number != key:
                continue

            # if the player has less than 30 frames of video, we ignore them
            if len(person['seconds']) < 30:
                continue

            file_name = 'player_' + key + '.mp4'

            print(video_file_path, file_name, person['time_segments'])

            time.sleep(1)

            mm.create_video(video_file_path, file_name,
                            person['time_segments'], person['bounds'], resolution=(720, 800), draw_bounds=draw_bounds)

    upload_video(video_file_path)


# adds command line arguments allowing the user to specify the video file path
#  and a target jersey number that is compared against the detected labels
args = ap.ArgumentParser()
args.add_argument("--video", type=str, default='./Video.MOV')
args.add_argument("--target", type=str, default=None, nargs='?')
args.add_argument("--analyze", action="store_true")
args.add_argument("--smoothing", type=float, default=.99, nargs='?')
args.add_argument("--draw_bounds", action="store_true")
args.add_argument("--debug", action="store_true")
args = args.parse_args()

print(args)

main(args.video, args.target, analyze=args.analyze,
     smoothing=args.smoothing, draw_bounds=args.draw_bounds, debug=args.debug)
