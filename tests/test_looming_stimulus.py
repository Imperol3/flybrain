"""Looming stimulus generation, encoding onto sensory populations, and DNp01 readout."""

import numpy as np

from brain.sensory import encoders, looming
from simulation import session


def test_looming_produces_positive_expansion_drive():
    params = looming.looming(simulation_duration_ms=100.0)
    drive = looming.generate_drive_signal(dt_ms=0.5, params=params)
    assert drive.shape[0] == 200
    assert np.any(drive > 0)
    assert np.all(drive >= 0)  # rectified


def test_receding_produces_no_positive_expansion_drive():
    params = looming.receding(simulation_duration_ms=100.0)
    drive = looming.generate_drive_signal(dt_ms=0.5, params=params)
    assert np.allclose(drive, 0.0)


def test_static_produces_no_drive():
    params = looming.static(simulation_duration_ms=100.0)
    drive = looming.generate_drive_signal(dt_ms=0.5, params=params)
    assert np.allclose(drive, 0.0)


def test_looming_parameters_are_exposed_not_hardcoded():
    default_params = looming.looming()
    custom_params = looming.looming(
        object_radius_cm=5.0,
        approach_velocity_cm_s=200.0,
        azimuth_deg=45.0,
        stimulus_duration_ms=50.0,
        simulation_duration_ms=80.0,
        seed=7,
    )
    assert custom_params.object_radius_cm != default_params.object_radius_cm
    assert custom_params.approach_velocity_cm_s != default_params.approach_velocity_cm_s
    assert custom_params.seed == 7


def test_encoder_only_drives_named_populations():
    drive = np.array([0.0, 1.0, 2.0, 0.0])
    population_indices = {"LC4": np.array([1, 2])}
    fn = encoders.make_external_input_fn(drive, population_indices, n_neurons=5, gain_mV_per_unit=3.0)

    step1 = fn(1, 0.1)
    assert step1[1] == 3.0
    assert step1[2] == 3.0
    assert step1[0] == 0.0 and step1[3] == 0.0 and step1[4] == 0.0

    step0 = fn(0, 0.1)
    assert np.all(step0 == 0.0)  # drive[0] == 0.0


def test_lc4_and_lplc2_stimulation_and_dnp01_readout(built_fixture_connectome):
    registry, connectome, _manifest = built_fixture_connectome
    stimulus_params = looming.looming(simulation_duration_ms=300.0, seed=1)
    result = session.run_looming_session(registry, connectome, stimulus_params, condition_name="looming")

    assert result.lc4_spike_count > 0
    assert result.lplc2_spike_count > 0
    assert result.dnp01_spike_count > 0
    assert result.escape_triggered is True


def test_descending_interpretation_is_a_configurable_threshold(built_fixture_connectome):
    """The escape-event interpretation threshold is a documented, changeable
    interface decision (not baked into the neuron model) — re-interpreting
    the same raw simulation output with a different threshold must change
    only the interpretation, not the underlying spike data.
    """
    registry, connectome, _manifest = built_fixture_connectome
    stimulus_params = looming.looming(simulation_duration_ms=300.0, seed=1)

    strict_result = session.run_looming_session(
        registry, connectome, stimulus_params, condition_name="looming",
        escape_threshold_rate_hz=1_000_000.0,
    )
    lenient_result = session.run_looming_session(
        registry, connectome, stimulus_params, condition_name="looming",
        escape_threshold_rate_hz=0.0,
    )

    assert strict_result.dnp01_spike_count == lenient_result.dnp01_spike_count  # same raw output
    assert strict_result.escape_triggered is False
    assert lenient_result.escape_triggered is True
