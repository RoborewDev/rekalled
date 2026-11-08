"""Worked examples. Expected values were recorded once from py-fsrs 6.3 with fuzzing off."""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.study.scheduler import Scheduler

AGAIN, HARD, GOOD, EASY = 1, 2, 3, 4
NOW = datetime(2026, 11, 2, 9, 0, tzinfo=UTC)


@pytest.fixture
def scheduler() -> Scheduler:
    return Scheduler(fuzzing=False)


def test_a_new_card_is_due_now_and_has_no_memory_score(scheduler: Scheduler):
    card = scheduler.new_card(NOW)

    assert card.due_at == NOW
    assert scheduler.retrievability(card, NOW) is None


def test_good_on_a_new_card_moves_to_the_second_learning_step(scheduler: Scheduler):
    card = scheduler.review(scheduler.new_card(NOW), GOOD, NOW)

    assert (card.state, card.step) == (1, 1)  # still Learning
    assert card.due_at == NOW + timedelta(minutes=10)


def test_good_twice_graduates_a_new_card_to_review(scheduler: Scheduler):
    first = scheduler.review(scheduler.new_card(NOW), GOOD, NOW)

    second = scheduler.review(first, GOOD, first.due_at)

    assert second.state == 2  # Review
    assert second.due_at == first.due_at + timedelta(days=2)


def test_again_on_a_review_card_sends_it_to_relearning(scheduler: Scheduler):
    card = scheduler.review(scheduler.new_card(NOW), EASY, NOW)  # straight to Review

    lapsed = scheduler.review(card, AGAIN, card.due_at)

    assert lapsed.state == 3


def test_preview_shows_when_each_rating_would_be_due(scheduler: Scheduler):
    preview = scheduler.preview(scheduler.new_card(NOW), NOW)

    assert preview == {
        AGAIN: NOW + timedelta(minutes=1),
        HARD: NOW + timedelta(minutes=5, seconds=30),
        GOOD: NOW + timedelta(minutes=10),
        EASY: NOW + timedelta(days=8),
    }


def test_memory_score_is_full_right_after_a_review_and_fades(scheduler: Scheduler):
    first = scheduler.review(scheduler.new_card(NOW), GOOD, NOW)
    card = scheduler.review(first, GOOD, first.due_at)
    last_review_at = card.last_review_at

    assert last_review_at is not None
    assert scheduler.retrievability(card, last_review_at) == pytest.approx(1.0)
    later = last_review_at + timedelta(days=10)
    assert scheduler.retrievability(card, later) == pytest.approx(0.774, abs=0.001)


def test_non_utc_times_are_accepted(scheduler: Scheduler):
    london = NOW.astimezone(ZoneInfo("Europe/London"))

    card = scheduler.review(scheduler.new_card(london), GOOD, london)

    assert card.due_at == NOW + timedelta(minutes=10)
