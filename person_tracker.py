# A PersonTracker class which has a map of people, where the key is a traceID and the values are the person's jersey number and the number of frames the person has been in the video. The class should have the following methods:
#
# person_tracker.py
#

class PersonTracker:

    def __init__(self):
        self.people = {}

    # add a person to the people map
    def add_person(self, label: str, trace_id: int, frame_time: float, bounds: []) -> None:

        trace_id = str(trace_id)

        if trace_id not in self.people:
            self.people[trace_id] = {
                'labels': [],
                'seconds': [],
                'time_segments': [],
                'bounds': {},
            }

        if label and type(label) == str:
            self.people[trace_id]['labels'].append(label)

        self.people[trace_id]['seconds'].append(frame_time)
        self.people[trace_id]['bounds'][frame_time] = bounds

    def filter_map(self, threshold=10):
        self.consolidate_people()
        self.filter_times(threshold)

    # combine any people entries with the same jersey number, and remove the duplicates
    def consolidate_people(self):
        people = self.people

        for person in people:

            for other_person in people:

                if person != other_person:

                    if people[person]['labels'] == []:
                        continue

                    if people[other_person]['labels'] == []:
                        continue

                    # next we check if any of the other person labels match the current person labels
                    if not any(label in people[person]['labels'] for label in people[other_person]['labels']):
                        continue

                    people[person]['seconds'].extend(
                        people[other_person]['seconds'])
                    people[person]['seconds'].sort()

                    people[person]['bounds'].update(
                        people[other_person]['bounds'])

                    people[other_person]['seconds'] = []
                    people[other_person]['labels'] = []
                    people[other_person]['bounds'] = {}

        people_to_remove = []
        for person in people:
            # next we remove duplicate labels
            people[person]['labels'] = list(set(people[person]['labels']))

            # add the person to the removal list if they have no labels
            if people[person]['labels'] == []:
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
