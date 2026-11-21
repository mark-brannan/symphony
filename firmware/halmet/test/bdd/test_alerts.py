import re

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/alerts.feature")

COUNTER = re.compile(r" \d+/\d+$")
NUMBER = re.compile(r"^ *\d+$")


def bare(text):
    return COUNTER.sub("", text)


def runs(values):
    """Collapse a sequence into [value, length] runs."""
    out = []
    for v in values:
        if out and out[-1][0] == v:
            out[-1][1] += 1
        else:
            out.append([v, 1])
    return out


def segments(world):
    return [s["segment"] for s in world.watched()]


def hours_shown(world):
    return [s["hours_segment"] for s in world.watched()]


def rows(world, row):
    return [s[f"row{row}"] for s in world.watched()]


def assert_cycle(seq, cycle, each_s):
    """seq walks `cycle` in order, `each_s` seconds per item (the ends may be cut short)."""
    r = runs(seq)
    assert {v for v, _ in r} == set(cycle), r
    for (a, _), (b, _) in zip(r, r[1:]):
        assert cycle.index(b) == (cycle.index(a) + 1) % len(cycle), r
    for v, n in r[1:-1]:
        assert n == each_s, r


def one_in_four(seq, word):
    for i in range(len(seq) - 3):
        assert seq[i:i + 4].count(word) == 1, seq


# ------------------------------------------------------------------ Given


@given("the board has been up for 15 minutes, unless a scenario says otherwise")
def up_15_min(world):
    world.up_s = 15 * 60


@given(parsers.parse("the board has been up for {n:d} seconds"))
def up_for(world, n):
    world.up_s = n


@given("no flame is seen")
def no_flame(world):
    world.set_seen(False)


@given(parsers.parse("the engine is turning at {rpm:d} RPM"))
def engine_turning(world, rpm):
    world.rpm = float(rpm)


@given("the engine is stopped")
def engine_stopped(world):
    world.rpm = 0.0


@given(parsers.parse("engine hours are {h:g}"))
def engine_hours(world, h):
    world.hours = h


@given(parsers.parse("the flash cache holds {h:g} engine hours"))
def cached_hours(world, h):
    # main.cpp shows the flash cache while no Signal K value has arrived.
    world.hours = h


@given("Signal K is connected")
def sk_connected(world):
    world.sk = True


@given("Signal K is not connected")
@given("Signal K has not connected since boot")
def sk_not_connected(world):
    world.sk = False


@given("the coolant alarm is on")
def coolant_on(world):
    world.coolant = True


@given("the oil pressure alarm is on")
def oil_on(world):
    world.oil = True


@given("the largest free heap block is under 30000 bytes")
def low_memory(world):
    world.block = 29_000


@given(parsers.re(r"the alternator has read (?P<v>[\d.]+) V for (?P<n>\d+) (?P<unit>seconds|minutes)"))
def alternator_read(world, v, n, unit):
    world.alt_v, world.alt_live = float(v), True
    world.run(int(n) * (60 if unit == "minutes" else 1))
    world.clear()


@given("no alternator voltage has arrived for 10 seconds")
def alternator_silent(world):
    world.alt_v, world.alt_live = 12.6, True
    world.run(1)
    world.alt_live = False
    world.run(10)
    world.clear()


@given(parsers.parse("the board reset {n:d} minutes ago after a {reason}"))
def reset_ago(world, n, reason):
    world.up_s, world.reset = n * 60, reason


@given('"Alt not charging" is showing')
def alt_showing(world):
    if world.rpm <= 0:
        world.rpm = 850.0
    world.alt_v, world.alt_live = 12.6, True
    world.run_until(lambda: "Alt not charging" in world.row6 or "Alt not charging" in world.row7, 60)
    world.clear()


@given(parsers.parse('OLED row 6 is cycling "{a}" and "{b}"'))
def row6_cycling(world, a, b):
    world.oil, world.sk = True, False
    world.run(6)
    assert {a, b} <= set(rows(world, 6))
    world.clear()


@given(parsers.parse('the flame alarm is counting down "{text}"'))
def flame_counting_down(world, text):
    world.set_seen(True)
    world.run(1)
    world.set_seen(False)
    world.run_until(lambda: world.row6 == text, 120)
    world.clear()


