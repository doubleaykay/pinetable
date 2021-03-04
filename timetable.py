import re
from bs4 import BeautifulSoup
import json
from urllib.request import urlopen


TIMETABLE_URL = (
    "http://oracle-www.dartmouth.edu/dart/groucho/timetable.display_courses")

DATA_TO_SEND = (
    "distribradio=alldistribs&depts=no_value&periods=no_value&"
    "distribs=no_value&distribs_i=no_value&distribs_wc=no_value&deliverymodes=no_value&pmode=public&"
    "term=&levl=&fys=n&wrt=n&pe=n&review=n&crnl=no_value&classyear=2008&"
    "searchtype=Subject+Area%28s%29&termradio=selectterms&terms=no_value&"
    "deliveryradio=selectdelivery&subjectradio=selectsubjects&hoursradio=allhours&sortorder=dept"
    "&terms={term}"
)

COURSE_TITLE_REGEX = re.compile(
    "(.*?)(?:\s\(((?:Remote|On Campus|Individualized)[^\)]*)\))?(\(.*\))?$")

DEPARTMENT_CORRECTIONS = {
    "M&SS": "QSS",
    "WGST": "WGSS"
}

term_regex = re.compile("^(?P<year>[0-9]{2})(?P<term>[WSXFwsxf])$")

def crawl_timetable(term):
    """
    Timetable HTML is malformed. All table rows except the head do not have
    a proper starting <tr>, which requires us to:

    1. Iterate over <td></td> in chunks rather than by <tr></tr>
    2. Remove all </tr> in the table, which otherwise breaks BeautifulSoup into
       not allowing us to iterate over all the <td></td>

    To iterate over the <td></td> in chunks, we get the number of columns,
    put all of the <td></td> in a generator, and pull the number of columns
    from the generator to get the row.
    """
    course_data = []
    request_data = DATA_TO_SEND.format(term=_get_timetable_term_code(term))
    request_data = request_data.encode("utf-8")
    soup = retrieve_soup(
        TIMETABLE_URL,
        data=request_data,
        preprocess=lambda x: re.sub("</tr>", "", x.decode('utf-8')),
    )
    num_columns = len(soup.find(class_="data-table").find_all("th"))
    assert num_columns == 20

    tds = soup.find(class_="data-table").find_all("td")
    assert len(tds) % num_columns == 0

    td_generator = (td for td in tds)
    for _ in range(int(len(tds) / num_columns)):
        tds = [next(td_generator) for _ in range(int(num_columns))]

        number, subnumber = parse_number_and_subnumber(tds[3].get_text())
        crosslisted_courses = _parse_crosslisted_courses(
            tds[7].get_text(strip=True))

        title_match = COURSE_TITLE_REGEX.match(tds[5].get_text(strip=True)
            .encode('ascii', 'ignore').decode('ascii'))

        title = title_match.group(1)
        if title_match.group(3):
            title += " " + title_match.group(3)

        course_data.append({
            "term": _convert_timetable_term_to_term(
                tds[0].get_text(strip=True)),
            "crn": int(tds[1].get_text(strip=True)),
            "program": tds[2].get_text(strip=True),
            "number": number,
            "subnumber": subnumber,
            "section": int(tds[4].get_text(strip=True)),
            "title": title,
            "delivery_mode": title_match.group(2),
            "crosslisted": crosslisted_courses,
            "period": tds[8].get_text(strip=True),
            "room": tds[10].get_text(strip=True),
            "building": tds[11].get_text(strip=True),
            "instructor": _parse_instructors(tds[12].get_text(strip=True)),
            "world_culture": tds[13].get_text(strip=True),
            "distribs": _parse_distribs(tds[14].get_text(strip=True)),
            "limit": int_or_none(tds[15].get_text(strip=True)),
            "enrollment": int_or_none(tds[16].get_text(strip=True)),
            "status": tds[17].get_text(strip=True),
        })
        
    return course_data


def _parse_crosslisted_courses(xlist_text):
    crosslisted_courses = []
    for course_text in (xlist_text.split(",") if xlist_text else []):
        program, numbers, section = course_text.split()
        number, subnumber = parse_number_and_subnumber(numbers)
        section = int(section)
        crosslisted_courses.append({
            "program": program,
            "number": number,
            "subnumber": subnumber,
            "section": section,
        })
    return crosslisted_courses


def _convert_timetable_term_to_term(timetable_term):
    assert len(timetable_term) == 6
    assert timetable_term[:2] == "20"
    month = int(timetable_term[-2:])
    year = timetable_term[2:4]
    return "{year}{season}".format(
        year=year, season={1: "W", 3: "S", 6: "X", 9: "F"}[month])


def _parse_distribs(distribs_text):
    return distribs_text.split(" or ") if distribs_text else []


def _parse_instructors(instructors):
    return instructors.split(", ") if instructors else []


def _get_timetable_term_code(term):
    year, term = split_term(term)
    return "20{year}0{term_number}".format(
        year=year,
        term_number={"w": 1, "s": 3, "x": 6, "f": 9}[term.lower()],
    )


def int_or_none(string):
    return int(string) if string else None


def parse_number_and_subnumber(numbers_text):
    numbers = numbers_text.split(".")
    if len(numbers) == 2:
        return (int(n) for n in numbers)
    else:
        assert len(numbers) == 1
        return int(numbers[0]), None


def retrieve_soup(url, data=None, preprocess=lambda x: x):
    return BeautifulSoup(
        preprocess(urlopen(url, data=data).read()), "html.parser")


def split_term(term):
    term_data = term_regex.match(term)
    if term_data and term_data.group("year") and term_data.group("term"):
        year = int(term_data.group("year"))
        term = term_data.group("term").upper()
        return year, term
    else:
        raise ValueError