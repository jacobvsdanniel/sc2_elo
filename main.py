import os
import re
import csv
import sys
import time
import logging
import argparse
from datetime import date
from xml.etree import ElementTree as ET
from collections import deque, defaultdict

import requests

logger = logging.getLogger(__name__)
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    datefmt="%Y/%m/%d %H:%M:%S",
    level=logging.INFO,
)
csv.register_dialect(
    "pandas", delimiter=",", quoting=csv.QUOTE_MINIMAL, quotechar='"', doublequote=True,
    escapechar=None, lineterminator="\n", skipinitialspace=False,
)


def read_lines(file):
    with open(file, "r", encoding="utf8") as f:
        line_list = f.read().splitlines()
    lines = len(line_list)
    logger.info(f"Read {lines:,} lines from {file}")
    return line_list, lines


def read_csv(file, dialect):
    with open(file, "r", encoding="utf8", newline="") as f:
        reader = csv.reader(f, dialect=dialect)
        row_list = [row for row in reader]
    return row_list


def write_csv(file, dialect, row_list):
    with open(file, "w", encoding="utf8", newline="") as f:
        writer = csv.writer(f, dialect=dialect)
        for row in row_list:
            writer.writerow(row)
    return


def get_year_to_div_from_html(html, first_year, last_year):
    last_year_header = f'<h4><span class="mw-headline" id="{last_year}">{last_year}</span></h4>'
    for line_index, line in enumerate(html):
        if line == last_year_header:
            break
    else:
        raise AssertionError

    year_to_div = {}
    for year in range(first_year, last_year + 1):
        li = line_index + (last_year - year) * 2 + 1
        assert html[li - 1] == f'<h4><span class="mw-headline" id="{year}">{year}</span></h4>'
        year_to_div[year] = html[li]
    return year_to_div


def get_date_from_html(html, year):
    comma = html.find(",")
    if comma != -1:
        y = html[comma + 1:]
        y = y.replace(" ", "")
        y = int(y)
        assert y == year or y == year + 1
        year = y
        html = html[:comma]
    month, day = html.split(" ")
    month_to_int = {
        "Jan": 1,
        "Feb": 2,
        "Mar": 3,
        "Apr": 4,
        "May": 5,
        "Jun": 6,
        "Jul": 7,
        "Aug": 8,
        "Sep": 9,
        "Oct": 10,
        "Nov": 11,
        "Dec": 12,
    }
    month = month_to_int[month]
    day = int(day)
    integer_date = int(f"{year:02}{month:02}{day:02}")
    return integer_date


def get_full_link(link):
    site_prefix = "https://liquipedia.net"
    link_root = "/starcraft2/"
    link_prefix = site_prefix + link_root

    if link.startswith(link_prefix):
        return link
    elif link.startswith(link_root):
        return site_prefix + link
    else:
        assert False


def get_date_to_tournament_from_div(div, year):
    img_exp = r"<img[^>]+>"
    div = re.sub(img_exp, "", div)

    escaped_exp = r"&[^;]+;"
    div = re.sub(escaped_exp, "", div)

    root = ET.fromstring(div)
    assert root[0][0].tag == "tbody"
    root = root[0][0]
    date_to_tournament = defaultdict(lambda: [])

    for row in root[1:]:
        start_date = "".join(row[0].itertext())
        end_date = "".join(row[1].itertext())
        start_date = get_date_from_html(start_date, year)
        end_date = get_date_from_html(end_date, year)

        tournament_name = "".join(row[2].itertext())
        tournament_link = row[2][0].attrib["href"]
        tournament_link = get_full_link(tournament_link)

        prize = "".join(row[4].itertext())
        assert prize[0] == "$"
        prize = prize[1:].replace(",", "")
        prize = int(float(prize))

        date_to_tournament[(end_date, start_date)].append(
            [start_date, end_date, tournament_name, prize, tournament_link]
        )
    return date_to_tournament


