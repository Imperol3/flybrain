"""LC4/LPLC2 lesion (output-silencing) behaviour: the crucial causal test (brief section 11)."""

from brain.sensory import looming
from simulation import session


def test_looming_drives_dnp01_response(built_fixture_connectome):
    registry, connectome, _manifest = built_fixture_connectome
    stimulus_params = looming.looming(simulation_duration_ms=300.0, seed=99)
    result = session.run_looming_session(registry, connectome, stimulus_params, condition_name="looming")
    assert result.dnp01_spike_count > 0
    assert result.escape_triggered is True


def test_silencing_lc4_and_lplc2_collapses_dnp01_response(built_fixture_connectome):
    """The core causal claim: sensory stimulation still happens (LC4/LPLC2
    still receive and respond to the looming drive), but with their outbound
    synaptic effect silenced, DNp01 must not respond.
    """
    registry, connectome, _manifest = built_fixture_connectome
    stimulus_params = looming.looming(simulation_duration_ms=300.0, seed=99)

    silenced_result = session.run_looming_session(
        registry,
        connectome,
        stimulus_params,
        condition_name="looming_LC4_LPLC2_silenced",
        silenced_populations=("LC4", "LPLC2"),
    )

    # Sensory neurons still receive/respond to the stimulus themselves.
    assert silenced_result.lc4_spike_count > 0
    assert silenced_result.lplc2_spike_count > 0

    # But their outbound effect on the rest of the network is removed.
    assert silenced_result.dnp01_spike_count == 0
    assert silenced_result.escape_triggered is False


def test_silencing_only_one_population_does_not_necessarily_collapse_response(built_fixture_connectome):
    """Silencing a single population is a required additional data point
    (brief section 11) but only the BOTH-silenced condition is asserted to
    fully collapse the response; report, don't force, partial results.
    """
    registry, connectome, _manifest = built_fixture_connectome
    stimulus_params = looming.looming(simulation_duration_ms=300.0, seed=99)

    full_result = session.run_looming_session(
        registry, connectome, stimulus_params, condition_name="looming"
    )
    lc4_silenced = session.run_looming_session(
        registry, connectome, stimulus_params, condition_name="looming_LC4_silenced",
        silenced_populations=("LC4",),
    )

    # Silencing one redundant pathway should not increase DNp01 drive beyond baseline.
    assert lc4_silenced.dnp01_spike_count <= full_result.dnp01_spike_count


def test_lesion_does_not_mutate_base_connectome(built_fixture_connectome):
    registry, connectome, _manifest = built_fixture_connectome
    before = connectome.copy()
    stimulus_params = looming.looming(simulation_duration_ms=300.0, seed=99)
    session.run_looming_session(
        registry, connectome, stimulus_params, condition_name="looming_LC4_LPLC2_silenced",
        silenced_populations=("LC4", "LPLC2"),
    )
    assert (connectome != before).nnz == 0
