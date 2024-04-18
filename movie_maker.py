from moviepy.editor import VideoFileClip, concatenate_videoclips, CompositeVideoClip, ColorClip, transfx
from moviepy.video.VideoClip import VideoClip


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


def splice_video_with_dynamic_rectangles(video_path, file_name, segments, time_bounds, rectangle_color=(255, 0, 0), rectangle_opacity=0.85):
    clip = VideoFileClip(video_path)
    annotated_clips = []
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

    # Concatenate all annotated clips
    final_clip = concatenate_videoclips(annotated_clips, method="compose")
    final_clip.write_videofile('./output/' + file_name, codec="libx264")
