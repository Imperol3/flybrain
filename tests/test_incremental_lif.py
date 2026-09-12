"""State-preserving engine checks for the interactive viewer."""

import numpy as np
import scipy.sparse as sp

import config
from simulation.engine import incremental_lif


def test_quiescent_segments_preserve_and_advance_state():
    n_neurons = 4
    connectome = sp.csr_matrix((n_neurons, n_neurons), dtype=np.float64)
    state = incremental_lif.initialize(n_neurons, 0.1, config.LIF_PARAMS)

    first, state = incremental_lif.run_segment(
        connectome=connectome,
        n_neurons=n_neurons,
        dataset_version="test",
        state=state,
        duration_ms=5.0,
        dt_ms=0.1,
    )
    second, same_state = incremental_lif.run_segment(
        connectome=connectome,
        n_neurons=n_neurons,
        dataset_version="test",
        state=state,
        duration_ms=7.5,
        dt_ms=0.1,
    )

    assert same_state is state
    assert same_state.elapsed_ms == 12.5
    assert first.spike_neuron_indices.size == 0
    assert second.spike_neuron_indices.size == 0


def test_outbound_mask_does_not_mutate_source_connectome():
    source = sp.csr_matrix(np.ones((3, 3), dtype=np.float64))
    masked = incremental_lif.mask_outbound(source, 3, (1,))
    assert source[1, :].sum() == 3
    assert masked[1, :].sum() == 0
    assert masked[0, :].sum() == 3
