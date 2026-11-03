"""CropPlannerNet through ONNX Runtime. The only module that imports onnxruntime (§4.11)."""

from collections.abc import Sequence
from datetime import date

import numpy as np
import onnxruntime as ort
from fieldpilot_planner.crops import CropCard
from fieldpilot_planner.serving import SiteSnapshot, decode_network, plan_inputs

from app.planning.bundle import PlannerBundle
from app.planning.ports import Recommendation


class OnnxRecommender:
    def __init__(self, bundle: PlannerBundle, success_threshold: float, spinup_days: int) -> None:
        self._bundle = bundle
        self._success_threshold = success_threshold
        self._spinup_days = spinup_days
        options = ort.SessionOptions()
        options.intra_op_num_threads = 1  # small batches; keep the API's threads free
        self._session = ort.InferenceSession(
            str(bundle.onnx_path), options, providers=["CPUExecutionProvider"]
        )

    @property
    def model_id(self) -> str:
        return self._bundle.id

    @property
    def crops(self) -> Sequence[CropCard]:
        return self._bundle.crops

    def recommend(self, snapshot: SiteSnapshot, sowing_dates: Sequence[date]) -> Recommendation:
        inputs = plan_inputs(
            snapshot,
            sowing_dates,
            self._bundle.crops,
            self._bundle.norm,
            self._success_threshold,
            self._spinup_days,
        )
        feed = {
            "weather": inputs.weather,
            "clim": inputs.clim,
            "static": inputs.static,
            "crops": inputs.crops,
            "prior": inputs.prior,
        }
        raw = np.asarray(self._session.run(None, feed)[0], dtype=np.float32)
        return Recommendation(inputs.climatology.contexts, decode_network(raw, inputs))
