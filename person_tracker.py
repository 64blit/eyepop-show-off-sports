import numpy as np
import scipy.signal

# A PersonTracker class which has a map of people, where the key is a traceID and the values are the person's jersey number and the number of frames the person has been in the video. The class should have the following methods:
#
# person_tracker.py
#


class PersonTracker:

    def __init__(self, smoothing=20):
        self.people = {}
        self.smoothing = smoothing

    # add a person to the people map
    def add_person(self, labels: [], trace_id: int, frame_time: float, bounds: []) -> None:

        # If there are not labels, we try to find the person by trace_id
        #   This may introduce error if the traceID Jumps from one player to another
        if len(labels) == 0:
            for person in self.people:
                if trace_id in self.people[person]['ids']:
                    labels.append(person)
                    break

        for label in labels:

            if not label or not type(label) == str or not label.isnumeric():
                continue

            if label not in self.people:

                self.people[label] = {
                    'ids': [trace_id],
                    'seconds': [],
                    'time_segments': [],
                    'bounds': {},
                }

            self.people[label]['ids'].append(trace_id)
            self.people[label]['seconds'].append(frame_time)
            self.people[label]['bounds'][frame_time] = bounds

    def filter_map(self, threshold=2):
        # self.consolidate_people()
        self.filter_times(threshold)
        self.smooth_bounds()

    # combine any people entries with the same jersey number, and remove the duplicates
    def consolidate_people(self):
        people = self.people

        for person in people:

            for other_person in people:

                people[person]['seconds'].extend(
                    people[other_person]['seconds'])
                people[person]['seconds'].sort()

                people[person]['bounds'].update(
                    people[other_person]['bounds'])

                people[person]['ids'].extend(
                    people[other_person]['ids'])

                people[other_person]['ids'] = []

        people_to_remove = []

        for person in people:

            # next we remove duplicate labels
            people[person]['ids'] = list(set(people[person]['ids']))
            people[person]['seconds'] = list(
                set(people[person]['seconds']))
            people[person]['seconds'].sort()

            # add the person to the removal list if they have no labels
            if people[person]['ids'] == []:
                people_to_remove.append(person)

        # remove the people with no labels
        for person in people_to_remove:
            del people[person]

    # consolidate person time list into segments of times in tuples with a threshold of seconds
    def filter_times(self, threshold=2):

        for key in self.people.keys():

            times = self.people[key]['seconds']
            start_time = times[0]

            for j in range(1, len(times)):
                if times[j] - times[j - 1] > threshold:
                    self.people[key]['time_segments'].append(
                        (start_time, times[j - 1]))
                    start_time = times[j]

            # Add the last segment
            self.people[key]['time_segments'].append((start_time, times[-1]))

    def average_bounds(self):
        if self.smoothing <= 0:
            return

        for key in self.people.keys():
            bounds = self.people[key]['bounds']
            seconds = self.people[key]['seconds']

            for second in seconds:
                closest_times = sorted(
                    bounds.keys(), key=lambda x: abs(x - second))[:30]

                x_values = []
                y_values = []
                w_values = []
                h_values = []

                for time in closest_times:
                    x1, y1, w, h = bounds[time]
                    x_values.append(x1)
                    y_values.append(y1)
                    w_values.append(w)
                    h_values.append(h)

                x_mean = np.mean(x_values)
                y_mean = np.mean(y_values)
                w_mean = np.mean(w_values)
                h_mean = np.mean(h_values)

                bounds[closest_times[0]] = [
                    x_mean, y_mean, w_mean, h_mean]

    def smooth_bounds(self):
        if self.smoothing <= 0.0:
            return

        self.average_bounds()

        alpha = self.smoothing  # Smoothing factor. Adjust this to increase or decrease smoothing

        for key in self.people.keys():
            bounds = self.people[key]['bounds']
            seconds = self.people[key]['seconds']
            ema_bounds = {}

            sorted_seconds = sorted(seconds)
            if sorted_seconds:
                ema_bounds[sorted_seconds[0]] = bounds[sorted_seconds[0]]

            for i in range(1, len(sorted_seconds)):
                current_time = sorted_seconds[i]
                previous_time = sorted_seconds[i - 1]

                previous_bounds = ema_bounds[previous_time]
                current_bounds = bounds[current_time]

                x1, y1, w, h = current_bounds
                prev_x, prev_y, prev_w, prev_h = previous_bounds

                # Calculate the exponential moving average
                x_mean = alpha * x1 + (1 - alpha) * prev_x
                y_mean = alpha * y1 + (1 - alpha) * prev_y
                w_mean = alpha * w + (1 - alpha) * prev_w
                h_mean = alpha * h + (1 - alpha) * prev_h

                ema_bounds[current_time] = [x_mean, y_mean, w_mean, h_mean]

            # Update the original bounds with the smoothed values
            bounds.update(ema_bounds)