def parse_tournment_list_html(source_file, first_date, last_date, level):
    html, _ = read_lines(source_file)

    first_year, first_month, first_day = int(first_date[:4]), int(first_date[4:6]), int(first_date[6:8])
    last_year, last_month, last_day = int(last_date[:4]), int(last_date[4:6]), int(last_date[6:8])
    first_date = int(first_date)
    last_date = int(last_date)

    year_to_div = get_year_to_div_from_html(html, first_year, last_year)

    date_to_tournament = defaultdict(lambda: [])
    for year, div in year_to_div.items():
        yearly_date_to_tournament = get_date_to_tournament_from_div(div, year)
        for date, tournament_list in yearly_date_to_tournament.items():
            end_date = date[0]
            if first_date <= end_date <= last_date:
                for tournament in tournament_list:
                    date_to_tournament[date].append([level] + tournament)

    tournaments = sum(len(t_list) for t_list in date_to_tournament.values())
    logger.info(f"Read {tournaments:,} {level} tournaments")
    return date_to_tournament


def run_liquipedia_tournament_list_parser(arg):
    premier_date_to_tournament = parse_tournment_list_html(arg.premier_list_file, arg.first_date, arg.last_date, "premier")
    major_date_to_tournament = parse_tournment_list_html(arg.major_list_file, arg.first_date, arg.last_date, "major")
    date_to_tournament = premier_date_to_tournament
    for date, tournament_list in major_date_to_tournament.items():
        for tournament in tournament_list:
            date_to_tournament[date].append(tournament)
    data = [["level", "start", "end", "name", "prize", "link"]]
    for _, tournament_list in sorted(date_to_tournament.items()):
        for tournament in tournament_list:
            data.append(tournament)
    tournaments = len(data) - 1
    write_csv(arg.tournament_list_file, "pandas", data)
    logger.info(f"Saved {tournaments:,} tournaments to {arg.tournament_list_file}")
    return


def get_tournament_file_name(start, end, link):
    link_prefix = "https://liquipedia.net/starcraft2/"
    assert link.startswith(link_prefix)
    link = link[len(link_prefix):]
    link = link.replace("/", "__")
    file = f"{start}__{end}__{link}"
    return file


def run_liquipedia_tournament_page_crawler(arg):
    tournament_data = read_csv(arg.tournament_list_file, "pandas")
    tournaments = len(tournament_data) - 1

    for ti, (level, start, end, name, prize, link) in enumerate(tournament_data[1:]):
        logger.info(f"Crawling ({ti + 1}/{tournaments}): {link}")
        file = get_tournament_file_name(start, end, link)
        file = os.path.join(arg.tournament_html_dir, file + ".html")
        if os.path.exists(file):
            line_list, _ = read_lines(file)
            if "Rate Limited" not in line_list[0]:
                continue
        html = requests.get(link).text
        time.sleep(3)
        if "Rate Limited" in html:
            logger.info("Rate Limited")
            break
        with open(file, "w", encoding="utf8") as f:
            f.write(html)
        logger.info(f"Saved to {file}")
    return


def get_wikitable_group_match(html):
    header = '<table class="wikitable matchlist'
    footer = '</table>'
    group_lici_list = []
    for li, line in enumerate(html):
        ci = line.find(header)
        if ci != -1:
            group_lici_list.append((li, ci))
    groups = len(group_lici_list)
    logger.info(f"wikitable matchlist: {groups} groups")

    data = []
    for li, ci in group_lici_list:
        for lj in range(li, len(html)):
            cj = html[lj].find(footer)
            if cj != -1:
                break
        else:
            assert False
        table = html[li:lj + 1]
        table[0] = table[0][ci:]
        table[-1] = table[-1][:cj+len(footer)]
        table = "".join(table)

        img_exp = r"<img[^>]+>"
        table = re.sub(img_exp, "", table)
        escaped_exp = r"&[^;]+;"
        table = re.sub(escaped_exp, "", table)

        root = ET.fromstring(table)[0]
        assert root.tag == "tbody"
        title = "".join(root[0].itertext()).strip()
        title = f"Group ({title})"

        for tr in root[1:]:
            assert tr.tag == "tr"
            if tr.attrib.get("class", "") != "match-row":
                continue
            try:
                p1_name = "".join(tr[0].itertext()).strip()
                p1_race = tr[0][1].attrib.get("title", "X")
                p1_score = int("".join(tr[1].itertext()).strip())
                p2_score = int("".join(tr[2].itertext()).strip())
                p2_race = tr[3][-2].attrib.get("title", "X")
                p2_name = "".join(tr[3].itertext()).strip()
            except IndexError:
                # missing cell
                continue
            except ValueError:
                # missing numerical score
                continue
            assert p1_race.startswith("Terran") or p1_race.startswith("Protoss") or p1_race.startswith("Zerg") \
                   or p1_race.startswith("Random") or p1_race == "X"
            p1_race = p1_race[0]
            assert p2_race.startswith("Terran") or p2_race.startswith("Protoss") or p2_race.startswith("Zerg") \
                   or p2_race.startswith("Random") or p2_race == "X"
            p2_race = p2_race[0]
            data.append([title, p1_name, p1_race, p1_score, p2_score, p2_race, p2_name])
    matches = len(data)
    logger.info(f"wikitable matchlist: {matches} matches")
    return data