# ------------------------------------------------------------------- When


@when(parsers.parse("I watch the displays for {n:d} seconds"))
@when(parsers.parse("I watch OLED row 6 for {n:d} seconds"))
def watch(world, n):
    world.clear()
    world.run(n)


@when(parsers.parse("the engine goes from stopped to {rpm:d} RPM"))
def engine_starts(world, rpm):
    world.rpm = 0.0
    world.run(4)
    world.rpm = float(rpm)
    world.run(4)


@when(parsers.parse("the alternator reads {v:g} V"))
def alternator_reads(world, v):
    world.alt_v, world.alt_live = v, True
    world.clear()


@when("Signal K connects")
def sk_connects(world):
    world.sk = True
    world.clear()


@when("a flame is seen")
def flame_seen(world):
    world.clear()
    world.set_seen(True)
    world.run(8)


@when("the countdown ends")
def countdown_ends(world):
    world.run_until(lambda: not world.flame_alarm, 5)
    world.clear()
    world.run(8)


# ------------------------------------------------------------------- Then


@then(parsers.parse('the segment display shows "{text}" every second'))
def segment_every_second(world, text):
    assert set(segments(world)) == {text}


@then(parsers.re(r'the hours display shows "(?P<text>[^"]*)" every second(?:, _ being a blank)?$'))
def hours_every_second(world, text):
    assert set(hours_shown(world)) == {text.replace("_", " ")}


@then(parsers.re(r'the hours display shows "(?P<text>[^"]*)"$'))
def hours_shows(world, text):
    assert text in hours_shown(world)


@then("the hours display is unchanged")
def hours_unchanged(world):
    shown = set(hours_shown(world))
    assert len(shown) == 1 and shown != {"    "}, shown


@then(parsers.re(r'the hours display never shows "(?P<a>[^"]*)"(?: or "(?P<b>[^"]*)")?$'))
def hours_never(world, a, b):
    shown = set(hours_shown(world))
    assert a not in shown and b not in shown, shown


@then(parsers.parse('the hours display flashes "{text}" with it'))
def hours_flashes(world, text):
    seq = [s["hours_segment"] for s in world.steps]
    assert [v for v, _ in runs(seq)][:4] == [text, "    ", text, "    "], runs(seq)[:4]


@then(parsers.parse('the hours display returns to "{text}"'))
def hours_return(world, text):
    assert set(hours_shown(world)) == {text}


@then(parsers.parse('the segment display shows "{text}" for 1 second in every 4'))
def segment_one_in_four(world, text, scratch):
    one_in_four(segments(world), text)
    scratch["word"] = text


@then(parsers.parse('"{text}" the other 3 seconds'))
def segment_otherwise(world, text, scratch):
    assert set(segments(world)) == {scratch["word"], text}


@then("never more often")
def never_more_often(world, scratch):
    one_in_four(segments(world), scratch["word"])


@then(parsers.re(r'the segment display shows "(?P<text>[^"]*)"$'))
def segment_shows(world, text):
    assert text in segments(world)


@then(parsers.re(r'the segment display never shows "(?P<a>[^"]*)"(?: or "(?P<b>[^"]*)")?$'))
def segment_never(world, a, b):
    shown = set(segments(world))
    assert a not in shown and b not in shown, shown


@then(parsers.parse("OLED row {row:d} is blank"))
def row_blank(world, row):
    assert set(rows(world, row)) == {""}


@then(parsers.re(r'OLED row 6 shows "(?P<text>[^"]*)"$'))
def row6_shows(world, text, scratch):
    assert set(map(bare, rows(world, 6))) == {text}
    scratch["row6"] = text


@then("it carries no counter")
def no_counter(world, scratch):
    assert set(rows(world, 6)) == {scratch["row6"]}


@then(parsers.parse('OLED row 6 does not show "{text}"'))
def row6_not(world, text):
    assert text not in map(bare, rows(world, 6))


@then(parsers.parse('the segment display changes from "{a}" to "{b}"'))
def segment_changes(world, a, b):
    seq = [s for s in segments(world) if NUMBER.match(s)]
    assert [v for v, _ in runs(seq)] == [a, b], seq


