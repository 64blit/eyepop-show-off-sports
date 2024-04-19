import cv2


class VideoTools:

    def __init__(self, video_path):
        self.video_path = video_path
        self.video_capture = cv2.VideoCapture(video_path)

    def get_image_at_time(self, time_in_seconds):
        self.video_capture.set(cv2.CAP_PROP_POS_MSEC, time_in_seconds * 1000)
        success, frame = self.video_capture.read()
        if success:
            return frame
        else:
            return None

    def get_average_color(self, x, y, width, height, time_in_seconds):
        frame = self.get_image_at_time(time_in_seconds)
        if frame is not None:
            # Crop the frame
            roi = frame[y:y+height, x:x+width]
            # Calculate the average color
            average_color = cv2.mean(roi)[:3]
            return average_color
        else:
            return None

    @staticmethod
    def are_colors_close(color1, color2, threshold):
        distance = sum((c1 - c2) ** 2 for c1, c2 in zip(color1, color2)) ** 0.5
        return distance <= threshold

    def release(self):
        self.video_capture.release()