def get_name_from_brkts_html(line, cell_start):
    tag = 'aria-label="'
    j = cell_start + line[cell_start:].find(tag)
    assert j > cell_start
    j += len(tag)
    k = j + line[j:].find('"')
    name = line[j:k]
    return name


def get_race_from_brkts_html(line, cell_start):
    tag = '<span class="race">'
    j = cell_start + line[cell_start:].find(tag)
    assert j > cell_start
    k = j + line[j:].find("</span>")
    assert k > j
    cell = line[j:k]
    for race in ["Terran", "Protoss", "Zerg", "Random"]:
        if race in cell:
            return race[0]
    return "X"


def get_score_from_brkts_html(line, cell_start):
    tag = 'brkts-matchlist-cell-content">'
    j = cell_start + line[cell_start:].find(tag)
    assert j > cell_start
    j += len(tag)
    k = j + line[j:].find("<")
    try:
        score = int(line[j:k])
    except ValueError:
        return "X"
    return score


def get_brkts_group_match(html):
    header = '<div class="brkts-matchlist '
    group_line_list = []
    for line in html:
        i = line.find(header)
        if i != -1:
            group_line_list.append(line[i:])
    groups = len(group_line_list)
    logger.info(f"brkts matchlist: {groups} groups")

    data = []
    for line in group_line_list:
        escaped_exp = r"&[^;]+;"
        line = re.sub(escaped_exp, "", line)

        i = line.find('<div class="brkts-matchlist-title"')
        assert i >= 0
        li = i + line[i:].find(">") + 1
        ri = li + line[li:].find("<")
        title = line[li:ri]
        title = f"Group ({title})"

        cell_exp = r'<div class="brkts-matchlist-cell[" ]'
        ci_list = [m.start() for m in re.finditer(cell_exp, line)]
        assert len(ci_list) > 0
        assert len(ci_list) % 4 == 0
        for i in range(0, len(ci_list), 4):
            p1_name = get_name_from_brkts_html(line, ci_list[i])
            p1_race = get_race_from_brkts_html(line, ci_list[i])
            p1_score = get_score_from_brkts_html(line, ci_list[i + 1])
            p2_score = get_score_from_brkts_html(line, ci_list[i + 2])
            p2_race = get_race_from_brkts_html(line, ci_list[i + 3])
            p2_name = get_name_from_brkts_html(line, ci_list[i + 3])
            if p1_score == "X" or p2_score == "X":
                continue
            data.append([title, p1_name, p1_race, p1_score, p2_score, p2_race, p2_name])
    matches = len(data)
    logger.info(f"brkts matchlist: {matches} matches")
    return data


def get_name_race_score_from_bracket_player_html(html):
    tag = 'aria-label="'
    i = html.find(tag)
    assert i > 0
    i += len(tag)
    j = i + html[i:].find('"')
    name = html[i:j]

    exp = r'<div class="brkts-opponent-entry-left ([^" ]+)[" ]'
    match_list = re.findall(exp, html)
    assert len(match_list) == 1
    race = match_list[0]
    if race in ["Terran", "Protoss", "Zerg", "Random"]:
        race = race[0]
    else:
        race = "X"

    tag = '<div class="brkts-opponent-score-inner">'
    i = html.find(tag)
    assert i > 0
    i += len(tag)
    j = i + html[i:].find("</div>")
    score = html[i:j]
    if score.startswith("<b>"):
        score = score[3:-4]
    try:
        score = int(score)
    except ValueError:
        score = "X"

    return name, race, score


