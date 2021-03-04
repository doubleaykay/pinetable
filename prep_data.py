from timetable import crawl_timetable
import json

term = '21S'

courses = crawl_timetable(term)

i = 1
for course in courses:
    course['id'] = i
    i += 1

with open('courses.json', 'w+') as f:
    f.write(json.dumps(courses))