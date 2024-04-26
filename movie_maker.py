from moviepy.editor import VideoFileClip, concatenate_videoclips, CompositeVideoClip, ColorClip, transfx
from moviepy.video.VideoClip import VideoClip
import os
import subprocess
import numpy as np
import cv2
import subprocess

sprite = cv2.imread(
    "indicator.png", cv2.IMREAD_UNCHANGED)


def get_bounds_at_time(time_bounds, t):
    """ Interpolate or retrieve bounds at given time `t`. """
    closest_time = min(time_bounds.keys(), key=lambda x: abs(x - t))
    return time_bounds[closest_time]


def create_video(video_path, output_video_path, segments, bounds, resolution=(720, 720), draw_bounds=False):

    video_file_name = os.path.basename(video_path)
    video_file_name = ''.join(e for e in video_file_name if e.isalnum())

    cap = cv2.VideoCapture(video_path)
    frame_rate = cap.get(cv2.CAP_PROP_FPS)

    output_folder = 'output\\' + output_video_path + '_temp\\'

    print(video_file_name, video_path, output_video_path, output_folder)

    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    dst = False
    count = 0

    for i, (start, end) in enumerate(segments):

        for t in np.arange(start, end, 1.0 / frame_rate):
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(t * frame_rate))
            ret, frame = cap.read()
            output = None

            if not ret:
                print("Error reading frame: " + str(t))
                break

            if not dst:
                dst = {}
                dst['padding'] = 5
                dst['min_dim'] = min(resolution)
                dst['size'] = dst['min_dim'] - 2 * dst['padding']
                dst['x_center'] = resolution[1] // 2
                dst['y_center'] = resolution[0] // 2
                dst['x_start'] = dst['x_center'] - dst['size'] // 2
                dst['x_end'] = dst['x_start'] + dst['size']
                dst['y_start'] = dst['y_center'] - dst['size'] // 2
                dst['y_end'] = dst['y_start'] + dst['size']

            blursrc = {}
            blursrc['x_center'] = frame.shape[1] // 2
            blursrc['y_center'] = frame.shape[0] // 2
            frame_to_output_width_ratio = frame.shape[1] / resolution[1]
            frame_to_output_height_ratio = frame.shape[0] / resolution[0]
            output_to_frame_scale = min(
                frame_to_output_width_ratio, frame_to_output_height_ratio)
            blursrc['w'] = int(resolution[1] * output_to_frame_scale)
            blursrc['h'] = int(resolution[0] * output_to_frame_scale)
            blursrc['x_start'] = blursrc['x_center'] - blursrc['w'] // 2
            blursrc['x_end'] = blursrc['x_start'] + blursrc['w']
            blursrc['y_start'] = blursrc['y_center'] - blursrc['h'] // 2
            blursrc['y_end'] = blursrc['y_start'] + blursrc['h']

            bounds_at_time = get_bounds_at_time(bounds, t)
            x1, y1, w, h = bounds_at_time[0], bounds_at_time[1], bounds_at_time[2], bounds_at_time[3]

            count += 1
            padding = 50

            min_frame_dim = min(frame.shape[:2])

            if draw_bounds:

                cv2.rectangle(frame, (int(x1), int(y1)),
                              (int(x1 + w), int(y1 + h)), (0, 255, 0), 2)

            # calculate the size of the region of interest, keeping it a square
            max_roi_dim = max(w, h)
            desired_roi_size = int(max_roi_dim + 2 * padding)
            roi_size = min(desired_roi_size, min_frame_dim)
            half_roi = roi_size // 2
            bounds_center_x = int(x1 + w / 2)
            bounds_center_y = int(y1 + h / 2)

            # clamped region of interest inside frame, preserving size
            roi_center_x = min(max(half_roi, bounds_center_x),
                               frame.shape[1] - half_roi)
            roi_center_y = min(max(half_roi, bounds_center_y),
                               frame.shape[0] - half_roi)

            # new start and end coordinates for the region of interest based on frame size
            x_start = int(max(0, roi_center_x - half_roi))
            y_start = int(max(0, roi_center_y - half_roi))
            x_end = int(x_start + roi_size)
            y_end = int(y_start + roi_size)

            cropped_frame = frame[y_start:y_end, x_start:x_end]

            # Load the sprite image
            sprite_width = int(w * 0.1)  # Adjust the scale factor as needed
            sprite_height = int(sprite_width)  # Load the sprite image

            # Calculate the new coordinates relative to the cropped region,
            #  keeping x1 in the center of the entire frame
            new_x1 = int((x_start - w/2) + sprite_width/2)

            # Calculate the position of the sprite
            sprite_x = new_x1
            sprite_y = int(y1 - y_start + padding - 50)

            sprite_resized = cv2.resize(sprite, (sprite_width, sprite_height))

            # Paste the sprite onto the frame, keeping it in bounds
            sprite_height, sprite_width, _ = sprite_resized.shape
            sprite_x = max(sprite_x, 0)
            sprite_y = max(sprite_y, 0)
            sprite_x = min(sprite_x, cropped_frame.shape[1] - sprite_width)
            sprite_y = min(sprite_y, cropped_frame.shape[0] - sprite_height)

            # Add the sprite to the cropped frame, respecting alpha channel
            alpha = sprite_resized[:, :, 3] / 255.0
            foreground = sprite_resized[:, :, :3]
            background = cropped_frame[sprite_y:sprite_y + sprite_height,
                                       sprite_x:sprite_x + sprite_width, :]

            # Expand the dimensions of alpha to match the shape of foreground and background
            alpha_expanded = np.expand_dims(alpha, axis=2)

            # Multiply alpha_expanded with foreground and (1 - alpha_expanded) with background
            blended = (alpha_expanded * foreground +
                       (1 - alpha_expanded) * background).astype(np.uint8)

            cropped_frame[sprite_y:sprite_y + sprite_height,
                          sprite_x:sprite_x + sprite_width, :] = blended

            # fill in the rest of the frame with a blurred version of the frame
            blurred_frame = cv2.blur(frame, (51, 51))
            blurred_frame = cv2.resize(
                blurred_frame, [frame.shape[1], frame.shape[0]])

            output = cv2.resize(
                blurred_frame[blursrc['y_start']:blursrc['y_end'], blursrc['x_start']:blursrc['x_end']], (resolution[1], resolution[0]))

            cropped_resized = cv2.resize(
                cropped_frame, (dst['size'], dst['size']))
            output[dst['y_start']:dst['y_end'],
                   dst['x_start']:dst['x_end']] = cropped_resized

            print(f"Writing frame {
                  t} to " + os.path.join(output_folder, str(count).zfill(4) + ".jpg"))

            cv2.imwrite(os.path.join(output_folder, str(
                count).zfill(4) + ".jpg"), output)

            cv2.imshow('frame', output)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                exit()
                break

    cap.release()

    combine_images_to_video(
        output_folder, f"output\\{video_file_name}_{output_video_path}.mp4", resolution=resolution, fps=frame_rate)


def combine_images_to_video(image_folder, output_path, resolution, fps):
    current_path = os.path.dirname(os.path.abspath(__file__))
    ffmpeg_cmd = [
        "ffmpeg",
        "-r", str(int(fps)),
        "-i", os.path.join(current_path, image_folder, "%04d.jpg"),
        "-c:v", "libx264",
        "-vf", f"fps={int(fps)}",
        "-pix_fmt", "yuv420p",
        os.path.join(current_path, output_path),
        '-y'
    ]

    print('\n\n\n\n\n\n\n\n', ' '.join(ffmpeg_cmd), '\n\n\n\n\n\n\n\n')

    subprocess.run(ffmpeg_cmd, check=True)

    # Delete the image folder
    subprocess.run(["cmd", "/c", "rmdir", "/s", "/q",
                   os.path.join(current_path, image_folder)])