def get_bracket_match(html):
    header = '<div class="brkts-bracket-wrapper'
    group_line_list = []
    for line in html:
        i = line.find(header)
        if i != -1:
            group_line_list.append(line[i:])
    groups = len(group_line_list)
    logger.info(f"bracket matchlist: {groups} groups")

    data = []
    for line in group_line_list:
        img_exp = r"<img[^>]+>"
        line = re.sub(img_exp, "", line)
        escaped_exp = r"&[^;]+;"
        line = re.sub(escaped_exp, "", line)
        title = "Bracket"

        cell_exp = r'<div class="brkts-match[" ]'
        ci_list = [m.start() for m in re.finditer(cell_exp, line)]
        assert len(ci_list) > 0

        for i, ci in enumerate(ci_list):
            try:
                cj = ci_list[i + 1]
                bracket = line[ci:cj]
            except IndexError:
                bracket = line[ci:]
            player_exp = r'<div class="brkts-opponent-entry[" ]'
            pi_list = [m.start() for m in re.finditer(player_exp, bracket)]
            assert len(pi_list) == 2 or len(pi_list) == 3
            p1 = bracket[pi_list[0]:pi_list[1]]
            p2 = bracket[pi_list[1]:pi_list[2]] if len(pi_list) > 2 else bracket[pi_list[1]:]
            p1_name, p1_race, p1_score = get_name_race_score_from_bracket_player_html(p1)
            p2_name, p2_race, p2_score = get_name_race_score_from_bracket_player_html(p2)
            if p1_score == "X" or p2_score == "X":
                continue
            data.append([title, p1_name, p1_race, p1_score, p2_score, p2_race, p2_name])
    matches = len(data)
    logger.info(f"bracket matchlist: {matches} matches")
    return data


def parse_tournament_html(html):
    match_list = []
    match_list += get_wikitable_group_match(html)
    match_list += get_brkts_group_match(html)
    match_list += get_bracket_match(html)
    return match_list


def run_liquipedia_tournament_page_parser(arg):
    tournament_data = read_csv(arg.tournament_list_file, "pandas")
    tournaments = len(tournament_data) - 1

    match_list = [[
        "level", "start", "end", "tournament",
        "match", "p1_name", "p1_race", "p1_score", "p2_score", "p2_race", "p2_name",
        "link", "prize",
    ]]
    for ti, (level, start, end, name, prize, link) in enumerate(tournament_data[1:]):
        file = get_tournament_file_name(start, end, link)
        file = os.path.join(arg.tournament_html_dir, file + ".html")
        logger.info(f"Parsing ({ti + 1}/{tournaments}): {name}")
        html, _ = read_lines(file)
        assert "Rate Limited" not in "".join(html)
        tournament_match_list = parse_tournament_html(html)
        for title, p1_name, p1_race, p1_score, p2_score, p2_race, p2_name in tournament_match_list:
            match_list.append([
                level, start, end, name,
                title, p1_name, p1_race, p1_score, p2_score, p2_race, p2_name,
                prize, link,
            ])
    matches = len(match_list) - 1
    write_csv(arg.match_list_file, "pandas", match_list)
    logger.info(f"Saved {matches:,} matches to {arg.match_list_file}")
    return


def get_pid_from_name(name):
    pid = name.strip().lower()
    i = pid.find("(")
    if i != -1:
        pid = pid[:i].strip()

    problematic_name_list = [
        "Bunny (Danish player)",
        "Classic (Kim Hong Jae)",
        "DarK",
        "Dragon (Chinese player)",
        "FuturE",
        "Happy (Russian player)",
        "HerO",
        "Lucky (American Protoss)",
        "San (Russian player)",
    ]

    if name in problematic_name_list:
        pid = name
    return pid


