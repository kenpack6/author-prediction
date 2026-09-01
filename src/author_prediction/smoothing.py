"""Step 4 stub: change-point smoothing / segment reconciliation.

Not designed yet -- this exists purely so run_pipeline has something
that satisfies SmootherProtocol to call, keeping the pipeline runnable
end to end while step 4's real design (boundary detection, segment
pooling, etc.) happens separately.
"""

from __future__ import annotations

from typing import List


class NoOpSmoother:
    """Passes assignments through unchanged. Placeholder for real step 4."""

    def smooth(self, assignments: List[dict]) -> List[dict]:
        """Return the assignments unmodified.

        Args:
            assignments: Step-3 results, in order.

        Returns:
            A shallow copy of ``assignments``, unchanged.
        """
        return list(assignments)
