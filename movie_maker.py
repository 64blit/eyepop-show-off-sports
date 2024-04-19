from moviepy.editor import VideoFileClip, concatenate_videoclips, CompositeVideoClip, ColorClip, transfx
from moviepy.video.VideoClip import VideoClip
import os
import subprocess
import numpy as np
import cv2


def splice_and_crop_video_with_transitions(video_path, output_path, segments, transition_duration=.2):
    clip = VideoFileClip(video_path)
    cropped_clips = []
    for start, end in segments:  # (x1, y1, x2, y2)
        # .crop(x1=x1, y1=y1, x2=x2, y2=y2)
        subclip = clip.subclip(start, end)
        cropped_clips.append(subclip)

    # Adding transitions between clips
    final_clips = [cropped_clips[0]]
    for i in range(1, len(cropped_clips)):
        transition = transfx.crossfadein(
            cropped_clips[i], duration=transition_duration)
        final_clips.append(transition)

    final_clip = concatenate_videoclips(
        final_clips, method="compose", padding=-transition_duration)
    final_clip.write_videofile(output_path, codec="libx264")


def get_bounds_at_time(time_bounds, t):
    """ Interpolate or retrieve bounds at given time `t`. """
    closest_time = min(time_bounds.keys(), key=lambda x: abs(x - t))
    return time_bounds[closest_time]


def rectangle_bounds(t, time_bounds):
    """ Return the position of the rectangle at time `t`. """
    bounds = get_bounds_at_time(time_bounds, t)
    x1, y1, w, h = bounds[0], bounds[1], bounds[2], bounds[3]
    return (x1, y1, w, h)


def splice_video_with_dynamic_rectangles(video_path, file_name, segments, time_bounds, rectangle_color=(255, 0, 0), rectangle_opacity=0.5):
    clip = VideoFileClip(video_path)
    clip = VideoFileClip(video_path)
    annotated_clips = []
    subclip = clip.subclip(start, end)

    for start, end in segments:
        subclip = clip.subclip(start, end)

        # Create a rectangle that will move according to the frame-specific bounds
        initial_bounds = get_bounds_at_time(time_bounds, start)
        rectangle = ColorClip(size=(int(initial_bounds[2]), int(
            initial_bounds[3])), color=rectangle_color, duration=.25, ismask=False)
        rectangle = rectangle.set_opacity(rectangle_opacity)
        rectangle = rectangle.set_position(
            (initial_bounds[0], initial_bounds[1]))

        # Overlay the rectangle on the subclip
        annotated_clip = CompositeVideoClip([subclip, rectangle])
        annotated_clips.append(annotated_clip)

    # get the filename from the video path and remove all non alphanumeric characters
    video_file_name = os.path.basename(video_path)
    video_file_name = ''.join(e for e in video_file_name if e.isalnum())

    # Concatenate all annotated clips
    clip = concatenate_videoclips(annotated_clips, method="compose")

    # Save the annotated video
    output_path = f"{file_name}.mp4"
    clip.write_videofile(output_path, codec="libx264")