def run_player_name_extraction(arg):
    match_list = read_csv(arg.match_list_file, "pandas")[1:]
    pid_name_count = defaultdict(lambda: defaultdict(lambda: 0))
    pid_race_count = defaultdict(lambda: defaultdict(lambda: 0))
    scores = 0

    for _, _, _, _, _, p1_name, p1_race, p1_score, p2_score, p2_race, p2_name, _, _ in match_list:
        scores += int(p1_score)
        scores += int(p2_score)
        for name, race in [(p1_name, p1_race), (p2_name, p2_race)]:
            pid = get_pid_from_name(name)
            pid_name_count[pid][name] += 1
            pid_race_count[pid][race] += 1

    pid_list = sorted(pid_name_count, key=lambda pid: (pid.lower(), pid))
    player_list = []
    for pid in pid_list:
        name_list = sorted(pid_name_count[pid], key=lambda name: pid_name_count[pid][name], reverse=True)
        race_list = sorted(pid_race_count[pid], key=lambda race: pid_race_count[pid][race], reverse=True)
        matches = sum(pid_name_count[pid].values())
        data = [str(matches), "".join(race_list)] + name_list
        player_list.append(data)

    players = len(player_list)
    names = sum(len(p) - 2 for p in player_list)
    races = sum(len(p[1]) for p in player_list)
    logger.info(f"{players:,} players")
    logger.info(f"{names:,} player-names")
    logger.info(f"{races:,} player-races")
    logger.info(f"{scores:,} player-scores")
    write_csv(arg.player_name_file, "pandas", player_list)
    return


class Player:
    def __init__(self, race_list, name_list):
        self.race_list = race_list
        self.name_list = name_list
        self.pid = get_pid_from_name(self.name_list[0])

        self.elo = 1500
        self.elo_cache = 0
        self.highest_elo = self.elo

        self.tournaments = 0
        self.in_tournament = False
        self.matches = 0

        self.recent_elo_list = deque([(self.elo, date(2010, 7, 27))])
        return

    def update_elo_cache(self, cache_date):
        self.elo += self.elo_cache
        self.elo_cache = 0
        if self.highest_elo < self.elo:
            self.highest_elo = self.elo

        if self.elo != self.recent_elo_list[-1][0]:
            self.recent_elo_list.append((self.elo, cache_date))

        latest_old = None
        while self.recent_elo_list:
            _, old_date = self.recent_elo_list[0]
            if (cache_date - old_date).days < 180:
                break
            latest_old = self.recent_elo_list.popleft()
        if latest_old is not None:
            self.recent_elo_list.appendleft(latest_old)
        return

    def get_recent_elo_change(self):
        return self.elo - self.recent_elo_list[0][0]

    def get_full_name(self):
        return f"{self.name_list[0]}({self.race_list[0]})"


def initialize_all_player(player_list):
    pid_to_player = {}
    for rame_list in player_list:
        race_list = [r for r in rame_list[1]]
        name_list = rame_list[2:]
        player = Player(race_list, name_list)
        pid_to_player[player.pid] = player
    return pid_to_player


def get_python_date(str_date):
    y = int(str_date[0:4])
    m = int(str_date[4:6])
    d = int(str_date[6:8])
    python_date = date(y, m, d)
    return python_date


def get_elo_update(p1, p2, score1, score2):
    q1 = 10 ** (p1.elo / 400)
    q2 = 10 ** (p2.elo / 400)

    rounds = score1 + score2
    expected1 = rounds * q1 / (q1 + q2)
    # expected2 = rounds * q2 / (q1 + q2)

    k1 = 40 if p1.matches < 50 else 20
    k2 = 40 if p2.matches < 50 else 20
    k = min(k1, k2)

    update1 = k * (score1 - expected1)
    # update2 = k * (score2 - expected2)

    update1 = round(update1)
    update2 = -update1
    return update1, update2