@then(parsers.parse('it never shows "{text}" while RPM is above 0'))
def never_while_running(world, text):
    assert all(s["segment"] != text for s in world.watched() if s["rpm"] > 0)


@then(parsers.re(r"each 4 second cycle shows (?P<words>.*)"))
def segment_cycle(world, words):
    cycle = re.findall(r'"([^"]*)"', words)
    seq = segments(world)
    assert any(all(seq[i] == cycle[(i + off) % 4] for i in range(len(seq))) for off in range(4)), seq


@then("it shows, 2 seconds each:")
def row6_cycle(world, datatable):
    assert_cycle(rows(world, 6), [r[0].strip() for r in datatable], 2)


@then(parsers.parse('the segment display alternates "{a}" and "{b}" in its alert second'))
def segment_alternates(world, a, b):
    seq = segments(world)
    words = [s for s in seq if not NUMBER.match(s)]
    assert words and all(w in (a, b) for w in words), seq
    assert all(x != y for x, y in zip(words, words[1:])), seq
    assert all(NUMBER.match(y) for x, y in zip(seq, seq[1:]) if not NUMBER.match(x)), seq


@then(parsers.parse('OLED row 6 shows "{text}" with no counter within {n:d} seconds'))
def row6_within(world, text, n):
    world.run(n)
    assert world.row6 == text


@then(parsers.parse('"{text}" is gone within {n:d} second'))
def gone_within(world, text, n):
    world.run(n)
    assert text not in bare(world.row6)


@then("the 30 second wait starts again from zero the next time it drops")
def alt_wait_restarts(world):
    world.alt_v = 12.6
    world.clear()
    world.run(29)
    assert "Alt not charging" not in map(bare, rows(world, 6))
    world.run_until(lambda: bare(world.row6) == "Alt not charging", 2)


@then(parsers.parse('the segment display flashes "{text}"'))
def segment_flashes(world, text):
    seq = [s["segment"] for s in world.steps]
    assert [v for v, _ in runs(seq)][:4] == [text, "    ", text, "    "], runs(seq)[:4]


@then(parsers.parse('OLED row 6 flashes "{text}"'))
def row6_flashes(world, text):
    seq = [s["row6"] for s in world.steps]
    assert [v for v, _ in runs(seq)][:4] == [text, "", text, ""], runs(seq)[:4]


def first_burst(world):
    """The first burst's steps, and the steady hold after it (step k is at (k + 1) ticks)."""
    on_ms, off_ms, pulses, hold_ms, _ = world.timing
    burst = (on_ms + off_ms) * pulses // world.STEP_MS - 1
    return world.steps[:burst], world.steps[burst:burst + hold_ms // world.STEP_MS]


@then("the piezo sounds with each flash")
def piezo_with_flash(world):
    burst, _ = first_burst(world)
    assert [s["piezo"] for s in burst] == [s["segment"] != "    " for s in burst], burst
    assert sum(1 for v, _ in runs([s["piezo"] for s in burst]) if v) == world.timing[2]


@then("the piezo is silent during the steady hold")
def piezo_silent_hold(world):
    _, hold = first_burst(world)
    assert hold and all(s["segment"] != "    " for s in hold), hold
    assert not any(s["piezo"] for s in hold), hold


@then("the piezo is silent")
def piezo_silent(world):
    assert world.steps and not any(s["piezo"] for s in world.steps)


@then(parsers.parse('OLED row 7 cycles "{a}" and "{b}"'))
def row7_cycles(world, a, b):
    assert_cycle(rows(world, 7), [a, b], 2)


@then(parsers.parse('the segment display never shows "{text}" while the alarm is latched'))
def never_while_latched(world, text):
    latched = [s for s in world.steps if s["alarm"]]
    assert latched and all(s["segment"] != text for s in latched)


@then("OLED row 6 cycles the alerts again")
def row6_alerts_again(world):
    assert set(rows(world, 6)) == {"COOLANT HOT"}


@then(parsers.parse('the segment display returns to its number and "{word}"'))
def segment_returns(world, word):
    seq = segments(world)
    one_in_four(seq, word)
    assert all(NUMBER.match(s) for s in seq if s != word), seq


@pytest.fixture
def scratch():
    """What an earlier Then named, for an "And" that refers back to it."""
    return {}
