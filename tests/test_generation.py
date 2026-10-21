"""Chronology, suitability, data corruption detection and deterministic generation."""

import numpy as np
import pandas as pd
import pytest

from data_utils import load_data, validate_data
from generate_data import generate_customers, generate_interactions, generate_services_df


def test_shipped_data():
    customers, interactions, services = load_data()
    assert len(customers) == 500 and len(interactions) == 3000 and len(services) == 10
    assert set(customers.region) == {"tucson", "ohio"}
    assert not {"name", "email"} & set(customers.columns)


def test_deterministic_local_rng(dataset):
    before = np.random.get_state()
    a = generate_customers(60, region="both")
    i = generate_interactions(a, 360)
    pd.testing.assert_frame_equal(a, dataset[0])
    pd.testing.assert_frame_equal(i, dataset[1])
    after = np.random.get_state()
    assert np.array_equal(before[1], after[1])
    validate_data(a, i, generate_services_df())
    assert i.date.is_monotonic_increasing


@pytest.mark.parametrize(
    "column,value",
    [
        ("days_since_last_service", -1),
        ("season", "fake"),
        ("repeat_booking", True),
        ("date", "1900-01-01"),
    ],
)
def test_invalid_data_rejected(dataset, column, value):
    customers, interactions, services = dataset
    broken = interactions.copy()
    broken.loc[0, column] = value
    with pytest.raises(ValueError):
        validate_data(customers, broken, services)


def test_bad_counts():
    with pytest.raises(ValueError):
        generate_customers(0)
    with pytest.raises(ValueError):
        generate_interactions(generate_customers(5), 1)