def run_player_elo_calculation(arg):
    player_list = read_csv(arg.player_name_file, "pandas")
    pid_to_player = initialize_all_player(player_list)

    match_list = read_csv(arg.match_list_file, "pandas")[1:]
    latest_date = None
    date_range = (get_python_date(arg.first_date), get_python_date(arg.last_date))

    for _, start, end, _, _, p1_name, p1_race, p1_score, p2_score, p2_race, p2_name, _, _ in match_list:
        match_date = (get_python_date(start), get_python_date(end))
        if match_date[1] < date_range[0]:
            continue
        if match_date[1] > date_range[1]:
            break

        # update elo after a tournament
        if latest_date is not None and latest_date != match_date:
            for pid, player in pid_to_player.items():
                player.update_elo_cache(latest_date[1])
                if player.in_tournament:
                    player.tournaments += 1
                    player.in_tournament = False
        latest_date = match_date

        # use normalized name as unique pid
        p1 = get_pid_from_name(p1_name)
        p2 = get_pid_from_name(p2_name)
        p1 = pid_to_player[p1]
        p2 = pid_to_player[p2]
        assert p1_race in p1.race_list
        assert p2_race in p2.race_list
        p1.in_tournament = True
        p2.in_tournament = True
        p1.matches += 1
        p2.matches += 1

        # add the elo updates of the match to cache
        p1_score = int(p1_score)
        p2_score = int(p2_score)
        update1, update2 = get_elo_update(p1, p2, p1_score, p2_score)
        p1.elo_cache += update1
        p2.elo_cache += update2

    # update elo for the last tournament
    for pid, player in pid_to_player.items():
        player.update_elo_cache(latest_date[1])
        if player.in_tournament:
            player.tournaments += 1
            player.in_tournament = False

    data = [["id", "elo", "recent", "tournaments", "matches", "career_high"]]
    for pid, p in sorted(pid_to_player.items(), key=lambda pp: pp[1].elo, reverse=True):
        if p.matches < 20:
            continue
        if p.elo < 1600:
            break
        full_name = p.get_full_name()
        recent_elo_change = p.get_recent_elo_change()
        recent_elo_change = f"{recent_elo_change:+d}" if recent_elo_change != 0 else "0"
        data.append([full_name, p.elo, recent_elo_change, p.tournaments, p.matches, p.highest_elo])
    write_csv(arg.player_elo_file, "pandas", data)

    data = [["id", "elo", "recent", "tournaments", "matches", "career_high"]]
    for pid, p in sorted(pid_to_player.items(), key=lambda pp: pp[1].highest_elo, reverse=True):
        if p.matches < 20:
            continue
        if p.highest_elo < 1600:
            break
        full_name = p.get_full_name()
        recent_elo_change = p.get_recent_elo_change()
        recent_elo_change = f"{recent_elo_change:+d}" if recent_elo_change != 0 else "0"
        data.append([full_name, p.elo, recent_elo_change, p.tournaments, p.matches, p.highest_elo])
    write_csv("..\\highest_elo.csv", "pandas", data)
    return


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--premier_list_file", type=str, default="..\\premier_2021_1213.html")
    parser.add_argument("--major_list_file", type=str, default="..\\major_2021_1213.html")
    parser.add_argument("--tournament_list_file", type=str, default="..\\tournament_list.csv")
    parser.add_argument("--tournament_html_dir", type=str, default="..\\tournament_html")
    parser.add_argument("--match_list_file", type=str, default="..\\match_list.csv")
    parser.add_argument("--player_name_file", type=str, default="..\\player_name.csv")
    parser.add_argument("--player_elo_file", type=str, default="..\\player_elo.csv")
    parser.add_argument("--player_highest_elo_file", type=str, default="..\\player_highest_elo.csv")

    parser.add_argument("--first_date", type=str, default="20160101")
    parser.add_argument("--last_date", type=str, default="20211212")
    parser.add_argument("--elo_level", type=str, default="major")

    parser.add_argument("--indent", type=int, default=2)

    arg = parser.parse_args()
    # run_liquipedia_tournament_list_parser(arg)
    # run_liquipedia_tournament_page_crawler(arg)
    # run_liquipedia_tournament_page_parser(arg)
    # run_player_name_extraction(arg)
    # run_player_elo_calculation(arg)
    return


if __name__ == "__main__":
    main()
    sys.exit()