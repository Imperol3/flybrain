"""LIF neuron model math and whole-connectome engine: calculations, determinism, quiescence."""

import numpy as np
import scipy.sparse as sp

import config
from brain.neuron_models import lif
from simulation.engine import lif_engine


def test_initial_state_at_reset_potential():
    state = lif.LifState.initial(5, config.LIF_PARAMS["v_reset_mV"])
    assert np.all(state.v == config.LIF_PARAMS["v_reset_mV"])
    assert np.all(state.g == 0.0)
    assert np.all(state.refractory_remaining_ms == 0.0)


def test_step_matches_scalar_recurrence_of_documented_equations():
    """Cross-check the vectorized step() against a plain-Python scalar
    reimplementation of the same documented ODE update, for a single
    isolated neuron receiving a constant external conductance input. This
    catches vectorization/indexing bugs; it is not an independent literature
    implementation (Brian2 is an optional dependency, see
    docs/BIOLOGICAL_ASSUMPTIONS.md for an independent cross-check path).
    """
    params = config.LIF_PARAMS
    dt = 0.1
    g_input = 0.05  # small constant sub-threshold conductance increment per step

    # Vectorized (n=1)
    state = lif.LifState.initial(1, params["v_reset_mV"])
    for _ in range(50):
        state, _spiked = lif.step(state, np.array([g_input]), dt, params)
    vectorized_v = float(state.v[0])
    vectorized_g = float(state.g[0])

    # Scalar recurrence of the same equations.
    v = params["v_reset_mV"]
    g = 0.0
    refractory = 0.0
    decay = np.exp(-dt / params["tau_synapse_ms"])
    for _ in range(50):
        g = g * decay + g_input
        if refractory <= 0.0:
            v = v + (dt / params["tau_membrane_ms"]) * (params["v_reset_mV"] - v + g)
            if v >= params["v_threshold_mV"]:
                v = params["v_reset_mV"]
                refractory = params["t_refractory_ms"]
        else:
            v = params["v_reset_mV"]
            refractory = max(refractory - dt, 0.0)

    assert np.isclose(vectorized_v, v)
    assert np.isclose(vectorized_g, g)


def test_step_spikes_when_driven_above_threshold():
    """v only moves a fraction (dt/tau_membrane) toward its target each step,
    so a strong constant conductance input should produce a spike within a
    handful of steps, not necessarily the very first one.
    """
    params = config.LIF_PARAMS
    state = lif.LifState.initial(1, params["v_reset_mV"])
    big_input = np.array([params["v_threshold_mV"] - params["v_reset_mV"] + 10.0])
    spiked_ever = False
    for _ in range(100):
        state, spiked = lif.step(state, big_input, dt_ms=0.1, params=params)
        if spiked[0]:
            spiked_ever = True
            break
    assert spiked_ever


def test_unstimulated_network_stays_silent():
    """No external input, no recurrent activity -> zero spikes for the whole run."""
    n = 10
    connectome = sp.csr_matrix((n, n))
    result = lif_engine.run(
        connectome, n_neurons=n, dataset_version="test", dt_ms=0.1, duration_ms=50.0, seed=0
    )
    assert result.spike_neuron_indices.size == 0
    assert result.n_active_neurons() == 0


def test_deterministic_given_same_seed_and_parameters():
    n = 6
    rows = [0, 0, 1, 2]
    cols = [1, 2, 3, 4]
    data = [50, 50, 50, 50]
    connectome = sp.coo_matrix((data, (rows, cols)), shape=(n, n)).tocsr()

    def external_input_fn(step, _dt_ms):
        vec = np.zeros(n)
        if step < 50:
            vec[0] = 2.0
        return vec

    kwargs = dict(
        connectome=connectome,
        n_neurons=n,
        dataset_version="test",
        dt_ms=0.1,
        duration_ms=30.0,
        seed=42,
        external_input_fn=external_input_fn,
    )
    result_a = lif_engine.run(**kwargs)
    result_b = lif_engine.run(**kwargs)

    assert np.array_equal(result_a.spike_times_ms, result_b.spike_times_ms)
    assert np.array_equal(result_a.spike_neuron_indices, result_b.spike_neuron_indices)