# creates a video file with the segments of the video and zooms into the bounds of the segment
#  The bounds parameter is a time sequenced dictionary of the bounds of the object in the video.#  They look like this: {second: {x: x, y: y, width: width, height: height}} that has an entry
#   for each decoded frame time of the video. This function will create a video file of a given aspect ratio which fills the frame with the object at the given bounds and maintains the aspect ratio of the object. Adding a blurred background of the video to fill the empty space.
def create_video(video_path, output_video_path, segments, bounds, resolution=(720, 720)):

    video_file_name = os.path.basename(video_path)
    video_file_name = ''.join(e for e in video_file_name if e.isalnum())

    cap = cv2.VideoCapture(video_path)
    frame_rate = cap.get(cv2.CAP_PROP_FPS)

    output_folder = 'output/' + output_video_path + '_temp/'

    print(video_file_name, video_path, output_video_path, output_folder)

    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    dst = False

    for i, (start, end) in enumerate(segments):
        segment_folder = os.path.join(
            output_folder, f"segment_{i}")
        os.makedirs(segment_folder, exist_ok=True)

        for t in np.arange(start, end, 1 / frame_rate):
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(t * frame_rate))
            ret, frame = cap.read()

            # print(t, ret, frame.shape)

            if not ret:
                print("Error reading frame: " + str(t))
                break

            if not dst:
                dst = {
                    'min_dim': min(frame.shape[:2]),
                    'padding': 50,
                    'full_size': resolution[0]
                }
                dst['size'] = resolution[0] - 2 * dst['padding']
                dst['center'] = dst['full_size'] // 2
                dst['x_start'] = dst['center'] - dst['size'] // 2
                dst['x_end'] = dst['x_start'] + dst['size']
                dst['y_start'] = dst['center'] - dst['size'] // 2
                dst['y_end'] = dst['y_start'] + dst['size']
            resolution = (dst['full_size'], dst['full_size'])

            bounds_at_time = get_bounds_at_time(bounds, t)
            x1, y1, w, h = bounds_at_time[0], bounds_at_time[1], bounds_at_time[2], bounds_at_time[3]

            if (w < 120 or h < 120):
                continue

            padding = 20

            min_frame_dim = min(frame.shape[:2])
            max_roi_dim = max(w, h)
            desired_roi_size = int(max_roi_dim + 2 * padding)
            roi_size = min(desired_roi_size, min_frame_dim)
            half_roi = roi_size // 2
            bounds_center_x = int(x1 + w / 2)
            bounds_center_y = int(y1 + h / 2)
            roi_center_x = min(max(half_roi, bounds_center_x),
                               frame.shape[1] - half_roi)
            roi_center_y = min(max(half_roi, bounds_center_y),
                               frame.shape[0] - half_roi)
            x_start = int(max(0, roi_center_x - half_roi))
            y_start = int(max(0, roi_center_y - half_roi))
            x_end = int(x_start + roi_size)
            y_end = int(y_start + roi_size)

            cropped_frame = frame[y_start:y_end, x_start:x_end]

            # fill in the rest of the frame with a blurred version of the frame
            blurred_frame = cv2.blur(cropped_frame, (51, 51))
            blurred_frame = cv2.resize(
                blurred_frame, (dst['size'] + 2 * dst['padding'], dst['size'] + 2 * dst['padding']))

            cropped_resized = cv2.resize(
                cropped_frame, (dst['size'], dst['size']))
            blurred_frame[dst['y_start']:dst['y_end'],
                          dst['x_start']:dst['x_end']] = cropped_resized

            # print(f"Writing frame {t} to {segment_folder}/{t}.jpg")
            cv2.imwrite(os.path.join(segment_folder,
                        f"{t}.jpg"), blurred_frame)

    cap.release()

    combine_images_to_video(
        output_folder, f"output/{video_file_name}_{output_video_path}.mp4", resolution=resolution, fps=frame_rate)


def resizeAndPad(img, size, padColor=0):

    h, w = img.shape[:2]
    sh, sw = size

    # interpolation method
    if h > sh or w > sw:  # shrinking image
        interp = cv2.INTER_AREA
    else:  # stretching image
        interp = cv2.INTER_CUBIC

    # aspect ratio of image
    # if on Python 2, you might need to cast as a float: float(w)/h
    aspect = w/h

    # compute scaling and pad sizing
    if aspect > 1:  # horizontal image
        new_w = sw
        new_h = np.round(new_w/aspect).astype(int)
        pad_vert = (sh-new_h)/2
        pad_top, pad_bot = np.floor(pad_vert).astype(
            int), np.ceil(pad_vert).astype(int)
        pad_left, pad_right = 0, 0
    elif aspect < 1:  # vertical image
        new_h = sh
        new_w = np.round(new_h*aspect).astype(int)
        pad_horz = (sw-new_w)/2
        pad_left, pad_right = np.floor(pad_horz).astype(
            int), np.ceil(pad_horz).astype(int)
        pad_top, pad_bot = 0, 0
    else:  # square image
        new_h, new_w = sh, sw
        pad_left, pad_right, pad_top, pad_bot = 0, 0, 0, 0

    # set pad color
    # color image but only one color provided
    if len(img.shape) is 3 and not isinstance(padColor, (list, tuple, np.ndarray)):
        padColor = [padColor]*3

    # scale and pad
    scaled_img = cv2.resize(img, (new_w, new_h), interpolation=interp)
    scaled_img = cv2.copyMakeBorder(
        scaled_img, pad_top, pad_bot, pad_left, pad_right, borderType=cv2.BORDER_CONSTANT, value=padColor)

    return scaled_img


def combine_images_to_video(image_folder, output_path, resolution, fps):
    images = []
    for root, dirs, files in os.walk(image_folder):
        for file in files:
            if file.endswith(".jpg"):
                image_path = os.path.join(root, file)
                images.append(image_path)

    images.sort()

    width, height = resolution
    aspect_ratio = float(width) / float(height)

    video = cv2.VideoWriter(
        output_path, cv2.VideoWriter_fourcc(*'MPV4'), fps, (width, height))

    for image_path in images:
        image = cv2.imread(image_path)

        video.write(image)

        cv2.imshow("Image", image)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            cv2.destroyAllWindows()
            video.release()
            exit()
            break

    video.release()
