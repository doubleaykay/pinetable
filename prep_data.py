from timetable import crawl_timetable
import json
from datetime import datetime as dt

# get courses
term = '21S'
courses = crawl_timetable(term)

# add numeric ID to courses
i = 1
for course in courses:
    course['id'] = i
    i += 1

# dump course data to json
with open('courses.json', 'w+') as f:
    f.write(json.dumps(courses))

# dump build data to json
with open('build_data.json', 'w+') as f:
    f.write(json.dumps({
        'build_time': dt.now().strftime("%m/%d/%Y, %H:%M:%S")
    }))