def test_different_seeds_still_deterministic_v0_has_no_stochastic_term():
    """V0's LIF model has no noise term (documented in BIOLOGICAL_ASSUMPTIONS.md),
    so changing only the seed must not change the result.
    """
    n = 4
    connectome = sp.csr_matrix((n, n))

    def external_input_fn(step, _dt_ms):
        vec = np.zeros(n)
        vec[0] = 1.0
        return vec

    result_seed1 = lif_engine.run(
        connectome, n_neurons=n, dataset_version="test", dt_ms=0.1, duration_ms=20.0, seed=1,
        external_input_fn=external_input_fn,
    )
    result_seed2 = lif_engine.run(
        connectome, n_neurons=n, dataset_version="test", dt_ms=0.1, duration_ms=20.0, seed=2,
        external_input_fn=external_input_fn,
    )
    assert np.array_equal(result_seed1.spike_neuron_indices, result_seed2.spike_neuron_indices)


def test_time_series_bins_spikes_per_named_population():
    n = 4
    connectome = sp.csr_matrix((n, n))

    def external_input_fn(step, _dt_ms):
        vec = np.zeros(n)
        vec[0] = 1.0
        return vec

    result = lif_engine.run(
        connectome, n_neurons=n, dataset_version="test", dt_ms=0.1, duration_ms=20.0, seed=0,
        external_input_fn=external_input_fn,
    )
    series = result.time_series({"pop_a": np.array([0]), "pop_b": np.array([1, 2, 3])}, bin_ms=5.0)

    assert len(series) == 4  # 20ms / 5ms bins
    assert all(set(row) == {"t_ms", "pop_a", "pop_b", "active_neurons"} for row in series)
    assert [row["t_ms"] for row in series] == [0.0, 5.0, 10.0, 15.0]
    # Only neuron 0 ever spikes (it's the only one driven and the connectome is empty).
    total_pop_a = sum(row["pop_a"] for row in series)
    total_pop_b = sum(row["pop_b"] for row in series)
    assert total_pop_a == result.spike_neuron_indices.size
    assert total_pop_b == 0


def test_time_series_empty_run_has_zeroed_bins():
    n = 3
    connectome = sp.csr_matrix((n, n))
    result = lif_engine.run(connectome, n_neurons=n, dataset_version="test", dt_ms=1.0, duration_ms=10.0, seed=0)
    series = result.time_series({"a": np.array([0, 1, 2])}, bin_ms=2.0)
    assert len(series) == 5
    assert all(row["a"] == 0 and row["active_neurons"] == 0 for row in series)


def test_first_spike_time_for_returns_none_when_never_spiked():
    n = 3
    connectome = sp.csr_matrix((n, n))
    result = lif_engine.run(connectome, n_neurons=n, dataset_version="test", dt_ms=1.0, duration_ms=10.0, seed=0)
    assert result.first_spike_time_for([0, 1, 2]) is None


def test_first_spike_time_for_returns_earliest_spike():
    n = 4
    connectome = sp.csr_matrix((n, n))

    def external_input_fn(step, _dt_ms):
        vec = np.zeros(n)
        vec[0] = 1.0
        return vec

    result = lif_engine.run(
        connectome, n_neurons=n, dataset_version="test", dt_ms=0.1, duration_ms=50.0, seed=0,
        external_input_fn=external_input_fn,
    )
    t = result.first_spike_time_for([0])
    assert t is not None
    assert t == float(result.spike_times_ms.min())
    # A neuron that never received input never appears.
    assert result.first_spike_time_for([1, 2, 3]) is None
